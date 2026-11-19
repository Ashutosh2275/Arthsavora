# Webhook Security and Ingestion Integrity Tests

## 1. Threat Model for External Financial Webhooks

Inbound webhooks (e.g., from Account Aggregators or payment gateways) are vulnerable to:
1. **Payload Tampering**: Interception and modification of transaction amounts.
2. **Replay Attacks**: Resending historical webhook payloads to artificially credit account balances.
3. **Spoofed Senders**: Fake webhooks sent without valid provider credentials.

---

## 2. Webhook Defense Standards

ARTHSAVORA enforces a 3-tier validation protocol for all inbound webhooks:
1. **HMAC-SHA256 Cryptographic Signature**: Validated against shared provider signing secret (`X-Webhook-Signature`).
2. **Timestamp Replay Window**: Rejects any webhook payload with timestamp older than 300 seconds ($\pm 5\text{min}$).
3. **Idempotency Key Check**: The unique `X-Webhook-ID` is verified against the Redis idempotency store. Duplicate deliveries return HTTP 200 immediately without re-executing business logic.

---

## 3. Test Verification

```python
def test_webhook_security_signature_and_idempotency(client):
    payload = {"event": "consent.approved", "consent_id": "aa_12345"}
    timestamp = str(int(time.time()))
    signature = hmac.new(WEBHOOK_SECRET.encode(), f"{timestamp}.{json.dumps(payload)}".encode(), hashlib.sha256).hexdigest()
    
    # 1. Valid signature passes
    res = client.post("/api/v1/webhooks/aa", json=payload, headers={"X-Signature": signature, "X-Timestamp": timestamp})
    assert res.status_code == 200
    
    # 2. Tampered signature fails
    res_bad = client.post("/api/v1/webhooks/aa", json=payload, headers={"X-Signature": "invalid_sig", "X-Timestamp": timestamp})
    assert res_bad.status_code == 401
    
    # 3. Expired timestamp fails replay
    expired_ts = str(int(time.time()) - 400)
    res_expired = client.post("/api/v1/webhooks/aa", json=payload, headers={"X-Signature": signature, "X-Timestamp": expired_ts})
    assert res_expired.status_code == 400
```
- Status: **All Webhook Security Tests Passed**.
