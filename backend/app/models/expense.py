from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import Optional, Annotated
from datetime import datetime

# Helper to handle MongoDB ObjectId as a string
PyObjectId = Annotated[str, BeforeValidator(str)]

class ExpenseBase(BaseModel):
    amount: float
    description: str
    category: str = "Uncategorized"
    date: datetime = Field(default_factory=datetime.utcnow)
    source: str = "Manual"

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseOut(ExpenseBase):
    # This allows us to map MongoDB's _id to id in our API
    id: PyObjectId = Field(alias="_id")
    user_id: str

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )