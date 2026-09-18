from app.services.webhooks import sign_payload, verify_signature


def test_signed_webhook_accepts_raw_digest():
    secret = "test-secret-that-is-long-enough-for-hmac"
    payload = b'{"event_id":"evt_123"}'
    signature = sign_payload(secret, payload)

    assert verify_signature(secret, payload, signature) is True


def test_signed_webhook_accepts_sha256_prefix():
    secret = "test-secret-that-is-long-enough-for-hmac"
    payload = b'{"event_id":"evt_123"}'
    signature = "sha256=" + sign_payload(secret, payload)

    assert verify_signature(secret, payload, signature) is True


def test_signed_webhook_rejects_tampered_payload():
    secret = "test-secret-that-is-long-enough-for-hmac"
    payload = b'{"event_id":"evt_123"}'
    signature = sign_payload(secret, payload)

    assert verify_signature(secret, b'{"event_id":"evt_999"}', signature) is False
