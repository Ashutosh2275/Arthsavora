from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import Annotated
from datetime import datetime

PyObjectId = Annotated[str, BeforeValidator(str)]

class BudgetBase(BaseModel):
    category: str
    limit: float
    month: int = Field(default_factory=lambda: datetime.utcnow().month)
    year: int = Field(default_factory=lambda: datetime.utcnow().year)

class BudgetCreate(BudgetBase):
    pass

class BudgetOut(BudgetBase):
    id: PyObjectId = Field(alias="_id")
    user_id: str

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )