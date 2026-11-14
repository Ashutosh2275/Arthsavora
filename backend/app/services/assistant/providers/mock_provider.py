"""
Arthsavora Mock Deterministic LLM Provider
Deterministic, zero-cost, and offline-capable implementation of the LLM provider abstraction.
Provides robust tool selection, factual financial summarization, and simulated streaming for testing and offline environments.
"""

import asyncio
from datetime import date
import json
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid

from app.domain.assistant import (
    FinancialIntentEnum,
    ModelCapabilities,
    ToolCallVO,
    detect_financial_intent,
)
from app.services.assistant.providers.base_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
)


class MockDeterministicProvider(BaseLLMProvider):
    """
    Deterministic provider providing truthful tool orchestration and natural language generation
    without incurring API costs or requiring external network connections.
    """

    def __init__(self, model_name: str = "mock-fin-v1"):
        self.model_name = model_name

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
            supports_structured_output=True,
            max_context_tokens=16384,
        )

    async def generate_completion(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        # Check if the last message is a tool result
        tool_msgs = [m for m in messages if m.role == "tool"]
        if tool_msgs:
            # Second turn: Synthesize verified backend tool results into natural language response
            latest_tool = tool_msgs[-1]
            try:
                tool_data = json.loads(latest_tool.content)
            except Exception:
                tool_data = {}

            response_text = self._synthesize_tool_response(latest_tool.name or "tool", tool_data)
            return LLMResponse(
                content=response_text,
                tool_calls=[],
                tokens_prompt=len(system_prompt.split()) + 50,
                tokens_completion=len(response_text.split()),
                finish_reason="stop",
                model_name=self.model_name,
            )

        # First turn: Check user query and decide whether to call a financial tool
        user_msgs = [m for m in messages if m.role == "user"]
        if not user_msgs:
            return LLMResponse(
                content="How can I assist you with your finances today?",
                tool_calls=[],
                tokens_prompt=20,
                tokens_completion=10,
                model_name=self.model_name,
            )

        last_user_query = user_msgs[-1].content
        intent_res = detect_financial_intent(last_user_query)

        # Map intent to appropriate tool call
        tool_call = self._map_intent_to_tool(intent_res, last_user_query)
        if tool_call:
            return LLMResponse(
                content="",
                tool_calls=[tool_call],
                tokens_prompt=len(last_user_query.split()) + 30,
                tokens_completion=20,
                finish_reason="tool_calls",
                model_name=self.model_name,
            )

        # Conversational / General help answer if no tool needed
        reply = self._generate_conversational_reply(intent_res, last_user_query)
        return LLMResponse(
            content=reply,
            tool_calls=[],
            tokens_prompt=len(last_user_query.split()) + 20,
            tokens_completion=len(reply.split()),
            finish_reason="stop",
            model_name=self.model_name,
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Simulates streaming by yielding chunks of the completion."""
        completion = await self.generate_completion(messages, system_prompt, tools, temperature, max_tokens)

        # If it decided to call tools, yield tool call in chunk
        if completion.tool_calls:
            for tc in completion.tool_calls:
                yield LLMStreamChunk(tool_call_delta=tc)
            yield LLMStreamChunk(is_finish=True)
            return

        # Otherwise stream text words with minimal latency simulation
        words = completion.content.split(" ")
        for i, word in enumerate(words):
            separator = " " if i > 0 else ""
            yield LLMStreamChunk(delta_text=separator + word)
            await asyncio.sleep(0.005)

        yield LLMStreamChunk(is_finish=True, tokens_completion=len(words))

    # -------------------------------------------------------------------------
    # Intent-to-Tool Mapping & Response Synthesis
    # -------------------------------------------------------------------------

    def _map_intent_to_tool(self, intent_res, query: str) -> Optional[ToolCallVO]:
        dr = intent_res.date_range
        today = date.today()
        s_date = dr.start_date.isoformat() if dr else today.replace(day=1).isoformat()
        e_date = dr.end_date.isoformat() if dr else today.isoformat()
        call_id = f"call_{uuid.uuid4().hex[:8]}"

        # 1. Action intents
        if intent_res.intent == FinancialIntentEnum.ACTION_BUDGET:
            return ToolCallVO(
                call_id=call_id,
                tool_name="create_budget_draft",
                arguments=intent_res.parameters,
            )
        elif intent_res.intent == FinancialIntentEnum.ACTION_GOAL:
            return ToolCallVO(
                call_id=call_id,
                tool_name="create_goal_draft",
                arguments=intent_res.parameters,
            )
        elif intent_res.intent == FinancialIntentEnum.ACTION_RECURRING:
            return ToolCallVO(
                call_id=call_id,
                tool_name="create_recurring_draft",
                arguments=intent_res.parameters,
            )

        # 2. Read-only analytical tools
        if intent_res.intent == FinancialIntentEnum.EXPENSE:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_expense_summary",
                arguments={"start_date": s_date, "end_date": e_date, "currency": intent_res.currency},
            )
        elif intent_res.intent == FinancialIntentEnum.INCOME:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_income_summary",
                arguments={"start_date": s_date, "end_date": e_date, "currency": intent_res.currency},
            )
        elif intent_res.intent == FinancialIntentEnum.CATEGORY:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_category_spending",
                arguments={
                    "start_date": s_date,
                    "end_date": e_date,
                    "category_name": intent_res.category_name,
                    "currency": intent_res.currency,
                },
            )
        elif intent_res.intent == FinancialIntentEnum.MERCHANT:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_merchant_spending",
                arguments={"start_date": s_date, "end_date": e_date, "limit": 10, "currency": intent_res.currency},
            )
        elif intent_res.intent == FinancialIntentEnum.CASH_FLOW:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_cash_flow",
                arguments={"start_date": s_date, "end_date": e_date, "currency": intent_res.currency},
            )
        elif intent_res.intent == FinancialIntentEnum.ACCOUNT:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_account_balances",
                arguments={},
            )
        elif intent_res.intent == FinancialIntentEnum.BUDGET:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_budget_status",
                arguments={"category_name": intent_res.category_name},
            )
        elif intent_res.intent == FinancialIntentEnum.GOAL:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_goal_progress",
                arguments={},
            )
        elif intent_res.intent == FinancialIntentEnum.RECURRING:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_upcoming_commitments",
                arguments={"days_ahead": 14},
            )
        elif intent_res.intent == FinancialIntentEnum.SUBSCRIPTIONS:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_subscription_summary",
                arguments={},
            )
        elif intent_res.intent == FinancialIntentEnum.FORECAST:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_forecast",
                arguments={"horizon_days": 30},
            )
        elif intent_res.intent == FinancialIntentEnum.ANOMALY:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_anomaly_details",
                arguments={"limit": 5},
            )
        elif intent_res.intent == FinancialIntentEnum.TRANSACTIONS:
            return ToolCallVO(
                call_id=call_id,
                tool_name="search_transactions",
                arguments={
                    "start_date": s_date,
                    "end_date": e_date,
                    "min_amount_paise": intent_res.amount_paise,
                    "limit": 10,
                },
            )
        elif intent_res.intent == FinancialIntentEnum.OVERVIEW:
            return ToolCallVO(
                call_id=call_id,
                tool_name="get_financial_overview",
                arguments={"start_date": s_date, "end_date": e_date, "currency": intent_res.currency},
            )

        return None

    def _synthesize_tool_response(self, tool_name: str, data: Dict[str, Any]) -> str:
        """Synthesizes backend tool outputs into factual, structured markdown text."""
        # Action Drafts
        if data.get("is_draft"):
            act_type = data.get("action_type")
            params = data.get("parameters", {})
            if act_type == "create_budget_draft":
                limit_inr = params.get("limit_paise", 0) / 100.0
                return (
                    f"I have prepared a draft budget for **{params.get('name', 'Budget')}** "
                    f"with a spending limit of **₹{limit_inr:,.2f}** ({params.get('period', 'monthly')}).\n\n"
                    f"Please review the action details below and confirm to activate it."
                )
            elif act_type == "create_goal_draft":
                target_inr = params.get("target_amount_paise", 0) / 100.0
                return (
                    f"I have prepared a savings goal draft for **{params.get('name', 'Goal')}** "
                    f"with a target amount of **₹{target_inr:,.2f}**.\n\n"
                    f"Please review the details below and confirm to save this goal."
                )
            elif act_type == "create_recurring_draft":
                amt_inr = params.get("expected_amount_paise", 0) / 100.0
                return (
                    f"I have prepared a recurring payment draft for **{params.get('name', 'Subscription')}** "
                    f"of **₹{amt_inr:,.2f}** ({params.get('frequency', 'monthly')}).\n\n"
                    f"Please review the action below and confirm to activate."
                )

        # Overview
        if tool_name == "get_financial_overview":
            inflow = data.get("total_inflow_rupees", 0.0)
            outflow = data.get("total_outflow_rupees", 0.0)
            net = data.get("net_savings_rupees", 0.0)
            tx_count = data.get("transaction_count", 0)
            savings_rate = data.get("savings_rate_pct", 0.0)
            return (
                f"### Financial Overview\n\n"
                f"- **Total Income (Inflows):** ₹{inflow:,.2f}\n"
                f"- **Total Spending (Outflows):** ₹{outflow:,.2f}\n"
                f"- **Net Savings:** ₹{net:,.2f}\n"
                f"- **Savings Rate:** {savings_rate:.1f}%\n"
                f"- **Total Transactions:** {tx_count}\n\n"
                f"{'You maintained a positive cash flow during this period.' if net >= 0 else 'Spending exceeded inflows during this period.'}"
            )

        # Expenses
        if tool_name == "get_expense_summary":
            total = data.get("total_volume_rupees", 0.0)
            cats = data.get("categories", [])
            lines = [f"### Total Expenses: ₹{total:,.2f}\n"]
            if cats:
                lines.append("| Category | Spent (₹) | % of Total |")
                lines.append("| :--- | :--- | :--- |")
                for c in cats[:5]:
                    lines.append(f"| {c.get('name', 'Other')} | ₹{c.get('total_rupees', 0.0):,.2f} | {c.get('percentage', 0.0):.1f}% |")
            return "\n".join(lines)

        # Income
        if tool_name == "get_income_summary":
            total = data.get("total_volume_rupees", 0.0)
            cats = data.get("categories", [])
            lines = [f"### Total Income: ₹{total:,.2f}\n"]
            if cats:
                for c in cats[:5]:
                    lines.append(f"- **{c.get('name', 'Income')}:** ₹{c.get('total_rupees', 0.0):,.2f} ({c.get('percentage', 0.0):.1f}%)")
            return "\n".join(lines)

        # Category Spending
        if tool_name == "get_category_spending":
            cats = data.get("categories", [])
            if not cats:
                return "No spending recorded in this category during the requested period."
            lines = ["### Category Spending Breakdown\n"]
            lines.append("| Category | Amount (₹) | Share |")
            lines.append("| :--- | :--- | :--- |")
            for c in cats[:8]:
                lines.append(f"| {c.get('name', 'Other')} | ₹{c.get('total_rupees', 0.0):,.2f} | {c.get('percentage', 0.0):.1f}% |")
            return "\n".join(lines)

        # Merchant Spending
        if tool_name == "get_merchant_spending":
            merchants = data.get("merchants", [])
            if not merchants:
                return "No merchant expenditures recorded for this period."
            lines = ["### Top Merchant Expenditures\n"]
            for m in merchants[:5]:
                lines.append(f"- **{m.get('name', 'Unknown')}:** ₹{m.get('total_rupees', 0.0):,.2f} ({m.get('count', 0)} payments)")
            return "\n".join(lines)

        # Account Balances
        if tool_name == "get_account_balances":
            tot = data.get("total_liquid_rupees", 0.0)
            accs = data.get("accounts", [])
            lines = [f"### Total Liquid Balance: ₹{tot:,.2f}\n"]
            for a in accs:
                mask = f" ({a['masked_account_number']})" if a.get("masked_account_number") else ""
                lines.append(f"- **{a['name']}{mask}:** ₹{a['current_balance_rupees']:,.2f} *({a['account_type'].capitalize()})*")
            return "\n".join(lines)

        # Budget Status
        if tool_name == "get_budget_status":
            budgets = data.get("budgets", [])
            if not budgets:
                return "You do not have any active budgets configured yet. Would you like me to prepare a draft budget for you?"
            lines = ["### Active Budgets Status\n"]
            for b in budgets:
                status_str = "⚠️ Overspent" if b["is_overspent"] else "✅ On Track"
                lines.append(
                    f"**{b['name']}** ({b['period_type'].capitalize()}): {status_str}\n"
                    f"- Limit: ₹{b['limit_rupees']:,.2f} | Spent: ₹{b['spent_rupees']:,.2f} | Remaining: ₹{b['remaining_rupees']:,.2f} ({b['utilization_pct']}%)"
                )
            return "\n\n".join(lines)

        # Goal Progress
        if tool_name == "get_goal_progress":
            goals = data.get("goals", [])
            if not goals:
                return "You have no active financial savings goals set up. Would you like me to help create one?"
            lines = ["### Financial Goals Progress\n"]
            for g in goals:
                lines.append(
                    f"- **{g['name']}:** ₹{g['current_saved_rupees']:,.2f} / ₹{g['target_amount_rupees']:,.2f} "
                    f"({g['progress_pct']}%) | Remaining: ₹{g['remaining_rupees']:,.2f}"
                )
            return "\n".join(lines)

        # Upcoming Commitments
        if tool_name == "get_upcoming_commitments":
            tot = data.get("total_upcoming_rupees", 0.0)
            items = data.get("upcoming_commitments", [])
            days = data.get("days_ahead", 14)
            if not items:
                return f"You have no scheduled payments or recurring bills due in the next {days} days."
            lines = [f"### Upcoming Payments (Next {days} Days) — Total: ₹{tot:,.2f}\n"]
            for it in items:
                lines.append(f"- **{it['next_due_date']}:** {it['name']} — ₹{it['expected_amount_rupees']:,.2f} *({it['frequency'].capitalize()})*")
            return "\n".join(lines)

        # Subscriptions
        if tool_name == "get_subscription_summary":
            burn = data.get("monthly_recurring_burn_rupees", 0.0)
            subs = data.get("subscriptions", [])
            if not subs:
                return "You currently have no active subscriptions tracked in this workspace."
            lines = [f"### Active Subscriptions (Monthly Burn: ₹{burn:,.2f})\n"]
            for s in subs:
                lines.append(f"- **{s['name']}:** ₹{s['cycle_amount_rupees']:,.2f} per {s['billing_cycle']} *(₹{s['monthly_equivalent_rupees']:,.2f}/mo)*")
            return "\n".join(lines)

        # Forecast
        if tool_name == "get_forecast":
            inflow = data.get("projected_inflow_rupees", 0.0)
            outflow = data.get("projected_expense_rupees", 0.0)
            net = data.get("projected_net_cash_flow_rupees", 0.0)
            h = data.get("horizon_days", 30)
            return (
                f"### {h}-Day Cash Flow Forecast\n\n"
                f"- **Projected Inflows:** ₹{inflow:,.2f}\n"
                f"- **Projected Expenses:** ₹{outflow:,.2f}\n"
                f"- **Projected Net Cash Flow:** ₹{net:,.2f}\n\n"
                f"> *Note: Projections are model-based statistical estimates based on historical activity and scheduled commitments, not guaranteed financial outcomes.*"
            )

        # Anomalies
        if tool_name == "get_anomaly_details":
            tot = data.get("total_anomalies", 0)
            recent = data.get("recent_anomalies", [])
            if not recent:
                return "No unexpected spending spikes or anomalous transactions detected in recent activity."
            lines = [f"### Detected Anomaly Alerts ({tot} Total)\n"]
            for a in recent:
                lines.append(f"- **[{a['severity'].upper()}]** {a['explanation']} *(Status: {a['status'].replace('_', ' ').capitalize()})*")
            lines.append("\n> *Reminder: An anomaly indicates an unusual statistical deviation, not confirmed fraud.*")
            return "\n".join(lines)

        # Transactions
        if tool_name == "search_transactions":
            txs = data.get("transactions", [])
            if not txs:
                return "No transactions found matching your criteria."
            lines = [f"### Found {len(txs)} Transactions\n"]
            lines.append("| Date | Description | Category | Amount (₹) |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for t in txs:
                lines.append(f"| {t['date']} | {t['description']} | {t.get('category') or '-'} | ₹{t['amount_rupees']:,.2f} |")
            return "\n".join(lines)

        return json.dumps(data, indent=2)

    def _generate_conversational_reply(self, intent_res, query: str) -> str:
        """Answers general conversational or help questions."""
        if intent_res.intent == FinancialIntentEnum.HELP:
            return (
                "### How I Can Help You\n\n"
                "I am your Arthsavora financial assistant. You can ask me:\n"
                "- **Spending Analysis:** *\"How much did I spend this month?\"* or *\"Where is most of my money going?\"*\n"
                "- **Cash Flow & Balances:** *\"What are my account balances?\"* or *\"Show my cash flow trends.\"*\n"
                "- **Budgets & Goals:** *\"Am I likely to exceed my budget?\"* or *\"How much do I need to save for my goal?\"*\n"
                "- **Upcoming Payments:** *\"What payments are due this week?\"* or *\"Which subscriptions are active?\"*\n"
                "- **Forecasts & Risks:** *\"What is my projected cash flow?\"* or *\"Explain recent unusual transactions.\"*\n"
                "- **Safe Actions:** *\"Create a monthly budget of ₹15,000 for groceries.\"* (requires your explicit confirmation)\n"
            )
        return (
            "I can retrieve and analyze your financial transactions, account balances, budgets, "
            "recurring bills, and spending trends. How would you like to explore your finances?"
        )
