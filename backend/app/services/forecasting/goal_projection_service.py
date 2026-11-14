"""
Arthsavora Savings Goal Trajectory & Completion Projection Service
Projects goal completion dates based on historical savings pace and target amounts.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.forecasting import calculate_goal_trajectory
from app.repositories.goal_repository import GoalRepository
from app.schemas.forecast_schema import GoalTrajectoryResponse


class GoalProjectionService:
    """Projects future savings velocity and goal completion milestones."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.goal_repo = GoalRepository(db)

    async def get_goal_trajectories(
        self,
        workspace_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> GoalTrajectoryResponse:
        """Projects completion timelines for all active savings goals in the workspace."""
        as_of = as_of_date or date.today()
        goals, _ = await self.goal_repo.list_goals(workspace_id=workspace_id, status="active", limit=50)

        projections: List[Dict[str, Any]] = []

        for g in goals:
            # Derive average monthly contribution pace from past activities
            activities, _ = await self.goal_repo.list_activities(goal_id=g.id, workspace_id=workspace_id, limit=50)
            contributions = [a for a in activities if a.activity_type == "contribution"]
            tot_contributions = sum(c.amount_paise for c in contributions)

            cur_bal = getattr(g, "current_amount_paise", 0)
            days_active = max(1, (as_of - g.created_at.date()).days)
            monthly_pace = int(round(tot_contributions / (days_active / 30.4375))) if days_active >= 15 else (cur_bal or 0)

            # If user has not contributed regularly yet, default to a minimum reasonable pace or 0
            if monthly_pace <= 0 and cur_bal > 0:
                monthly_pace = cur_bal

            traj = calculate_goal_trajectory(
                goal_id=str(g.id),
                goal_name=g.name,
                target_amount_paise=g.target_amount_paise,
                current_balance_paise=cur_bal,
                target_date=g.target_date,
                as_of_date=as_of,
                monthly_savings_pace_paise=monthly_pace,
            )

            projections.append({
                "goal_id": traj.goal_id,
                "goal_name": traj.goal_name,
                "target_amount_paise": traj.target_amount_paise,
                "target_amount": Decimal(traj.target_amount_paise) / Decimal("100.0000"),
                "current_balance_paise": traj.current_balance_paise,
                "current_balance": Decimal(traj.current_balance_paise) / Decimal("100.0000"),
                "remaining_paise": traj.remaining_paise,
                "remaining": Decimal(traj.remaining_paise) / Decimal("100.0000"),
                "target_date": traj.target_date,
                "monthly_savings_pace_paise": traj.monthly_savings_pace_paise,
                "monthly_savings_pace": Decimal(traj.monthly_savings_pace_paise) / Decimal("100.0000"),
                "projected_completion_date": traj.projected_completion_date,
                "is_on_track": traj.is_on_track,
                "status": traj.status,
            })

        return GoalTrajectoryResponse(
            workspace_id=workspace_id,
            as_of_date=as_of,
            goals=projections,
        )
