"""Durable native-CNY batch claims, shared by every bound task/process.

The separate host-owned SQLite database is mandatory, never auto-created on
open. Reserve here before touching the task call log. A crash in either-database
seam leaves a full hold and blocks the entire batch. There is intentionally no
release, reset, retry, resume-send, or grant-renewal API. A temporary CI ledger is
NOT cross-run protection: CI must first durably claim its unique authorized run.
"""
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from threading import RLock
import time

from hcl.memory import codec
from hcl.models.deepseek_contracts import (
    DeepSeekBatchAuthorization, DeepSeekCandidateRequest, DeepSeekCandidateReturn,
    MODE, MODEL, MODEL_VERSION, CONTEXT_TOKENS, OUTPUT_TOKENS, INPUT_RATE, CACHE_RATE, OUTPUT_RATE, RESERVATION_NANOYUAN, digest,
)
from hcl.runtime.candidate_ledger import blocked
from hcl.runtime.budget import TaskBudgetLedger
from hcl.runtime.execution_ledger import validate_execution_reservation


def authorization_hash(grant):
    return sha256(codec.dumps(grant)).hexdigest()


def cny(value):
    whole, fraction = divmod(value, 10**9)
    return str(whole)+"."+str(fraction).zfill(9)


class CNYBatchLedger:
    @classmethod
    def create(cls, authorization):
        """Explicit host issuance only; never reinitializes an existing path.

        Caller owns globally unique batch issuance and durable storage. This
        API is not exposed to model/source input, a CLI, or workflow dispatch.
        """
        if type(authorization) is not DeepSeekBatchAuthorization:
            raise ValueError("native-CNY authorization required")
        path = Path(authorization.ledger_path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        db = sqlite3.connect(path, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE control(singleton INTEGER PRIMARY KEY, protocol TEXT NOT NULL, path TEXT NOT NULL, authorization BLOB NOT NULL, authorization_hash TEXT NOT NULL, status TEXT NOT NULL)")
            db.execute("CREATE TABLE claims(claim_id TEXT PRIMARY KEY, task_fingerprint TEXT NOT NULL, state TEXT NOT NULL, cost_upper INTEGER, receipt BLOB)")
            db.execute("INSERT INTO control VALUES(1,?,?,?,?,?)", (MODE, str(path), codec.dumps(authorization), authorization_hash(authorization), "ACTIVE"))
            db.execute("PRAGMA user_version=1")
            db.commit()
        finally:
            db.close()
        # A failed creation intentionally leaves a non-reusable path.
        return cls(authorization)

    def __init__(self, authorization):
        if type(authorization) is not DeepSeekBatchAuthorization:
            raise ValueError("native-CNY authorization required")
        self.authorization, self.path = authorization, Path(authorization.ledger_path)
        if self.path.is_symlink() or not self.path.is_file():
            raise blocked("CNY_DURABLE_LEDGER_REQUIRED")
        self._identity = (self.path.stat().st_dev, self.path.stat().st_ino)
        self._lock = RLock()
        self._db = sqlite3.connect(self.path.as_uri()+"?mode=rw", uri=True, isolation_level=None, timeout=10, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA synchronous=FULL")
        try:
            with self._transaction() as db:
                self._validate(db)
        except BaseException:
            self._db.close()
            raise

    def close(self):
        self._db.close()

    @contextmanager
    def _transaction(self):
        with self._lock:
            if (self.path.is_symlink() or not self.path.is_file()
                    or (self.path.stat().st_dev, self.path.stat().st_ino) != self._identity):
                raise blocked("CNY_LEDGER_REPLACED")
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
                self._db.commit()
            except BaseException:
                self._db.rollback()
                raise

    def _validate(self, db, *, active=False):
        try:
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("version")
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables != {"control", "claims"}:
                raise ValueError("layout")
            layouts = {
                "control": [("singleton","INTEGER",0,1),("protocol","TEXT",1,0),("path","TEXT",1,0),
                    ("authorization","BLOB",1,0),("authorization_hash","TEXT",1,0),("status","TEXT",1,0)],
                "claims": [("claim_id","TEXT",0,1),("task_fingerprint","TEXT",1,0),("state","TEXT",1,0),
                    ("cost_upper","INTEGER",0,0),("receipt","BLOB",0,0)],
            }
            for table, expected in layouts.items():
                actual = [(r[1],r[2],r[3],r[5]) for r in db.execute("PRAGMA table_info("+table+")")]
                if actual != expected:
                    raise ValueError("schema columns or primary keys")
            if db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view')").fetchone():
                raise ValueError("unexpected active schema")
            control = list(db.execute("SELECT * FROM control"))
            if len(control) != 1:
                raise ValueError("control")
            control = dict(control[0])
            if (set(control) != {"singleton","protocol","path","authorization","authorization_hash","status"}
                    or control["singleton"] != 1 or control["protocol"] != MODE
                    or control["path"] != str(self.path)
                    or control["authorization"] != codec.dumps(self.authorization)
                    or control["authorization_hash"] != authorization_hash(self.authorization)
                    or control["status"] not in {"ACTIVE", "REVOKED", "CLOSED", "BLOCKED"}):
                raise ValueError("authorization")
            rows = list(db.execute("SELECT * FROM claims"))
            if len(rows) > self.authorization.max_calls:
                raise ValueError("claims")
            for row in rows:
                digest(row["claim_id"]); digest(row["task_fingerprint"])
                if (set(row.keys()) != {"claim_id","task_fingerprint","state","cost_upper","receipt"}
                        or row["task_fingerprint"] not in self.authorization.task_fingerprints
                        or row["state"] not in {"RESERVED", "SEND_STARTED", "RETURNED", "UNKNOWN"}):
                    raise ValueError("claim")
                if row["state"] == "RETURNED":
                    receipt = codec.loads(row["receipt"])
                    if (type(receipt) is not DeepSeekCandidateReturn or receipt.visible_text is not None
                            or row["cost_upper"] != receipt.usage_cost_upper_nanoyuan
                            or type(row["cost_upper"]) is not int or row["cost_upper"] < 0):
                        raise ValueError("settlement")
                    values = (receipt.input_tokens, receipt.cached_input_tokens, receipt.uncached_input_tokens,
                              receipt.output_tokens, receipt.reasoning_tokens)
                    if (not all(type(v) is int and 0 <= v <= 10**12 for v in values)
                            or receipt.input_tokens < 1 or receipt.output_tokens < 1
                            or receipt.input_tokens != receipt.cached_input_tokens + receipt.uncached_input_tokens
                            or receipt.reasoning_tokens > receipt.output_tokens
                            or receipt.model not in (MODEL,MODEL_VERSION)
                            or type(receipt.provider_response_id) is not str or not 1 <= len(receipt.provider_response_id) <= 256
                            or any(ord(c) < 32 for c in receipt.provider_response_id)
                            or receipt.usage_cost_upper_nanoyuan != receipt.uncached_input_tokens*INPUT_RATE
                                + receipt.cached_input_tokens*CACHE_RATE + receipt.output_tokens*OUTPUT_RATE
                            or (receipt.validation_code is not None and
                                (type(receipt.validation_code) is not str or not receipt.validation_code.startswith("DEEPSEEK_")))):
                        raise ValueError("receipt usage or identity")
                    if receipt.validation_code is None and (
                            receipt.input_tokens + receipt.output_tokens > CONTEXT_TOKENS
                            or receipt.output_tokens > OUTPUT_TOKENS or receipt.reasoning_tokens != 0
                            or receipt.finish_reason != "stop" or row["cost_upper"] > RESERVATION_NANOYUAN):
                        raise ValueError("unreported invalid receipt")
                    if control["status"] == "ACTIVE" and receipt.validation_code is not None:
                        raise ValueError("failed receipt with active authority")
                elif row["receipt"] is not None or row["cost_upper"] is not None:
                    raise ValueError("unknown settlement")
                if row["state"] == "UNKNOWN" and control["status"] == "ACTIVE":
                    raise ValueError("unknown active authority")
        except (sqlite3.Error, TypeError, ValueError, KeyError):
            raise blocked("CNY_LEDGER_CORRUPT", "FAILED") from None
        if active:
            if control["status"] != "ACTIVE":
                raise blocked("CNY_BATCH_"+control["status"])
            now = time.time()
            if not self.authorization.verified_at <= now <= self.authorization.expires_at:
                raise blocked("CNY_TARIFF_OR_GRANT_EXPIRED")
        return control, rows

    def reserve(self, claim_id, fingerprint):
        digest(claim_id); digest(fingerprint)
        with self._transaction() as db:
            _, rows = self._validate(db, active=True)
            if fingerprint not in self.authorization.task_fingerprints:
                raise blocked("CNY_TASK_NOT_AUTHORIZED")
            if any(r["state"] != "RETURNED" for r in rows):
                raise blocked("CNY_UNRESOLVED_CLAIM_NO_SEND", "SEND_UNKNOWN")
            if any(r["claim_id"] == claim_id for r in rows):
                raise blocked("CNY_CLAIM_ALREADY_EXISTS")
            if len(rows) >= self.authorization.max_calls:
                raise blocked("CNY_BATCH_CALL_LIMIT", "BUDGET_EXHAUSTED")
            if sum(r["cost_upper"] for r in rows)+RESERVATION_NANOYUAN > self.authorization.max_cost_nanoyuan:
                raise blocked("CNY_BATCH_COST_LIMIT", "BUDGET_EXHAUSTED")
            db.execute("INSERT INTO claims VALUES(?,?,?,NULL,NULL)", (claim_id, fingerprint, "RESERVED"))

    def dispatch(self, claim_id, authorize):
        with self._transaction() as db:
            _, rows = self._validate(db, active=True)
            row = next((r for r in rows if r["claim_id"] == claim_id), None)
            if row is None or row["state"] != "RESERVED" or any(r["state"] != "RETURNED" for r in rows if r["claim_id"] != claim_id):
                raise blocked("CNY_DISPATCH_STATE")
            authorize()  # Fresh HCL grant/ACL validation while batch revocation is serialized.
            self._validate(db, active=True)  # Gate work may have crossed the attestation expiry.
            db.execute("UPDATE claims SET state='SEND_STARTED' WHERE claim_id=?", (claim_id,))

    def returned(self, claim_id, receipt):
        from dataclasses import replace
        if type(receipt) is not DeepSeekCandidateReturn:
            raise ValueError("native-CNY receipt required")
        with self._transaction() as db:
            _, rows = self._validate(db)
            row = next((r for r in rows if r["claim_id"] == claim_id), None)
            if row is None or row["state"] != "SEND_STARTED":
                raise blocked("CNY_RETURN_STATE")
            if receipt.usage_cost_upper_nanoyuan is None:
                db.execute("UPDATE claims SET state='UNKNOWN' WHERE claim_id=?", (claim_id,))
                db.execute("UPDATE control SET status='BLOCKED'")
            else:
                # Sidecar never stores visible text, reasoning or source material.
                db.execute("UPDATE claims SET state='RETURNED',cost_upper=?,receipt=? WHERE claim_id=?",
                    (receipt.usage_cost_upper_nanoyuan, codec.dumps(replace(receipt, visible_text=None)), claim_id))
                if receipt.validation_code:
                    db.execute("UPDATE control SET status='BLOCKED' WHERE status='ACTIVE'")

    def stop(self, status="BLOCKED"):
        if status not in {"BLOCKED", "REVOKED", "CLOSED"}:
            raise ValueError("terminal status required")
        with self._transaction() as db:
            self._validate(db)
            db.execute("UPDATE control SET status=? WHERE status='ACTIVE'", (status,))

    def audit(self):
        with self._transaction() as db:
            control, rows = self._validate(db)
            observed = sum(r["cost_upper"] or 0 for r in rows)
            held = sum(r["cost_upper"] if r["cost_upper"] is not None else RESERVATION_NANOYUAN for r in rows)
            return dict(batch_id=self.authorization.batch_id, status=control["status"], claimed_calls=len(rows),
                        max_calls=self.authorization.max_calls, currency="CNY", held_nanoyuan=held,
                        observed_usage_cost_upper_nanoyuan=observed, actual_billed_cny=None,
                        unresolved=any(r["state"] != "RETURNED" for r in rows),
                        states=tuple(r["state"] for r in rows))


def split_deepseek_calls(store, rows):
    ordinary, native = [], []
    for row in rows:
        request = store._get_object(row["request_hash"])
        if type(request) is DeepSeekCandidateRequest:
            receipt = store._get_object(row["response_hash"]) if row["response_hash"] else None
            if receipt is not None and type(receipt) is not DeepSeekCandidateReturn:
                raise blocked("CNY_TASK_LEDGER_CORRUPT", "FAILED")
            native.append((row,request,receipt))
        else:
            ordinary.append(row)
    return ordinary, native


def native_usage(rows):
    if not rows:
        return {}
    observed = sum(r.usage_cost_upper_nanoyuan or 0 for _,_,r in rows if r)
    held = sum(r.usage_cost_upper_nanoyuan if r and r.usage_cost_upper_nanoyuan is not None
               else request.reservation_nanoyuan for _,request,r in rows)
    unknown = any(row["attempted"] is None for row,_,_ in rows)
    return dict(accounting_mode=MODE, currency="CNY", provider_calls=None if unknown else sum(row["attempted"] or 0 for row,_,_ in rows),
                observed_provider_calls=sum(row["attempted"] or 0 for row,_,_ in rows), held_provider_calls=len(rows),
                provider_send_unknown=unknown, provider_spend_usd=None, actual_billed_cny=None,
                observed_usage_cost_upper_cny=cny(observed), held_cost_upper_cny=cny(held),
                observed_usage_cost_upper_nanoyuan=observed, held_cost_upper_nanoyuan=held,
                provider_usage_unknown=any(r is None or r.usage_cost_upper_nanoyuan is None for _,_,r in rows),
                observed_provider_input_tokens=sum(r.input_tokens or 0 for _,_,r in rows if r),
                observed_provider_output_tokens=sum(r.output_tokens or 0 for _,_,r in rows if r),
                provider_tokenizer="PROVIDER_REPORTED_USAGE_WITH_FULL_CONTEXT_RESERVATION",
                replay_new_provider_calls=0)


class DeepSeekTaskLedger(TaskBudgetLedger):
    def reserve_candidate(self, lease, snapshot, question, allowance, call_id, envelope):
        with self.store._transaction(True) as db:
            session, task = self._lease(db, lease)
            self.store._validate_snapshot(db, snapshot)
            request = self.store._get_object(task["request_hash"])
            if (envelope.task_fingerprint != task["fingerprint"] or snapshot.session_id != lease.session_id
                    or snapshot.principal != lease.principal or question != request.question
                    or dict(envelope.source_versions) != dict(snapshot.source_versions)):
                raise blocked("DEEPSEEK_TASK_BINDING_MISMATCH")
            validate_execution_reservation(self, db, task, request, snapshot, call_id, envelope.context, allowance)
            rows = list(db.execute("SELECT * FROM calls WHERE task_key=?", (lease.task_key,)))
            ordinary, native = split_deepseek_calls(self.store, rows)
            if ordinary or any(r.authorization_hash != envelope.authorization_hash for _,r,_ in native):
                raise blocked("DEEPSEEK_MIXED_AUTHORIZATION")
            if rows and (len(rows) != 1 or rows[0]["state"] != "RETURNED"
                    or not (rows[0]["validation_code"] or "").startswith("COMPILE_REJECTED:")):
                raise blocked("DEEPSEEK_ONLY_SEMANTIC_REPAIR")
            if db.execute("SELECT 1 FROM calls WHERE task_key=? AND call_id=?", (lease.task_key,call_id)).fetchone():
                raise blocked("CALL_ALREADY_RESERVED")
            size = len(envelope.body.encode("utf-8"))
            if size > allowance.max_request_bytes or sum(r["request_bytes"] for r in rows)+size > allowance.max_total_request_bytes:
                raise blocked("DEEPSEEK_REQUEST_CAPACITY", "BUDGET_EXHAUSTED")
            row = dict(task_key=lease.task_key, call_id=call_id, session_id=lease.session_id, state="RESERVED",
                       owner_id=lease.owner_id, request_hash=self.store._put_content(envelope,
                       session_id=lease.session_id, context=snapshot, owner=("task",lease.session_id,lease.task_key)),
                       response_hash=None, request_bytes=size, output_bytes=None, attempted=0, validation_code=None)
            self.store._record(db,"calls",row,session["revision"])

    def returned(self, lease, call_id, receipt):
        with self.store._transaction(True) as db:
            session, _ = self._lease(db, lease)
            row = dict(db.execute("SELECT * FROM calls WHERE task_key=? AND call_id=?", (lease.task_key,call_id)).fetchone())
            if row["state"] != "SEND_STARTED" or type(receipt) is not DeepSeekCandidateReturn:
                raise blocked("DEEPSEEK_RETURN_STATE")
            row.update(state="RETURNED", attempted=1, response_hash=self.store._put_content(receipt,
                       session_id=lease.session_id,owner=("task",lease.session_id,lease.task_key)),
                       output_bytes=len(receipt.visible_text.encode()) if receipt.visible_text is not None else None,
                       validation_code=receipt.validation_code)
            self.store._record(db,"calls",row,session["revision"])
