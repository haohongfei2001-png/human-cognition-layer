"""Read-only explicit adapters for the old source, evidence and order types.

No adapter calls a preparation backend or answer callback. Story observers do
not provision system readers. Partial evidence cannot reconstruct a document.
"""
from dataclasses import asdict
import json

from .types import LegacyRecord, LegacySnapshot, LegacySource


class LegacyAdapter:
    @staticmethod
    def authorized_text(source, *, status="CURRENT", formal_problem=None):
        from hcl.cognition.semantic import AuthorizedText
        if type(source) is not AuthorizedText:
            raise ValueError("AuthorizedText snapshot required")
        metadata = asdict(source)
        del metadata["text"]
        return LegacySource(source.source_id, source.version, source.text, status, metadata, formal_problem)

    @staticmethod
    def workspace(workspace):
        from hcl.cognition.workspace import CognitionWorkspace
        if type(workspace) is not CognitionWorkspace:
            raise ValueError("legacy CognitionWorkspace snapshot required")
        core = workspace.core
        sources = {}
        for key, version in workspace._versions.items():
            current = workspace._documents.get(key)
            sources[key, version] = LegacySource(key, version, current[0] if current else None,
                "CURRENT" if current else "WITHDRAWN",
                {"permitted_observers": current[1] if current else (), "history_complete": False})
        records = []
        grounded, statuses = core.grounded(), core.support_statuses()
        for key, span in sorted(core.spans.items()):
            if (span.source_id, span.version) not in sources:
                sources[span.source_id, span.version] = LegacySource(span.source_id, span.version, None,
                    "HISTORICAL", {"history_complete": False})
            records.append(LegacyRecord(key, "SOURCE_SPAN", asdict(span),
                "WITHDRAWN" if key in core.withdrawn else "LEGACY_ONLY"))
        for key, claim in sorted(core.claims.items()):
            records.append(LegacyRecord(key, claim.kind.value, {
                "scope": asdict(claim.scope), "content": claim.content,
                "grounded": key in grounded, "support_status": statuses[key],
                "supports": sorted([sorted(group) for group in core.dependencies.get(key, ())]),
                "challenges": sorted(core.challenges.get(key, ())),
                "projection_of": core.projections.get(key),
                "interpretation": asdict(core.interpretations[key]) if key in core.interpretations else None,
                "grounding_semantics": "LIVE_RECORDED_DERIVATION_NOT_TRUTH",
            }, "WITHDRAWN" if key in core.withdrawn else "LEGACY_ONLY"))
        for index, revision in enumerate(core.revisions):
            records.append(LegacyRecord(f"revision:{index}", "INTERPRETATION_REVISION", revision))
        return LegacySnapshot(tuple(sources[key] for key in sorted(sources)), tuple(records), "CognitionWorkspace")

    @staticmethod
    def receipt(receipt, *, old_id="receipt"):
        if type(receipt) is not dict or receipt.get("schema") != "hcl-shared-evidence-v1":
            raise ValueError("versioned legacy evidence receipt required")
        return LegacyRecord(old_id, "SCOPED_EVIDENCE_RECEIPT", receipt)

    @staticmethod
    def report(assessment, *, old_id="report"):
        from hcl.cognition.report_provenance import ReportAssessment
        if type(assessment) is not ReportAssessment:
            raise ValueError("ReportAssessment snapshot required")
        return LegacyRecord(old_id, "REPORT_ASSESSMENT", {
            "scope": asdict(assessment.scope), "query": assessment.query,
            "entries": json.loads(assessment.entries_json), "families": json.loads(assessment.families_json),
            "diagnostics": json.loads(assessment.diagnostics_json),
            "independence": "NOT_ESTABLISHED", "independent_support_count": None,
        })

    @staticmethod
    def event(event, *, provenance):
        from hcl.v04.model import EventRecord
        if type(event) is not EventRecord or provenance not in ("v1.prepare_narrative", "caller_event_snapshot"):
            raise ValueError("typed event and explicit adapter provenance required")
        raw = asdict(event)
        synthetic = provenance == "v1.prepare_narrative" and event.source_id == "authorized-narrative-order-only"
        return LegacyRecord(event.event_id, "ORDER_EVENT", {
            "original": raw, "adapter_provenance": provenance,
            "time_kind": "SOURCE_ORDER" if synthetic else "UNVERIFIED_LEGACY_TIME_LABEL",
            "event_time": None, "access_time": None, "calendar_time_established": False,
            "actor_binding": "SOURCE_LOCAL_NAME_ONLY", "exact_source_offsets": None,
        })

    @staticmethod
    def order(order, *, old_id="order"):
        from hcl.narrative_order import NarrativeOrder
        if type(order) is not NarrativeOrder:
            raise ValueError("NarrativeOrder snapshot required")
        return LegacyRecord(old_id, "NARRATIVE_ORDER", {
            "scope": order.scope, "text": order.text,
            "events": {key: asdict(anchor) for key, anchor in order.events.items()},
            "relations": [asdict(edge) for edge in order.relations],
            "semantics": "SUPPLIED_STRICT_BEFORE_ONLY_NOT_CALENDAR_OR_MENTAL_TRUTH",
        })
