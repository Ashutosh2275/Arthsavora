from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import Annotated, Optional
from datetime import datetime

PyObjectId = Annotated[str, BeforeValidator(str)]

class GoalBase(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    category: str = "Savings" # e.g., Car, House, Emergency Fund
    deadline: Optional[datetime] = None

class GoalCreate(GoalBase):
    pass

class GoalOut(GoalBase):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    
    # AI Calculated Fields (not stored in DB, calculated on the fly)
    predicted_completion_date: Optional[str] = None
    is_on_track: bool = True

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )