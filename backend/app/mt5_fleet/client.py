from __future__ import annotations

import httpx

from app.mt5_fleet.schemas import (
    AgentStartRequest,
    AgentStartResponse,
    AgentStopResponse,
    MT5VerifyResult,
)


class MT5FleetClientError(RuntimeError):
    pass


class MT5FleetClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        if not self.base_url:
            raise MT5FleetClientError("MT5 fleet agent URL is not configured")
        if not self.token:
            raise MT5FleetClientError("MT5 fleet agent token is not configured")

    def _headers(self) -> dict[str, str]:
        return {"X-Abutron-Fleet-Token": self.token}

    async def verify(self, request: AgentStartRequest) -> MT5VerifyResult:
        payload = request.model_dump(mode="json", exclude={"requested_port"})
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    f"{self.base_url}/v1/verify",
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.TimeoutException as exc:
            raise MT5FleetClientError("MT5 verification timed out") from exc
        except httpx.RequestError as exc:
            raise MT5FleetClientError("MT5 fleet agent unavailable") from exc

        if response.status_code >= 400:
            detail = ""
            try:
                payload = response.json()
            except ValueError:
                payload = {}

            if isinstance(payload, dict):
                detail = str(payload.get("detail", "")).strip()
            suffix = f": {detail}" if detail else ""
            raise MT5FleetClientError(
                f"MT5 verification failed ({response.status_code}){suffix}"
            )
        return MT5VerifyResult.model_validate(response.json())

    async def start(self, request: AgentStartRequest) -> AgentStartResponse:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/v1/sessions/start", json=request.model_dump(mode="json"), headers=self._headers())
        if response.status_code >= 400:
            raise MT5FleetClientError(f"MT5 session start failed ({response.status_code})")
        return AgentStartResponse.model_validate(response.json())

    async def stop(self, session_id: str) -> AgentStopResponse:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/v1/sessions/{session_id}/stop", headers=self._headers())
        if response.status_code >= 400:
            raise MT5FleetClientError(f"MT5 session stop failed ({response.status_code})")
        return AgentStopResponse.model_validate(response.json())

    async def status(self, session_id: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/v1/sessions/{session_id}", headers=self._headers())
        if response.status_code >= 400:
            raise MT5FleetClientError(f"MT5 session status failed ({response.status_code})")
        return response.json()
