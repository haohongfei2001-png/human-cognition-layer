"""Formal HCL entrypoint. The embedding host supplies authenticated identity."""
from __future__ import annotations

import asyncio

from hcl.kernel.types import Principal, TaskRequest, TaskResult
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway
from hcl.runtime.engine import Engine


class HCL:
    def __init__(self, store: StateStore, *, principal: Principal, gateway: ModelGateway | None = None,
                 semantic_profile=None):
        self._engine = Engine(store, principal, gateway, semantic_profile=semantic_profile)

    async def run(self, request: TaskRequest) -> TaskResult:
        return await self._engine.run(request)

    def stream(self, request: TaskRequest):
        return self._engine.stream(request)

    def run_sync(self, request: TaskRequest) -> TaskResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.run(request))
        raise RuntimeError("Use await HCL.run inside an existing event loop")
