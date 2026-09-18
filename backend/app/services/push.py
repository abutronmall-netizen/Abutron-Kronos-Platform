from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.models import Device, Notification

settings = get_settings()
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushDeliveryError(RuntimeError):
    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class PushResult:
    provider_message_id: str


class PushGatewayClient:
    async def send(self, device: Device, notification: Notification) -> PushResult:
        if not settings.push_gateway_enabled:
            raise PushDeliveryError("Push gateway is disabled", code="DISABLED")
        if not settings.push_gateway_url:
            raise PushDeliveryError("Push gateway URL is not configured", code="NOT_CONFIGURED")
        if not device.push_token:
            raise PushDeliveryError("Device has no push token", code="NO_TOKEN")

        url = settings.push_gateway_url.rstrip("/")
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                if url == EXPO_PUSH_URL:
                    return await self._send_expo(device, notification)
                return await self._send_gateway(url, device, notification)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == 2:
                    break
                await asyncio.sleep(2 ** attempt)
        raise PushDeliveryError(f"Push transport failed: {last_error}", code="TRANSPORT_ERROR")

    async def _send_expo(self, device: Device, notification: Notification) -> PushResult:
        payload = {
            "to": device.push_token,
            "title": notification.title,
            "body": notification.body,
            "data": notification.data,
            "sound": "default",
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if settings.push_gateway_token:
            headers["Authorization"] = f"Bearer {settings.push_gateway_token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(EXPO_PUSH_URL, json=payload, headers=headers)
        if response.is_error:
            raise PushDeliveryError(f"Expo push returned HTTP {response.status_code}", code="HTTP_ERROR")

        body = response.json()
        ticket = body.get("data")
        if isinstance(ticket, list):
            ticket = ticket[0] if ticket else None
        if not isinstance(ticket, dict):
            raise PushDeliveryError("Expo push response did not contain a ticket", code="BAD_RESPONSE")
        if ticket.get("status") != "ok":
            details = ticket.get("details") or {}
            code = details.get("error") if isinstance(details, dict) else None
            raise PushDeliveryError(str(ticket.get("message") or "Expo push rejected message"), code=code)
        message_id = ticket.get("id")
        if not message_id:
            raise PushDeliveryError("Expo push ticket did not contain an id", code="BAD_RESPONSE")
        return PushResult(provider_message_id=str(message_id))

    async def _send_gateway(
        self, url: str, device: Device, notification: Notification
    ) -> PushResult:
        payload = {
            "platform": device.platform.value,
            "token": device.push_token,
            "title": notification.title,
            "body": notification.body,
            "data": notification.data,
        }
        headers = {}
        if settings.push_gateway_token:
            headers["X-Abutron-Push-Token"] = settings.push_gateway_token
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url + "/v1/push", json=payload, headers=headers)
        if response.is_error:
            raise PushDeliveryError(f"Push gateway returned HTTP {response.status_code}", code="HTTP_ERROR")
        body = response.json()
        message_id = body.get("message_id")
        if not message_id:
            raise PushDeliveryError("Push gateway did not return message_id", code="BAD_RESPONSE")
        return PushResult(provider_message_id=str(message_id))
