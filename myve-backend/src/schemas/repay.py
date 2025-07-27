from pydantic import BaseModel
from typing import Optional

class CreditAccount(BaseModel):
    bank_name: str
    balance: float
    limit: Optional[float] = None
    interest_rate: Optional[float] = None
    overdue: Optional[float] = 0.0
