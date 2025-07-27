from pydantic import BaseModel
from typing import Optional, List

class GoalMetadata(BaseModel):
    goal_type: Optional[str]
    amount: Optional[float]
    timeline_months: Optional[int]

class EMIOption(BaseModel):
    tenure: str
    emi: float
    total_payable: float
    interest_paid: float

class PlanMetadata(BaseModel):
    context_used: Optional[bool] = False
    goal: Optional[List[GoalMetadata]] = None  # updated from GoalMetadata to List[GoalMetadata]
    risk_analysis: Optional[str] = None
    emi_options: Optional[List[EMIOption]] = None
    graph_points: Optional[List[dict]] = None

class PlanResponse(BaseModel):
    response: str
    metadata: PlanMetadata