from pydantic import BaseModel
from typing import Optional

class CreditSummary(BaseModel):
    creditScore: Optional[int] = None
    totalCurrentBalance: Optional[float] = None
    totalCreditLimit: Optional[float] = None
    creditUtilization: Optional[float] = None


class BankSummary(BaseModel):
    averageBalance: Optional[float] = None
    totalCredits: Optional[float] = None
    totalDebits: Optional[float] = None


# SnapshotSummary captures a high-level snapshot of user's financials
class SnapshotSummary(BaseModel):
    income: Optional[float] = None
    expenses: Optional[float] = None
    savings: Optional[float] = None
    debt: Optional[float] = None
    investment_summary: Optional[dict] = None
    networth_composition: Optional[dict] = None
    deduped_asset_map: Optional[dict] = None


# PlanMetadata captures the effect of a plan or purchase on user's financials
class PlanMetadata(BaseModel):
    impact_on_networth: Optional[str] = None  # e.g., "Minor reduction due to purchase"
    savings_projection: Optional[dict] = None  # e.g., {"before": 100000, "after": 85000}
    investment_shift: Optional[str] = None  # e.g., "Pause SIP for 3 months to manage EMI"