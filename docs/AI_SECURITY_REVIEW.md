# ARTHSAVORA — AI Financial Assistant Security & Safety Review

## 1. Overview & Operational Principles

The ARTHSAVORA AI Financial Assistant provides conversational financial intelligence across Personal, Family, and Small Business accounts.

Financial AI assistants present unique security risks:
- Direct and indirect prompt injection attacks.
- Unauthorized tool execution and data exfiltration.
- Hallucinated balances or non-existent transactions.
- Premature or unauthorized mutation of ledger accounts.
- Cross-workspace context leakage.

To mitigate these risks, the AI architecture implements strict operational invariants, pure functional prompt sanitization, allowlisted deterministic tools, and a mandatory human-in-the-loop action confirmation pattern.

---

## 2. Five Operational Invariants

1. **Truthfulness & Exact Financial Precision:** The assistant utilizes verified tool outputs exclusively for financial facts and amounts. It is strictly forbidden from inventing transactions, accounts, or ledger figures.
2. **Zero Autonomous Ledger Mutation:** The LLM cannot directly post to the general ledger, execute funds transfers, or modify database records. State-changing intents are staged as **Action Drafts** requiring explicit human confirmation.
3. **Objective & Non-Alarmist Tone:** Anomaly detection signals are statistical deviations, not confirmed fraud. The assistant communicates findings in calm, neutral language with appropriate context.
4. **Data Privacy & Redaction:** The assistant never outputs raw credentials, full 16-digit account numbers, IFSC codes, or API secrets.
5. **Prompt Injection Defense:** Instructions embedded in transaction notes, receipt OCR extractions, or user queries attempting to override system constraints are systematically neutralized.

---

## 3. Prompt Injection Defense Architecture

### 3.1. Adversarial Pattern Neutralization
User inputs are processed through `sanitize_and_detect_prompt_injection` prior to LLM submission. The sanitizer evaluates inputs against known adversarial injection patterns:
- System delimiter injection (`<system>`, `</system>`, `system:`)
- Instruction overrides (`ignore all previous instructions`, `ignore prior instructions`)
- Prompt extraction attempts (`reveal your system prompt`)
- Jailbreaks (`you are now DAN`)
- Security bypass commands (`bypass security`, `grant all permissions`)
- SQL injection tokens (`drop table`, `select * from`)

If an injection attempt is detected:
1. The request is flagged with an audit explanation.
2. The payload is neutralized to a safe default query (`"Show my financial summary for this month."`).
3. The LLM is shielded from processing adversarial instructions.

### 3.2. Test Evidence
Verified in `test_ai_prompt_injection_neutralization`. All injection variations are successfully flagged and neutralized to safe queries.

---

## 4. Deterministic Tool Registry & Authorization

1. **Allowlisted Execution:** The assistant can only invoke tools explicitly defined in `FINANCIAL_TOOLS` (`backend/app/services/assistant/tool_registry.py`).
2. **Strict Parameter Schemas:** Every tool parameter is validated against typed JSON schemas (Pydantic models) before execution.
3. **Server-Side Authorization:** The `ToolExecutor` validates that the active `WorkspaceContext` possesses the required granular permission (e.g., `Permission.VIEW_TRANSACTIONS`, `Permission.VIEW_ANOMALIES`) before invoking the tool logic.
4. **Tenant Isolation:** All tool queries join against the active `workspace_id`. Cross-workspace tool queries return empty sets or not-found exceptions.
5. **No Direct SQL Execution:** The LLM is never given tools to execute raw SQL statements against PostgreSQL.

---

## 5. Financial Safety Policies & Contextual Disclaimers

The output pipeline enforces regulatory compliance and financial non-speculation via `apply_financial_safety_policy`:
- **Forecast Queries:** Contextual disclaimer automatically appended:
  > *\*Note: Projections are model-based statistical estimates based on historical activity and scheduled commitments, not guaranteed financial outcomes.\**
- **Anomaly Queries:** Neutral reminder automatically appended:
  > *\*Reminder: An anomaly indicates an unusual statistical deviation, not confirmed fraud. Legitimate one-off expenses frequently deviate from baseline patterns.\**

### Test Evidence
Verified in `test_ai_financial_safety_policy_disclaimers`. Disclaimers are attached to predictive and anomaly responses.
