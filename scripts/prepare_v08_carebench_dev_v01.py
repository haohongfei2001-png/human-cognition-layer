"""Pinned, source-only CAREBench development slice; no label fields released."""

from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE_SHA256 = "93b410dab0ea3f40796f6e02bf4cb8085898670a340fe2a6f10f154593d6d05c"
SOURCE_COMMIT = "8b4135219d493c4aaa2474beeefed11779c66890"
SALT = "HCL-V08-CAREBENCH-DEV-V01"
MANIFEST = ROOT / "eval/v08/carebench_dev_selection_v01.json"


def sha(value):
    return hashlib.sha256(
        value.encode("utf-8") if isinstance(value, str) else value
    ).hexdigest()


@dataclass(frozen=True)
class SourceNarrative:
    source_key_sha256: str
    narrative_sha256: str
    text: str


def select_source_only(source: bytes):
    if sha(source) != SOURCE_SHA256:
        raise ValueError("CAREBench source hash drift")
    data = json.loads(source)
    if not isinstance(data, dict) or len(data) != 1000:
        raise ValueError("CAREBench source count drift")
    candidates = []
    seen = set()
    for key, row in sorted(data.items()):
        # Only the published first-person story reaches any model. Never
        # release cognitive responses, ratings, chat, identity or demographics.
        text = row["story_collection"]["final_scenario"]
        if not isinstance(text, str) or not 80 <= len(text) <= 1500:
            continue
        digest = sha(text)
        if digest in seen:
            continue
        seen.add(digest)
        candidates.append(SourceNarrative(sha(key), digest, text))
    return sorted(candidates, key=lambda x: sha(SALT + "|" + x.narrative_sha256))[:8]


def verified_selection(source: bytes):
    manifest = json.loads(MANIFEST.read_text())
    selected = select_source_only(source)
    expected = [
        {
            "case_id": f"care-dev-{i+1:02d}",
            "source_key_sha256": x.source_key_sha256,
            "narrative_sha256": x.narrative_sha256,
        }
        for i, x in enumerate(selected)
    ]
    if (
        manifest.get("format") != "hcl-v08-carebench-dev-selection-v01"
        or manifest.get("source_sha256") != SOURCE_SHA256
        or manifest.get("source_commit") != SOURCE_COMMIT
        or manifest.get("salt") != SALT
        or manifest.get("selected") != expected
        or len(selected) != 8
    ):
        raise ValueError("CAREBench frozen selection drift")
    return list(zip(expected, selected))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    a = p.parse_args()
    print(
        json.dumps(
            {
                "selected": len(verified_selection(a.source.read_bytes())),
                "provider_calls": 0,
            }
        )
    )
