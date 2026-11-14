# ARTHSAVORA — AI Usage, Token Observability and Cost Governance

## 1. Governance Objectives

Enterprise adoption of AI assistants requires transparent cost accounting, token consumption monitoring, and guardrails against runaway usage or abusive loops.

ARTHSAVORA maintains an immutable ledger of all AI invocations in the `assistant_usage_logs` table.

---

## 2. Telemetry Schema & Log Fields

Every assistant turn records the following attributes:

| Field | Type | Description |
| :--- | :--- | :--- |
| `workspace_id` | UUID | Tenant boundary for billing allocation |
| `user_id` | UUID | Requesting user identifier |
| `conversation_id`| UUID | Associated conversation thread |
| `model_provider` | String | Active provider (`mock`, `gemini`, `openai`) |
| `model_name` | String | Model identifier (`mock-fin-v1`, `gemini-1.5-flash`, etc.) |
| `tokens_prompt` | Integer | Prompt token count |
| `tokens_completion`| Integer | Generated completion token count |
| `total_tokens` | Integer | Aggregate turn token consumption |
| `estimated_cost_usd`| Numeric(10, 6) | Blended financial cost estimate in USD |
| `duration_ms` | Integer | Execution latency in milliseconds |
| `tool_count` | Integer | Number of backend financial tools invoked |
| `is_success` | Boolean | Turn execution status |
| `error_category` | String | Categorized error code if failed |
| `created_at` | Timestamp | UTC timestamp of the turn |

---

## 3. Cost Modeling

Cost estimation uses a configurable model pricing matrix. For example:
$$\text{Cost} = (\text{Tokens}_{\text{prompt}} + \text{Tokens}_{\text{completion}}) \times \$0.000002$$

For the `MockDeterministicProvider`, estimated costs are recorded as `$0.000000`.

---

## 4. Usage Aggregation API

Workspace administrators can inspect usage via `GET /api/v1/workspaces/{id}/assistant/usage`:

```json
{
  "success": true,
  "data": {
    "total_requests": 48,
    "total_tokens": 14250,
    "tokens_prompt": 10200,
    "tokens_completion": 4050,
    "estimated_cost_usd": 0.0285,
    "avg_latency_ms": 185
  },
  "message": "Usage metrics retrieved successfully."
}
```

---

## 5. Security & Privacy Safeguards
- **Zero Raw Prompt Logging**: To protect client privacy, raw user prompts, transaction descriptions, and full assistant responses are never duplicated in `assistant_usage_logs`. Only token counts and high-level tool names are recorded.
- **Tenant Aggregation Isolation**: Usage metrics are strictly scoped to the caller's active workspace ID.
