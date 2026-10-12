"""Hybrid retrieval and recursive recorded dependency closure.

Inputs to the pure projection must ALREADY have been filtered by current host
ACL, including every index, graph node and corpus-statistics contribution.
Ranking is discovery, not support/contradiction classification or completeness.
"""
from collections import Counter, deque
from dataclasses import asdict
from hashlib import sha256
from math import log, sqrt

from hcl.kernel.retrieval import EvidenceNode, RetrievalQuery, RetrievalDependency, ROUTES, RETRIEVAL_VERSION
from hcl.kernel.types import freeze, thaw
from hcl.memory import codec
from hcl.memory.index import INDEX_VERSION, TOKENIZER, terms, index_identity
from hcl.semantics.segments import SourceSegment


def rank_regions(query, regions):
    """BM25 and normalized sparse TF-IDF cosine, fused by reciprocal rank.

    All candidates are authorized regions; no hidden-document IDF, counts or
    length normalization. Deterministic ties use exact original segment identity.
    """
    query_counts = Counter(terms(query))
    size = len(regions)
    if not query_counts or not size:
        return ()
    df = Counter(term for row in regions for term in row["counts"])
    lengths = {row["segment_id"]: sum(row["counts"].values()) for row in regions}
    average = sum(lengths.values()) / size
    idf = {term: log((1 + size) / (1 + frequency)) + 1 for term, frequency in df.items()}
    q_vector = {term: (1 + log(count)) * idf[term] for term, count in query_counts.items() if term in df}
    q_norm = sqrt(sum(value * value for value in q_vector.values()))
    scores = {}
    for row in regions:
        key, counts = row["segment_id"], row["counts"]
        bm25 = sum(log(1 + (size - df[term] + .5) / (df[term] + .5)) * counts[term] * 2.2
                   / (counts[term] + 1.2 * (.25 + .75 * lengths[key] / (average or 1)))
                   for term in query_counts if term in counts)
        vector = {term: (1 + log(count)) * idf[term] for term, count in counts.items()}
        norm = sqrt(sum(value * value for value in vector.values()))
        cosine = sum(value * q_vector.get(term, 0) for term, value in vector.items()) / (norm * q_norm) if norm and q_norm else 0.0
        if bm25 or cosine:
            scores[key] = dict(bm25=bm25, tfidf_cosine=cosine, rrf=0.0)
    for channel in ("bm25", "tfidf_cosine"):
        ranking = sorted((key for key in scores if scores[key][channel] > 0), key=lambda key: (-scores[key][channel], key))
        for position, key in enumerate(ranking, 1):
            scores[key]["rrf"] += 1 / (60 + position)
    return tuple(dict(segment_id=key, **scores[key]) for key in sorted(scores, key=lambda key: (-scores[key]["rrf"], key)))


def recorded_closure(seeds, nodes, available_segments, *, max_nodes, max_characters):
    """Read all recorded AND members/OR alternatives, challenges and revisions.

    Traversal may discover new obligations repeatedly. A bound leaves explicit
    unresolved frontier, never a selected fragment marked as a full closure.
    Missing IDs are opaque: caller may not resolve them in unauthorized storage.
    """
    if set(nodes) & set(available_segments):
        raise ValueError("recorded node and original segment identities must be disjoint")
    if any(type(node) is not EvidenceNode or node.node_id != key for key, node in nodes.items()):
        raise ValueError("typed uniquely keyed evidence graph required")
    queue, queued, seen = deque(sorted(set(seeds))), set(seeds), set()
    selected_nodes, selected_segments, missing, frontier, edges = {}, {}, [], [], []
    used_characters = 0
    while queue:
        key = queue.popleft()
        if key in seen:
            continue
        if len(seen) >= max_nodes:
            frontier.extend((key, *queue))
            break
        seen.add(key)
        if key in available_segments:
            segment = available_segments[key]
            if used_characters + len(segment.text) > max_characters:
                frontier.append(key)
                continue
            selected_segments[key] = segment
            used_characters += len(segment.text)
            continue
        node = nodes.get(key)
        if node is None:
            missing.append(key)
            continue
        selected_nodes[key] = asdict(node)
        links = [(target, "SOURCE") for target in node.source_segments]
        links += [(target, "REQUIRED_AND_MEMBER", group_number) for group_number, group in enumerate(node.support_groups) for target in group]
        for name in ("challenges", "alternatives", "revision_reasons"):
            links += [(target, name.upper()) for target in getattr(node, name)]
        for link in links:
            edges.append((key, *link))
            target = link[0]
            if target not in queued:
                queue.append(target)
                queued.add(target)
    return dict(nodes=selected_nodes, segments=selected_segments, edges=tuple(edges),
                missing=tuple(sorted(set(missing))), frontier=tuple(sorted(set(frontier))),
                visited=len(seen), character_count=used_characters,
                support_semantics="AND_WITHIN_GROUP_OR_BETWEEN_GROUPS_ALL_RECORDED_ALTERNATIVES_READ",
                complete=not missing and not frontier)


def project_retrieval(query, sources, indexes, nodes):
    """Deterministic packet and query-dependency digest over an authorized scope."""
    if type(query) is not RetrievalQuery or set(sources) != set(indexes):
        raise ValueError("complete authorized indexed source scope required")
    regions, segments, source_bindings, unknown = [], {}, {}, []
    for source_id, source in sorted(sources.items()):
        if query.source_scope is not None and source_id not in query.source_scope:
            raise ValueError("projection received source outside requested scope")
        index = indexes[source_id]
        digest = sha256(source.text.encode()).hexdigest()
        if (index["source_id"], index["source_version"], index["source_sha256"]) != (source_id, source.handle.version, digest):
            raise ValueError("index source binding mismatch")
        source_bindings[source_id] = dict(version=source.handle.version, source_sha256=digest, index_sha256=index_identity(index))
        if not index["complete"]:
            unknown.append(dict(source_id=source_id, start=index["indexed_end"], end=len(source.text), reason="UNINDEXED_REGION"))
        for row in index["regions"]:
            regions.append(row)
            segment = SourceSegment(row["segment_id"], "SOURCE", source_id, source.handle.version, digest,
                                    row["start"], row["end"], row["byte_start"], row["byte_end"], source.text[row["start"]:row["end"]])
            if segment.segment_id in segments:
                raise ValueError("duplicate original region identity")
            segments[segment.segment_id] = segment
    routes, seeds = {}, set(query.seed_nodes)
    for route in ROUTES:
        ranked = rank_regions(query.queries[route], regions)
        selected = ranked[:query.max_hits_per_route]
        routes[route] = dict(query=query.queries[route], hits=selected,
                             matching_region_count=len(ranked), unselected_matching_count=max(0, len(ranked)-len(selected)),
                             role="SEARCH_INTENT_NOT_VERIFIED_SEMANTIC_RELATION")
        seeds.update(row["segment_id"] for row in selected)
    # Actual source-anchored recorded nodes become relation seeds. No NLP label
    # match or model-generated score can replace this graph traversal.
    for key, node in nodes.items():
        if seeds.intersection(node.source_segments):
            seeds.add(key)
    closure = recorded_closure(seeds, nodes, segments, max_nodes=query.max_nodes, max_characters=query.max_characters)
    read_regions = tuple(dict(segment_id=s.segment_id, source_id=s.source_id, version=s.version,
                             start=s.start, end=s.end, byte_start=s.byte_start, byte_end=s.byte_end)
                         for s in sorted(closure["segments"].values(), key=lambda s: (s.source_id, s.start)))
    read_ids = set(closure["segments"])
    unread = []
    for key, segment in segments.items():
        if key in read_ids:
            continue
        if unread and unread[-1]["source_id"] == segment.source_id and unread[-1]["end"] == segment.start:
            unread[-1]["end"] = segment.end
        else:
            unread.append(dict(source_id=segment.source_id, start=segment.start, end=segment.end, reason="INDEXED_NOT_READ"))
    projection = dict(schema=RETRIEVAL_VERSION, query=query.wire(), index_version=INDEX_VERSION,
                      tokenizer=TOKENIZER, vector_representation="AUTHORIZED_CORPUS_SPARSE_TFIDF_NOT_SEMANTIC_EMBEDDING",
                      search_scope=source_bindings, routes=routes,
                      packet=dict(segments=tuple(asdict(s) for s in closure["segments"].values()),
                                  recorded_nodes=closure["nodes"], edges=closure["edges"],
                                  support_semantics=closure["support_semantics"]),
                      coverage=dict(read_regions=read_regions, unread_regions=unread,
                                    unknown_regions=unknown, recorded_closure_complete=closure["complete"],
                                    missing_recorded_dependencies=closure["missing"], frontier=closure["frontier"],
                                    semantic_completeness="NOT_ESTABLISHED", whole_source_read=not unread and not unknown,
                                    indexed_region_count=len(regions), visited_nodes=closure["visited"],
                                    selected_characters=closure["character_count"]))
    # Corpus, query settings, full graph and unknown regions participate, not
    # merely the selected top-k. A newly indexed counterexample invalidates it.
    identity = dict(projection=projection, recorded_graph={key: asdict(node) for key, node in sorted(nodes.items())})
    dependency = RetrievalDependency(query, sha256(codec.canonical(identity).encode()).hexdigest())
    return dependency, freeze(projection)
