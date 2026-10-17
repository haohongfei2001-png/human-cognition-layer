"""Read-only v1 repository lifecycle audit; never an execution authorization.

The live host still accepts only its exact READY E -> G -> M chain. This audit
also recognizes the inert preparation and irreversible closure of that chain,
so later provider-free CI does not mistake a valid closed history for a new
grant. Historical Python is hashed as data, never imported or executed.
"""
from hashlib import sha256
from pathlib import Path
import subprocess

from hcl.memory import codec
from hcl.models.candidate_protocol import strict_json

GRANT = ".github/HCL_DEEPSEEK_CORE_SMOKE_GRANT.json"
MARKER = ".github/HCL_DEEPSEEK_CORE_SMOKE_TRIGGER.json"
CASE = "scripts/deepseek_core_smoke_case.py"
CAMPAIGN = "hcl-core-deepseek-synthetic-v1"
CASE_HASH = "770beaae03fd6c72d3c169e5a3e99f565bc50c0c5022cb540dcaab24f87b50dc"
CASE_FILE_HASH = "94e9aa8441da1cfdccd02bee92e67b940cd884383183e4a08a13a35337bfc44a"
READERS = {
    "scripts/two_stage_price.py": "32c9747dc3411f4d090517f07fc60a524d327f9aecc49b5cf0a10dfcd50451b0",
    "scripts/two_stage_account.py": "18bbb9085a3a0789115d2065d7aa498e485a547b477ada40aecdd4a67d58582b",
}
UNISSUED = dict(schema="hcl-deepseek-core-smoke-grant-1", status="CLOSED_UNISSUED", campaign=CAMPAIGN)


def require(value):
    if not value:
        raise ValueError("EXACT_V1_REPOSITORY_LIFECYCLE_REQUIRED")


def digest(value, length=40):
    require(type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value))


def hash_value(value):
    return sha256(codec.canonical(value).encode()).hexdigest()


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    require(result.returncode == 0)
    return result.stdout


def text(root, *args):
    return git(root, *args).decode("utf-8").strip()


def exists(root, commit, path):
    return bool(git(root, "ls-tree", commit, "--", path))


def document(root, commit, path):
    entry = text(root, "ls-tree", commit, "--", path)
    require(entry.startswith("100644 blob ") and entry.endswith("\t" + path))
    raw = git(root, "show", commit + ":" + path)
    require(len(raw) <= 8192)
    return strict_json(raw)


def parent(root, commit):
    row = text(root, "rev-list", "--parents", "-n", "1", commit).split()
    require(len(row) == 2 and row[0] == commit)
    return row[1]


def only_change(root, before, after, path):
    require(text(root, "diff", "--name-only", before, after).splitlines() == [path])


def history(root, revision, *paths):
    return text(root, "rev-list", "--full-history", revision, "--", *paths).splitlines()


def preparation(root, commit):
    require(document(root, commit, GRANT) == UNISSUED and not exists(root, commit, MARKER))
    require(not history(root, commit, MARKER))
    # Resetting an already issued grant to the initial spelling is not inert.
    for old in history(root, commit, GRANT):
        require(exists(root, old, GRANT) and document(root, old, GRANT) == UNISSUED)


def historical_grant(root, executor):
    digest(executor)
    preparation(root, executor)
    for path, expected in {CASE: CASE_FILE_HASH, **READERS}.items():
        require(sha256(git(root, "show", executor + ":" + path)).hexdigest() == expected)
    files = {}
    for entry in git(root, "ls-tree", "-r", "-z", executor, "--", "hcl").split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        path = path.decode("utf-8")
        if path.endswith(".py"):
            require(metadata.startswith(b"100644 blob ") and path.startswith("hcl/"))
            files[path[4:]] = sha256(git(root, "show", executor + ":" + path)).hexdigest()
    require(bool(files))
    return dict(schema="hcl-deepseek-core-smoke-grant-1", status="READY", campaign=CAMPAIGN,
        executor_commit=executor, case_sha256=CASE_HASH, runtime_sha256=hash_value(files),
        reader_sha256=dict(READERS), currency="CNY", authorized_cny="20.00", authorized_calls=2,
        max_semantic_repairs=1, model="deepseek-v4-pro", model_version="DeepSeek-V4-Pro-0813",
        endpoint="https://api.deepseek.com/chat/completions", account_scope="HCL_CORE_DEEPSEEK_DIRECT",
        source_policy="SYNTHETIC_ONLY", retries=0, historical_budget_transfer=False,
        publication="SYNTHETIC_RESULT_AND_MECHANICAL_USAGE_ONLY")


def grant_commit(root, grant_head):
    executor = parent(root, grant_head)
    only_change(root, executor, grant_head, GRANT)
    require(not exists(root, grant_head, MARKER))
    grant = document(root, grant_head, GRANT)
    expected = historical_grant(root, executor)
    require(grant == expected and all(type(grant[k]) is type(v) for k, v in expected.items()))
    return grant


def marker_commit(root, marker_head):
    adopted = parent(root, marker_head)
    grant = grant_commit(root, adopted)
    only_change(root, adopted, marker_head, MARKER)
    require(document(root, marker_head, GRANT) == grant)
    expected = dict(schema="hcl-deepseek-core-smoke-marker-1", campaign=CAMPAIGN,
        executor_commit=grant["executor_commit"], grant_commit=adopted,
        grant_sha256=hash_value(grant), case_sha256=CASE_HASH)
    require(document(root, marker_head, MARKER) == expected)
    return grant


def validate_repository(root):
    """Validate tracked data/history only; no environment, secret or network use."""
    root = Path(root)
    require(not text(root, "status", "--porcelain", "--untracked-files=no"))
    head = text(root, "rev-parse", "HEAD")
    digest(head)
    current = document(root, head, GRANT)
    require(type(current) is dict)
    status = current.get("status")
    if status == "CLOSED_UNISSUED":
        preparation(root, head)
        return "PREPARATION"
    if status == "READY":
        if exists(root, head, MARKER):
            marker_commit(root, head)
            return "MARKER_COMMITTED"
        grant_commit(root, head)
        return "GRANT_COMMITTED"
    require(status in {"CLOSED_CONSUMED", "CLOSED_BLOCKED", "CLOSED_CANCELLED"})
    closed = history(root, head, GRANT)[0]
    prior = parent(root, closed)
    only_change(root, prior, closed, GRANT)
    closure = current.get("closure")
    if status == "CLOSED_CANCELLED":
        original = grant_commit(root, prior)
        require(closure == dict(schema="hcl-deepseek-core-smoke-closure-1", grant_commit=prior,
            reason="CANCELLED_BEFORE_TRIGGER"))
        require(not exists(root, head, MARKER) and not history(root, head, MARKER))
    else:
        original = marker_commit(root, prior)
        require(type(closure) is dict and set(closure) == {"schema", "marker_commit", "run_id", "receipt_sha256"})
        require(closure["schema"] == "hcl-deepseek-core-smoke-closure-1" and closure["marker_commit"] == prior)
        run = closure["run_id"]
        require(type(run) is str and run.isascii() and run.isdecimal() and int(run) > 0)
        digest(closure["receipt_sha256"], 64)
        require(document(root, head, MARKER) == document(root, prior, MARKER))
    require(current == dict(original, status=status, closure=closure))
    require(all(type(current[k]) is type(v) for k, v in original.items()))
    require(document(root, closed, GRANT) == current)
    # Even change-then-revert of either authorization path is not a new budget.
    require(not history(root, closed + ".." + head, GRANT, MARKER))
    return status
