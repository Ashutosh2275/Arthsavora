# ARTHSAVORA — Tool Orchestration Security & Execution Boundaries

## 1. Threat Model & Security Posture

Orchestrating tools with Large Language Models introduces unique architectural risks:
1. **Tool Impersonation / Parameter Tampering**: Malicious prompts attempting to invoke backend tools with elevated privileges or cross-tenant parameters.
2. **Data Exfiltration / Excessive Data Retrieval**: Tools returning unbounded result sets containing confidential client records or credentials.
3. **Ledger Contamination**: Autonomous agent tools executing state mutations without explicit human authorization.
4. **Indirect Prompt Injection**: Hostile instructions embedded in transaction notes, counterparty names, or merchant descriptions intended to hijack LLM behavior.

ARTHSAVORA defends against these risks through **Multi-Layered Tool Sandboxing**.

---

## 2. Invariant Security Controls

```
               [ User Input / LLM Turn ]
                          │
                          ▼
             ┌─────────────────────────┐
             │ Layer 1: Tool Filter    │ ➔ Exposes only permitted tools
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ Layer 2: Permission     │ ➔ Re-checks user permissions server-side
             │          Gatekeeper     │
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ Layer 3: Tenant Bound   │ ➔ Locks all SQL queries to workspace_id
             │          Enforcement    │
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ Layer 4: Bounded Limits │ ➔ Caps transaction queries to max 25 rows
             │          & PII Redaction│ ➔ Masks bank account numbers (e.g. •••• 4512)
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ Layer 5: Zero Direct    │ ➔ Mutations require ActionDraft + Token
             │          Mutation Gate  │
             └─────────────────────────┘
```

---

## 3. Server-Side Permission Verification

Permissions are evaluated twice:
1. **Pre-flight Tool Advertisement**: Only tools permitted for the user's role are passed to the model prompt.
2. **Execution-Time Guard**: `ToolExecutor.execute_tool()` validates `tool_def.required_permission in user_permissions` before dispatching to any database query. Hallucinated or injected tool calls are immediately rejected with `Permission denied`.

---

## 4. Sensitive Data Masking & PII Redaction

Financial data returned by tools is sanitized before being passed into the LLM context:
- **Account Numbers**: Truncated to the last 4 digits (e.g., `•••• 4812`).
- **Cryptographic Secrets & API Keys**: Stripped from any model input.
- **Query Bounds**: Transaction listings are hard-capped at 25 items to prevent model context flooding and bulk data exfiltration.

---

## 5. Controlled Human-in-the-Loop Action Confirmation

State mutations adhere to a strict asynchronous proposal-confirmation lifecycle:
1. Tool `create_budget_draft` (or goal/recurring) records an `AssistantActionDraft` with status `pending_confirmation`.
2. A cryptographically secure 256-bit token (`secrets.token_urlsafe(32)`) is generated and associated with a 24-hour expiration window.
3. The mutation is committed to the database **only** when the user calls `POST /api/v1/workspaces/{id}/assistant/actions/{action_id}/confirm` with the valid confirmation token.
4. Multiple confirmation requests are idempotent; secondary attempts return `already_confirmed` without creating duplicate records.
