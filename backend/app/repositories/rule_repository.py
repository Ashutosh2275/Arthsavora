"""
Arthsavora Classification Rule Repository
Manages user-defined and system-wide deterministic classification rules,
priority ordering, and rule lifecycle operations.
"""

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.exceptions import DomainValidationError, InvalidRuleConditionError
from app.infrastructure.database.models.rule import ClassificationRule


class RuleRepository:
    """Manages classification rule persistence, priority ordering, and workspace scoping."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self,
        workspace_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> Optional[ClassificationRule]:
        stmt = (
            select(ClassificationRule)
            .where(
                ClassificationRule.id == rule_id,
                or_(
                    ClassificationRule.workspace_id == workspace_id,
                    ClassificationRule.workspace_id.is_(None),
                ),
            )
            .options(
                selectinload(ClassificationRule.suggested_category),
                selectinload(ClassificationRule.suggested_merchant),
                selectinload(ClassificationRule.created_by),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_rules(
        self,
        workspace_id: uuid.UUID,
        include_disabled: bool = False,
    ) -> List[ClassificationRule]:
        """
        Lists all rules applicable to workspace:
        Both workspace-specific rules and universal system rules,
        ordered strictly by priority DESC (higher precedence first).
        """
        stmt = (
            select(ClassificationRule)
            .where(
                or_(
                    ClassificationRule.workspace_id == workspace_id,
                    ClassificationRule.workspace_id.is_(None),
                )
            )
            .options(
                selectinload(ClassificationRule.suggested_category),
                selectinload(ClassificationRule.suggested_merchant),
            )
        )
        if not include_disabled:
            stmt = stmt.where(ClassificationRule.is_enabled.is_(True))

        stmt = stmt.order_by(
            ClassificationRule.priority.desc(),
            ClassificationRule.created_at.asc(),
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_rule(
        self,
        workspace_id: Optional[uuid.UUID],
        name: str,
        conditions: Dict[str, Any],
        suggested_category_id: uuid.UUID,
        suggested_merchant_id: Optional[uuid.UUID] = None,
        priority: int = 100,
        is_enabled: bool = True,
        rule_scope: str = "workspace",
        created_by_id: Optional[uuid.UUID] = None,
    ) -> ClassificationRule:
        clean_name = name.strip()
        if not clean_name:
            raise DomainValidationError("Rule name cannot be empty.", field="name")

        if not conditions:
            raise InvalidRuleConditionError("Rule must contain at least one valid condition.")

        rule = ClassificationRule(
            workspace_id=workspace_id,
            name=clean_name,
            priority=priority,
            is_enabled=is_enabled,
            rule_scope=rule_scope,
            conditions=conditions,
            suggested_category_id=suggested_category_id,
            suggested_merchant_id=suggested_merchant_id,
            created_by_id=created_by_id,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def update_rule(
        self,
        workspace_id: uuid.UUID,
        rule_id: uuid.UUID,
        name: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None,
        suggested_category_id: Optional[uuid.UUID] = None,
        suggested_merchant_id: Optional[uuid.UUID] = None,
        priority: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> ClassificationRule:
        rule = await self.get_by_id(workspace_id, rule_id)
        if not rule:
            raise DomainValidationError(f"Rule '{rule_id}' not found in workspace.")

        # System rules cannot be mutated by ordinary workspace users
        if rule.workspace_id is None:
            raise DomainValidationError("Universal system rules cannot be modified.")

        if name:
            rule.name = name.strip()
        if conditions is not None:
            if not conditions:
                raise InvalidRuleConditionError("Rule must contain at least one valid condition.")
            rule.conditions = conditions
        if suggested_category_id is not None:
            rule.suggested_category_id = suggested_category_id
        if suggested_merchant_id is not None:
            rule.suggested_merchant_id = suggested_merchant_id
        if priority is not None:
            rule.priority = priority
        if is_enabled is not None:
            rule.is_enabled = is_enabled

        await self.session.flush()
        return rule

    async def delete_rule(
        self,
        workspace_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> None:
        rule = await self.get_by_id(workspace_id, rule_id)
        if not rule or rule.workspace_id != workspace_id:
            return
        await self.session.delete(rule)
        await self.session.flush()
