import logging

class NetWorthAnalyzer:
    def __init__(self, user_id: str, networth_data: dict):
        self.user_id = user_id
        self.networth_data = networth_data

    def analyze(self) -> dict:
        return process_networth_data(self.user_id, self.networth_data)

    def process(self) -> dict:
        return self.analyze()

logger = logging.getLogger(__name__)

def process_networth_data(user_id: str, networth_data: dict) -> dict:
    """
    Processes net worth data and returns detailed metrics.
    """
    try:
        # Fallback: direct netWorth object
        if "netWorth" in networth_data and isinstance(networth_data["netWorth"], dict):
            fallback_units = float(networth_data["netWorth"].get("units", 0))
            result = {
                "user_id": user_id,
                "totalNetWorth": {
                    "raw": fallback_units,
                    "formatted": f"₹{fallback_units:,.0f}"
                },
                "assetBreakdown": {"TOTAL": fallback_units},
                "liabilityBreakdown": {},
                "assetToLiabilityRatio": None
            }
            logger.info(f"[NetWorthProcessor] Fallback processed for user {user_id}")
            return {"summary": result}

        response = networth_data.get("netWorthResponse", {})
        asset_list = response.get("assetValues", [])
        try:
            total_raw_networth = float(response.get("totalNetWorthValue", {}).get("units", 0))
        except (ValueError, TypeError):
            total_raw_networth = 0.0

        assets = {}
        liabilities = {}
        for item in asset_list:
            attr = item.get("netWorthAttribute")
            if not attr or not isinstance(attr, str):
                attr = "UNKNOWN_ASSET"
                logger.warning(f"[NetWorthProcessor] Missing or invalid attribute in item: {item}")

            value_dict = item.get("value", {})
            try:
                value = float(value_dict.get("units", 0))
            except (ValueError, TypeError):
                logger.warning(f"[NetWorthProcessor] Invalid units in item: {item}")
                value = 0.0

            if "LIABILITY" in attr.upper():
                liabilities[attr] = value
            else:
                assets[attr] = value

        asset_total = sum(assets.values())
        liability_total = sum(liabilities.values())
        networth_ratio = round(asset_total / abs(liability_total), 2) if liability_total != 0 else None

        result = {
            "user_id": user_id,
            "totalNetWorth": {
                "raw": total_raw_networth,
                "formatted": f"₹{total_raw_networth:,.0f}"
            },
            "assetBreakdown": assets,
            "liabilityBreakdown": liabilities,
            "assetToLiabilityRatio": networth_ratio
        }

        logger.info(f"[NetWorthProcessor] Processed for user {user_id}")
        return {"summary": result}

    except Exception as e:
        logger.error(f"[NetWorthProcessor] Error processing net worth for {user_id}: {e}")
        return {
            "user_id": user_id,
            "totalNetWorth": {
                "raw": 0,
                "formatted": "₹N/A"
            },
            "assetBreakdown": {},
            "liabilityBreakdown": {},
            "assetToLiabilityRatio": None
        }