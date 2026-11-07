"""Know the customer: I, F, S, B, H, P (datathon README definitions).

  I = median money_in            F = median(household_bills + insurance + loan_payments)
  S = median money_out           H = median household_bills
  B = mean avg_daily_balance over the last 6 monthly rows
  P = loans.monthly_payment if the loan is still running at end of 2025 (status C or D), else 0
Rows can come from the dataset or from an uploaded statement (Ledger.monthly_summary()).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, median

from services import data_store


@dataclass
class Metrics:
    account_id: str
    months_of_history: int
    income: float            # I
    spending: float          # S
    fixed_costs: float       # F
    household_bills: float   # H
    insurance: float
    loan_payments: float
    loan_payment_active: float  # P
    buffer: float            # B

    def to_dict(self) -> dict:
        return asdict(self)


def _f(v) -> float:
    return float(v) if v not in (None, "") else 0.0


def metrics_from_rows(rows: list[dict], account_id: str = "?", loan: dict | None = None) -> Metrics:
    if not rows:
        raise ValueError("no monthly rows")
    rows = sorted(rows, key=lambda r: r["month"])
    col = lambda k: [_f(r.get(k)) for r in rows]
    fixed = [_f(r.get("household_bills")) + _f(r.get("insurance")) + _f(r.get("loan_payments")) for r in rows]
    last6 = [_f(r["avg_daily_balance"]) for r in rows[-6:] if r.get("avg_daily_balance") not in (None, "")]
    p = float(loan["monthly_payment"]) if loan and loan.get("status") in ("C", "D") else 0.0
    return Metrics(
        account_id=str(account_id), months_of_history=len(rows),
        income=median(col("money_in")), spending=median(col("money_out")),
        fixed_costs=median(fixed), household_bills=median(col("household_bills")),
        insurance=median(col("insurance")), loan_payments=median(col("loan_payments")),
        loan_payment_active=p, buffer=mean(last6) if last6 else 0.0,
    )


def customer_metrics(account_id) -> Metrics:
    return metrics_from_rows(data_store.account_rows(account_id), str(account_id),
                             data_store.account_loan(account_id))
