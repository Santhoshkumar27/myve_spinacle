

from pydantic import BaseModel
from typing import Dict, Union, Optional

class SavingsProjection(BaseModel):
    current_monthly_savings: Union[int, float]
    projected_savings_post_purchase: Union[int, float]
    months_to_recover: Optional[int] = None
    alert: Optional[str] = None

class PlanMetadata(BaseModel):
    impact_on_networth: str
    savings_projection: SavingsProjection
    investment_shift: str
    cashflow_change: Optional[str] = None
    monthly_impact: Optional[Dict[str, Union[int, float]]] = None
    recommendation_level: Optional[str] = None