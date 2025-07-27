from src.database.json_mongo import (
    fetch_networth,
    fetch_credit,
    fetch_assets,
    fetch_mf_transactions,
    fetch_bank_transactions,
    fetch_stock_transactions,
    fetch_epf_details
    # fetch_monthly_trend  # Monthly trend is generated dynamically below
)

from datetime import datetime
from collections import defaultdict

from loguru import logger

import asyncio
import json

from src.data_processors.networth_processor import NetWorthAnalyzer
from src.data_processors.mf_processor import MutualFundAnalyzer
from src.data_processors.stock_processor import StockAnalyzer
from src.data_processors.credit_processor import CreditReportAnalyzer
from src.data_processors.epf_processor import EPFAnalyzer
from src.data_processors.bank_processor import BankTransactionAnalyzer


class AgentDataOrchestrator:
    def fetch_all_financial_data(self, user_id: str) -> dict:
        logger.info(f"[Orchestrator] Fetching data for user: {user_id}")
        return asyncio.run(self._fetch_async_data(user_id))

    async def _fetch_async_data(self, user_id: str) -> dict:
        networth = await fetch_networth(user_id)
        credit = await fetch_credit(user_id)
        assets = await fetch_assets(user_id)
        mf_txns = await fetch_mf_transactions(user_id)
        bank_txns = await fetch_bank_transactions(user_id)
        bank_analyzer = BankTransactionAnalyzer(user_id=user_id, bank_data={"bankTransactions": bank_txns})
        bank_processed_summary = bank_analyzer.process()
        stock_txns = await fetch_stock_transactions(user_id)
        # Normalize stock data to dict for agent compatibility
        if isinstance(stock_txns, list):
            try:
                stock_txns = {
                    f"stock_{i}": entry for i, entry in enumerate(stock_txns)
                }
                logger.info("[Orchestrator] Normalized stock_txns list to dict format")
            except Exception as e:
                logger.warning(f"[Orchestrator] Failed to normalize stock_txns: {e}")

        # Mutual Fund Summary with safe checks
        mf_summary = {}
        try:
            mf_analyzer = MutualFundAnalyzer(user_id=user_id, mf_data=mf_txns or [])
            mf_summary = mf_analyzer.process()
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to process MF data: {e}")

        # Stock Summary with safe checks
        # Ensure stock_txns is a list of dicts before passing to StockAnalyzer
        if isinstance(stock_txns, dict):
            stock_txns = list(stock_txns.values())
            logger.info("[Orchestrator] Converted stock_txns dict to list of entries")
        elif isinstance(stock_txns, str):
            stock_txns = []
            logger.warning("[Orchestrator] stock_txns was a string. Resetting to empty list.")
        stock_summary = {}
        try:
            stock_summary = StockAnalyzer.analyze(user_id=user_id, stock_data=stock_txns or [])
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to process stock data: {e}")

        # Credit Summary with safe checks
        credit_summary = {}
        try:
            credit_summary = CreditReportAnalyzer.analyze(user_id, credit or {})
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to process credit data: {e}")

        # EPF Summary with safe checks
        epf_data = await fetch_epf_details(user_id)
        epf_summary = {}
        try:
            epf_summary = EPFAnalyzer.analyze(user_id=user_id, epf_data=epf_data or {})
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to process EPF data: {e}")

        # Net Worth Summary with safe checks
        networth_summary = {}
        try:
            networth_analyzer = NetWorthAnalyzer(user_id=user_id, networth_data=networth or {})
            networth_summary = networth_analyzer.process()
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to process net worth data: {e}")

        monthly_trend = self._compute_monthly_trend(mf_txns, stock_txns)

        # === Compute income, expenses, savings, debt ===
        from dateutil.relativedelta import relativedelta
        recent_income = 0
        recent_expenses = 0
        if bank_txns:
            now = datetime.now()
            for acc in bank_txns:
                for txn in acc.get("txns", []):
                    try:
                        if isinstance(txn, list):
                            date_str = txn[2]  # assuming 3rd item is date
                            txn_type = txn[3]  # assuming 4th item is type (1 for credit, 2 for debit, etc.)
                            amount = float(txn[0])  # assuming 1st item is amount
                            txn_type_str = "CREDIT" if txn_type == 1 else "DEBIT"
                        else:
                            date_str = txn.get("txnDate") or txn.get("txn_date")
                            amount_data = txn.get("txnAmount") or {}
                            amount = float(amount_data.get("amount", 0) or 0)
                            txn_type_str = (txn.get("txnType") or txn.get("txn_type") or "").upper()

                        if date_str:
                            date = datetime.strptime(date_str, "%Y-%m-%d")
                            if date >= now - relativedelta(months=3):
                                logger.debug(f"[Income/Expense Parsed] Date: {date}, Amount: {amount}, Type: {txn_type_str}")
                                if txn_type_str == "CREDIT":
                                    recent_income += amount
                                elif txn_type_str == "DEBIT":
                                    recent_expenses += amount
                        else:
                            logger.warning(f"[Income/Expense Debug] Missing txnDate in transaction: {txn}")
                    except Exception as e:
                        logger.warning(f"[Income/Expense Debug] Skipped transaction due to error: {e}")

        # Fallback: If either income or expenses is still zero, try to get from bank summary
        if (recent_income == 0 or recent_expenses == 0) and bank_processed_summary:
            try:
                bank_summary_data = bank_processed_summary.get("summary", {})
                if recent_income == 0:
                    recent_income = float(bank_summary_data.get("totalCredits", 0))
                if recent_expenses == 0:
                    recent_expenses = float(bank_summary_data.get("totalDebits", 0))
                logger.info("[Fallback] Extracted income/expenses from bank summary")
            except Exception as e:
                logger.warning(f"[Fallback Error] Failed to extract income/expenses from bank_summary: {e}")

        # Compute savings from networth assetValues with enhanced fallback-safe parsing
        savings_total = 0
        debt_total = 0
        assets_list = networth.get("netWorthResponse", {}).get("assetValues", [])
        for item in assets_list:
            try:
                logger.debug(f"[NetWorth Raw Item] {item}")
                code = (str(item.get("netWorthAttribute", "") or "UNKNOWN_ASSET")).upper().strip()
                value_data = item.get("value", {})
                value_raw = value_data.get("units", 0)
                value = float(str(value_raw).strip()) if str(value_raw).strip().replace('.', '', 1).isdigit() else 0
                logger.debug(f"[NetWorth Parsed] Code: {code}, Value: {value}")
                if "SAVINGS" in code or "DEPOSIT" in code:
                    savings_total += value
                if "LIABILITY" in code or "CREDIT_CARD" in code:
                    debt_total += abs(value)
            except Exception as e:
                logger.warning(f"[NetWorth Parsing] Skipped malformed asset entry: {e}")

        # Only include EPF and MF balances if not already reflected in assetValues
        epf_balance = float(epf_summary.get("summary", {}).get("total_pf_balance", 0))
        mf_holdings = float(mf_summary.get("summary", {}).get("totalValue", 0))

        epf_already_counted = any(
            (str(item.get("netWorthAttribute", "")).upper().strip() == "EPF_BALANCE")
            for item in assets_list
        )
        mf_already_counted = any(
            (str(item.get("netWorthAttribute", "")).upper().strip() == "MF_BALANCE")
            for item in assets_list
        )

        # === Diagnostic Block for Accurate Accounting ===
        stock_included = any(
            (str(item.get("netWorthAttribute", "")).upper().strip() == "STOCK_BALANCE")
            for item in assets_list
        )

        liabilities = []
        for item in assets_list:
            code = (str(item.get("netWorthAttribute", "") or "")).upper().strip()
            value_raw = item.get("value", {}).get("units", 0)
            try:
                value = float(str(value_raw).strip()) if str(value_raw).strip().replace('.', '', 1).isdigit() else 0
                if "LIABILITY" in code or "CREDIT_CARD" in code or "LOAN" in code:
                    liabilities.append(value)
            except:
                continue

    

        if not epf_already_counted:
            savings_total += epf_balance
            logger.info(f"[Savings] Added EPF balance: {epf_balance}")

        if not mf_already_counted:
            savings_total += mf_holdings
            logger.info(f"[Savings] Added MF holdings: {mf_holdings}")

        if (savings_total == 0 or debt_total == 0) and networth_summary:
            try:
                net_summary_data = networth_summary.get("summary", {})
                if savings_total == 0:
                    savings_total = float(net_summary_data.get("totalNetWorth", {}).get("raw", 0))
                logger.info(f"[Fallback] Used networth_summary for savings_total: {savings_total}")
            except Exception as e:
                logger.warning(f"[Fallback Error] Failed to extract savings from networth_summary: {e}")


        if debt_total == 0:
            try:
                credit_data = credit_summary.get("summary", {})
                debt_from_credit = float(credit_data.get("totalCurrentBalance", 0))
                if debt_from_credit > 0:
                    debt_total += debt_from_credit
            except Exception as e:
                logger.warning(f"[Fallback Error] Failed to extract debt from credit_summary: {e}")

            try:
                epf_data_summary = epf_summary.get("summary", {})
                pension_balance = float(epf_data_summary.get("pension_balance", 0))
                if pension_balance < 0:
                    debt_total += abs(pension_balance)
            except Exception as e:
                logger.warning(f"[Fallback Error] Failed to extract debt from epf_summary: {e}")

            logger.info(f"[Fallback Totals] Final Debt total after fallbacks: {debt_total}")

        # === Investment Summary ===
        try:
            mf_value = float(mf_summary.get("summary", {}).get("totalValue", 0))
            stock_value = float(stock_summary.get("summary", {}).get("total_invested", 0))
            total_investment = mf_value + stock_value
            networth_value = float(networth_summary.get("summary", {}).get("totalNetWorth", {}).get("raw", 0))
            investment_ratio = round((total_investment / networth_value) * 100, 2) if networth_value else 0

            if investment_ratio > 40:
                investment_health = "Strong"
            elif investment_ratio > 20:
                investment_health = "Moderate"
            else:
                investment_health = "Weak"

            # === Net Worth Composition Breakdown ===
            stock_ratio = mf_ratio = epf_ratio = cash_ratio = 0
            try:
                networth_value = float(networth_summary.get("summary", {}).get("totalNetWorth", {}).get("raw", 0))
                if networth_value > 0:
                    stock_ratio = round((stock_value / networth_value) * 100, 2) if stock_value else 0
                    mf_ratio = round((mf_value / networth_value) * 100, 2) if mf_value else 0
                    epf_ratio = round((epf_balance / networth_value) * 100, 2) if epf_balance else 0
                    cash_ratio = round((savings_total / networth_value) * 100, 2) if savings_total else 0

                 
            except Exception as e:
                logger.warning(f"[Net Worth Composition Error] Failed to compute: {e}")

            investment_summary = {
                "total_investment": total_investment,
                "investment_ratio": investment_ratio,
                "investment_health": investment_health
            }

        except Exception as e:
            investment_summary = {}
            stock_ratio = mf_ratio = epf_ratio = cash_ratio = 0
            logger.warning(f"[Investment Summary Error] Failed to compute investment health: {e}")

        # === Deduplicated Asset Map Block ===
        try:
            deduped_asset_map = {}
            # STOCKS
            stocks_val = round(float(stock_summary.get("summary", {}).get("total_invested", 0)), 2)
            deduped_asset_map["STOCKS"] = stocks_val
            # MUTUAL_FUNDS
            if not mf_already_counted:
                mf_val = round(float(mf_summary.get("summary", {}).get("totalValue", 0)), 2)
                deduped_asset_map["MUTUAL_FUNDS"] = mf_val
            # EPF
            if not epf_already_counted:
                epf_val = round(float(epf_summary.get("summary", {}).get("total_pf_balance", 0)), 2)
                deduped_asset_map["EPF"] = epf_val
            # NETWORTH_REPORTED
            networth_val = round(float(networth_summary.get("summary", {}).get("totalNetWorth", {}).get("raw", 0)), 2)
            deduped_asset_map["NETWORTH_REPORTED"] = networth_val
            # CASH_SAVINGS
            cash_value = savings_total
            if not mf_already_counted:
                cash_value -= mf_value
            if not epf_already_counted:
                cash_value -= epf_balance
            deduped_asset_map["CASH_SAVINGS"] = round(cash_value, 2)
            logger.info(f"[Deduplicated Asset Map] {deduped_asset_map}")
        except Exception as e:
            deduped_asset_map = {}
            logger.warning(f"[Deduped Asset Map Error] {e}")

        # logger.debug(f"[Orchestrator] Final returned structure has keys: {list(locals().keys())}")
        # To avoid logging the full return dictionary, only log a summary if needed:
        # logger.debug(f"[Orchestrator] Final returned structure keys: {list({
        #     'networth', 'credit', 'assets', 'mf', 'bank', 'bank_summary', 'stock', 'monthly', 'income', 'expenses', 'savings', 'debt', 'mf_summary', 'stock_summary', 'credit_summary', 'epf_summary', 'networth_summary'
        # })}")
        try:
            logger.info("[Final Summary Snapshot]")
            logger.info(f"📊 Income: {recent_income}")
            logger.info(f"💸 Expenses: {recent_expenses}")
            logger.info(f"💰 Savings: {savings_total}")
        except Exception as e:
            logger.warning(f"[Summary Log Error] Failed to generate final summary log: {e}")

        return {
            "networth": networth,
            "credit": credit,
            "assets": assets,
            "mf": mf_txns,
            "bank": bank_txns,
            "bank_summary": bank_processed_summary,
            "stock": stock_txns,
            "monthly": monthly_trend,
            "income": recent_income,
            "expenses": recent_expenses,
            "savings": savings_total,
            "debt": debt_total,
            "mf_summary": mf_summary,
            "stock_summary": stock_summary,
            "credit_summary": credit_summary,
            "epf_summary": epf_summary,
            "networth_summary": networth_summary,
            "investment_summary": investment_summary,
            "deduped_asset_map": deduped_asset_map,
            "snapshot": {
                "income": recent_income,
                "expenses": recent_expenses,
                "savings": savings_total,
                "debt": debt_total,
                "investment_summary": investment_summary,
                "networth_composition": {
                    "stocks_percent": stock_ratio,
                    "mf_percent": mf_ratio,
                    "epf_percent": epf_ratio,
                    "cash_percent": cash_ratio
                },
                "deduped_asset_map": deduped_asset_map
            },
            "final_snapshot": {
                "income": recent_income,
                "expenses": recent_expenses,
                "savings": savings_total,
                "debt": debt_total,
                "investment_summary": investment_summary,
                "networth_composition": {
                    "stocks_percent": stock_ratio,
                    "mf_percent": mf_ratio,
                    "epf_percent": epf_ratio,
                    "cash_percent": cash_ratio
                },
                "deduped_asset_map": deduped_asset_map
            }
        }
        
    def _compute_monthly_trend(self, mf_data, stock_data):
        def extract_month_value(txns, index):
            monthly = defaultdict(float)
            for txn in txns if isinstance(txns, list) else []:
                for entry in txn.get("txns", []):
                    if len(entry) > index:
                        try:
                            date = datetime.strptime(entry[1], "%Y-%m-%d")
                            key = date.strftime("%Y-%m")
                            amount = float(entry[3]) * float(entry[2])
                            monthly[key] += amount
                        except Exception:
                            continue
            return monthly

        mf_months = extract_month_value(mf_data, 3)
        stock_months = extract_month_value(stock_data, 3)

        combined = defaultdict(float)
        for k, v in mf_months.items():
            combined[k] += v
        for k, v in stock_months.items():
            combined[k] += v

        sorted_months = sorted(combined.items(), key=lambda x: x[0], reverse=True)
        return [{"month": k, "value": v} for k, v in sorted_months[:6]]

    def get_user_data(self, user_id: str) -> dict:
        return self.fetch_all_financial_data(user_id)

