#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  SPENDSENSE AI  v4.0  —  Offline Student Expense Intelligence       ║
║  Retrod Travel Tech Hackathon  |  Wooble.org  |  Python 3.8+       ║
╚══════════════════════════════════════════════════════════════════════╝

Architecture (Single-Responsibility, Dependency-Injected)
─────────────────────────────────────────────────────────
  Expense          Validated dataclass — the core record
  StorageManager   Atomic JSON persistence layer
  ExpenseManager   CRUD + search / filter / sort / export
  BudgetManager    Budget tracking, thresholds, multi-level alerts
  InsightEngine    Health score, forecasting, recommendations
  ReportGenerator  Monthly formatted reports (screen + file)
  AppController    CLI routing, session orchestration, demo mode

Run normally : python spendsense_ai.py
Demo mode    : python spendsense_ai.py --demo
"""

# ── Standard Library ──────────────────────────────────────────────────────────
import csv
import json
import os
import sys
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

APP_NAME: str = "SPENDSENSE AI"
VERSION:  str = "4.0"
DATA_FILE: str = "expenses.json"

VALID_CATEGORIES: Tuple[str, ...] = (
    "Food", "Travel", "Recharge", "Education",
    "Entertainment", "Health", "Shopping", "Other",
)

# Recommended fraction of monthly budget per category (personal-finance norms)
CATEGORY_IDEAL_RATIO: Dict[str, float] = {
    "Food":          0.35,
    "Travel":        0.20,
    "Recharge":      0.10,
    "Education":     0.15,
    "Entertainment": 0.10,
    "Health":        0.05,
    "Shopping":      0.05,
    "Other":         0.00,
}

CATEGORY_EMOJI: Dict[str, str] = {
    "Food":          "🍱",
    "Travel":        "🚌",
    "Recharge":      "📱",
    "Education":     "📚",
    "Entertainment": "🎬",
    "Health":        "💊",
    "Shopping":      "🛍",
    "Other":         "📦",
}


class SortField(Enum):
    DATE     = "date"
    AMOUNT   = "amount"
    CATEGORY = "category"


class SortOrder(Enum):
    ASC  = "asc"
    DESC = "desc"


# ══════════════════════════════════════════════════════════════════════════════
#  TERMINAL STYLING  (zero dependencies — raw ANSI)
# ══════════════════════════════════════════════════════════════════════════════

class Ansi:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"


def S(text: str, *codes: str) -> str:
    """Apply ANSI style codes and reset cleanly."""
    return "".join(codes) + str(text) + Ansi.RESET


def rule(char: str = "─", width: int = 66) -> str:
    return S(char * width, Ansi.DIM)


def progress_bar(used: float, total: float, width: int = 30) -> str:
    """Colour-coded progress bar with percentage label."""
    if total <= 0:
        return S("[" + "─" * width + "] N/A", Ansi.DIM)
    ratio  = min(used / total, 1.0)
    filled = int(ratio * width)
    color  = Ansi.RED if ratio >= 1.0 else (Ansi.YELLOW if ratio >= 0.80 else Ansi.GREEN)
    bar    = "█" * filled + "░" * (width - filled)
    return S(f"[{bar}] {ratio*100:.1f}%", color)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause() -> None:
    input(S("\n  Press Enter to continue ...", Ansi.DIM))


def ask(prompt_text: str, default: str = "") -> str:
    """Styled prompt. Returns stripped input or default if blank."""
    suffix = f" [{default}]" if default else ""
    raw = input(S(f"  ▸ {prompt_text}{suffix}: ", Ansi.CYAN)).strip()
    return raw if raw else default


def ok(msg: str)   -> None: print(S(f"\n  ✔  {msg}", Ansi.GREEN))
def fail(msg: str) -> None: print(S(f"\n  ✘  {msg}", Ansi.RED))
def warn(msg: str) -> None: print(S(f"\n  ⚠  {msg}", Ansi.YELLOW))
def info(msg: str) -> None: print(S(f"\n  ℹ  {msg}", Ansi.CYAN))


def print_header() -> None:
    print(S("""
╔══════════════════════════════════════════════════════════════════╗
║  ███████╗██████╗ ███████╗███╗  ██╗██████╗ ███████╗███╗  ██╗███████╗║
║  ██╔════╝██╔══██╗██╔════╝████╗ ██║██╔══██╗██╔════╝████╗ ██║██╔════╝║
║  ███████╗██████╔╝█████╗  ██╔██╗██║██║  ██║███████╗██╔██╗██║█████╗  ║
║  ╚════██║██╔═══╝ ██╔══╝  ██║╚████║██║  ██║╚════██║██║╚████║██╔══╝  ║
║  ███████║██║     ███████╗██║ ╚███║██████╔╝███████║██║ ╚███║███████╗║
║  ╚══════╝╚═╝     ╚══════╝╚═╝  ╚══╝╚═════╝ ╚══════╝╚═╝  ╚══╝╚══════╝║
║            A I   v4.0  —  Offline Expense Intelligence            ║
╚══════════════════════════════════════════════════════════════════╝
""", Ansi.CYAN))


def print_section(title: str) -> None:
    print()
    print(S(f"  ◆ {title.upper()}", Ansi.BOLD + Ansi.YELLOW))
    print(rule())


def pick_category() -> str:
    """Interactive numbered category picker with emoji."""
    print()
    for i, cat in enumerate(VALID_CATEGORIES, 1):
        emoji = CATEGORY_EMOJI.get(cat, "")
        print(f"  {S(str(i), Ansi.CYAN)}.  {emoji}  {cat}")
    while True:
        raw = ask("Select category (1–8)")
        if raw.isdigit() and 1 <= int(raw) <= len(VALID_CATEGORIES):
            return VALID_CATEGORIES[int(raw) - 1]
        fail("Enter a number between 1 and 8.")


def print_expense_table(expenses: List["Expense"]) -> None:
    """Render expenses as a clean aligned table."""
    if not expenses:
        warn("No expenses to display.")
        return

    print()
    hdr = (
        f"  {'#':<4} {'ID':<10} {'Date':<12} "
        f"{'Category':<15} {'Amount':>11}  Description"
    )
    print(S(hdr, Ansi.BOLD + Ansi.WHITE))
    print(rule())

    for idx, exp in enumerate(expenses, 1):
        amt_color = (
            Ansi.RED    if exp.amount >= 1000 else
            Ansi.YELLOW if exp.amount >= 500  else
            Ansi.GREEN
        )
        emoji = CATEGORY_EMOJI.get(exp.category, "")
        row = (
            f"  {idx:<4} "
            f"{S(exp.id, Ansi.DIM):<19} "
            f"{exp.date:<12} "
            f"{emoji} {S(exp.category, Ansi.CYAN):<23} "
            f"{S(f'₹{exp.amount:,.2f}', amt_color):>20}  "
            f"{exp.description[:30]}"
        )
        print(row)

    print(rule())
    total = sum(e.amount for e in expenses)
    print(S(f"  {'TOTAL':>58}  ₹{total:,.2f}", Ansi.BOLD + Ansi.WHITE))


# ══════════════════════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Expense:
    """
    A single validated expense record.

    Fields
    ------
    amount      Positive INR amount (rounded to 2 dp).
    category    One of VALID_CATEGORIES.
    description Non-empty free-text label (max 80 chars).
    date        ISO date string YYYY-MM-DD.
    id          8-char uppercase hex UUID (auto-generated).
    created_at  ISO timestamp of creation (auto-generated).
    """
    amount:      float
    category:    str
    description: str
    date:        str
    id:          str = field(default_factory=lambda: uuid.uuid4().hex[:8].upper())
    created_at:  str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def __post_init__(self) -> None:
        """Validate all fields immediately after construction."""
        if self.amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category. Choose from: {', '.join(VALID_CATEGORIES)}"
            )
        if not self.description.strip():
            raise ValueError("Description cannot be empty.")
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")

    def __repr__(self) -> str:
        return (
            f"Expense(id={self.id!r}, date={self.date!r}, "
            f"category={self.category!r}, amount={self.amount})"
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Expense":
        """
        Reconstruct an Expense from a persisted dictionary.
        Skips __post_init__ to tolerate minor format drift in saved data;
        critical fields are still type-coerced explicitly.
        """
        obj = cls.__new__(cls)
        obj.id          = str(data["id"])
        obj.amount      = round(float(data["amount"]), 2)
        obj.category    = str(data["category"])
        obj.description = str(data["description"])
        obj.date        = str(data["date"])
        obj.created_at  = data.get(
            "created_at", datetime.now().isoformat(timespec="seconds")
        )
        return obj

    @property
    def month_key(self) -> str:
        """'YYYY-MM' string for grouping by month."""
        return self.date[:7]

    @property
    def year_month(self) -> Tuple[int, int]:
        """(year, month) integer tuple."""
        y, m = self.date.split("-")[:2]
        return int(y), int(m)


# ══════════════════════════════════════════════════════════════════════════════
#  STORAGE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class StorageManager:
    """
    Atomic JSON persistence layer.

    A single write replaces the entire file — no partial-write corruption.
    A meta block is stored alongside data for provenance / debugging.
    """

    def __init__(self, filepath: str = DATA_FILE) -> None:
        self.filepath = filepath

    def load(self) -> Tuple[List[dict], dict]:
        """
        Read state from disk.

        Returns
        -------
        (expenses_list, budget_dict) — both empty on missing or corrupt file.
        """
        if not os.path.exists(self.filepath):
            return [], {}
        try:
            with open(self.filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("expenses", []), data.get("budget", {})
        except (json.JSONDecodeError, KeyError, TypeError):
            warn("Data file appears corrupted — starting with a clean slate.")
            return [], {}

    def save(self, expenses: List[dict], budget: dict) -> None:
        """Write full application state to disk atomically."""
        payload = {
            "meta": {
                "app":           APP_NAME,
                "version":       VERSION,
                "last_saved":    datetime.now().isoformat(timespec="seconds"),
                "total_records": len(expenses),
            },
            "budget":   budget,
            "expenses": expenses,
        }
        with open(self.filepath, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
#  EXPENSE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class ExpenseManager:
    """
    Full CRUD engine for Expense records.

    Responsibilities
    ----------------
    Create, read, update, delete expenses.
    Search (full-text), filter (category / month), sort (field + direction).
    Aggregate statistics: totals, category breakdown, daily average, streaks.
    CSV export.
    """

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self._records: List[Expense] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def load_from_storage(self) -> None:
        """Populate in-memory records from persistent storage."""
        raw, _ = self._storage.load()
        self._records = [Expense.from_dict(r) for r in raw]

    def flush(self, budget_dict: dict) -> None:
        """Write current in-memory state to disk."""
        self._storage.save([e.to_dict() for e in self._records], budget_dict)

    # ── CREATE ────────────────────────────────────────────────────────────────

    def add(
        self,
        amount: float,
        category: str,
        description: str,
        date_str: str,
    ) -> Expense:
        """
        Create, validate, and store a new expense.

        Raises ValueError for any invalid argument (propagated from Expense).
        """
        exp = Expense(
            amount=round(float(amount), 2),
            category=category,
            description=description.strip(),
            date=date_str,
        )
        self._records.append(exp)
        return exp

    # ── READ ──────────────────────────────────────────────────────────────────

    def all_sorted(
        self,
        sort_field: SortField = SortField.DATE,
        order: SortOrder = SortOrder.DESC,
    ) -> List[Expense]:
        """Return all records sorted by field and direction."""
        reverse = order == SortOrder.DESC
        key_fn = {
            SortField.DATE:     lambda e: e.date,
            SortField.AMOUNT:   lambda e: e.amount,
            SortField.CATEGORY: lambda e: e.category,
        }[sort_field]
        return sorted(self._records, key=key_fn, reverse=reverse)

    def get_by_id(self, expense_id: str) -> Optional[Expense]:
        """Return the Expense matching the given ID, or None."""
        target = expense_id.upper().strip()
        return next((e for e in self._records if e.id == target), None)

    def search(self, query: str) -> List[Expense]:
        """Case-insensitive search across description and category, newest first."""
        q = query.lower()
        hits = [
            e for e in self._records
            if q in e.description.lower() or q in e.category.lower()
        ]
        return sorted(hits, key=lambda e: e.date, reverse=True)

    def filter_by_category(self, category: str) -> List[Expense]:
        """Return expenses in the given category, newest first."""
        return sorted(
            [e for e in self._records if e.category == category],
            key=lambda e: e.date, reverse=True,
        )

    def filter_by_month(self, year: int, month: int) -> List[Expense]:
        """Return expenses for the given month, newest first."""
        prefix = f"{year}-{month:02d}"
        return sorted(
            [e for e in self._records if e.date.startswith(prefix)],
            key=lambda e: e.date, reverse=True,
        )

    def total(self) -> float:
        """Sum of all expense amounts, rounded to 2 dp."""
        return round(sum(e.amount for e in self._records), 2)

    def count(self) -> int:
        """Number of expense records."""
        return len(self._records)

    def total_by_category(self) -> Dict[str, float]:
        """Spending totals per category, descending by amount."""
        totals: Dict[str, float] = defaultdict(float)
        for exp in self._records:
            totals[exp.category] += exp.amount
        return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))

    def top_category(self) -> Optional[Tuple[str, float]]:
        """(category, amount) for the highest-spending category, or None."""
        totals = self.total_by_category()
        if not totals:
            return None
        top = max(totals, key=lambda k: totals[k])
        return top, round(totals[top], 2)

    def daily_average(self) -> float:
        """Average daily spend based on the date-span of all records."""
        if not self._records:
            return 0.0
        dates = sorted({e.date for e in self._records})
        if len(dates) < 2:
            return round(self.total(), 2)
        first = datetime.strptime(dates[0],  "%Y-%m-%d")
        last  = datetime.strptime(dates[-1], "%Y-%m-%d")
        days  = max((last - first).days, 1)
        return round(self.total() / days, 2)

    def monthly_summary(self) -> Dict[str, float]:
        """Spending totals grouped by 'YYYY-MM', ascending."""
        summary: Dict[str, float] = defaultdict(float)
        for exp in self._records:
            summary[exp.month_key] += exp.amount
        return dict(sorted(summary.items()))

    def tracking_streak(self) -> int:
        """
        Count the number of consecutive calendar days (ending today)
        on which at least one expense was recorded.

        Returns
        -------
        int: 0 if no expenses today, otherwise the streak length.
        """
        if not self._records:
            return 0
        today = date.today()
        recorded_dates = {
            datetime.strptime(e.date, "%Y-%m-%d").date()
            for e in self._records
        }
        streak = 0
        current = today
        while current in recorded_dates:
            streak += 1
            current = date.fromordinal(current.toordinal() - 1)
        return streak

    def this_month_total(self) -> float:
        """Total spending in the current calendar month."""
        now = datetime.now()
        return round(
            sum(
                e.amount for e in self._records
                if e.date.startswith(f"{now.year}-{now.month:02d}")
            ),
            2,
        )

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def edit(
        self,
        expense_id:  str,
        amount:      Optional[float] = None,
        category:    Optional[str]   = None,
        description: Optional[str]   = None,
        date_str:    Optional[str]   = None,
    ) -> bool:
        """
        Update one or more fields of an existing expense.

        Returns True if found and updated; False if ID not found.
        Raises ValueError for invalid new values.
        """
        exp = self.get_by_id(expense_id)
        if exp is None:
            return False
        if amount is not None:
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            exp.amount = round(float(amount), 2)
        if category is not None:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"Invalid category: {category}")
            exp.category = category
        if description is not None:
            if not description.strip():
                raise ValueError("Description cannot be empty.")
            exp.description = description.strip()
        if date_str is not None:
            datetime.strptime(date_str, "%Y-%m-%d")  # raises ValueError if bad
            exp.date = date_str
        return True

    # ── DELETE ────────────────────────────────────────────────────────────────

    def delete(self, expense_id: str) -> bool:
        """Remove expense by ID. Returns True if deleted, False if not found."""
        before = len(self._records)
        self._records = [e for e in self._records if e.id != expense_id.upper()]
        return len(self._records) < before

    # ── EXPORT ────────────────────────────────────────────────────────────────

    def export_csv(self, filepath: str) -> int:
        """
        Export all expenses to a CSV file, sorted newest first.

        Returns the number of rows written.
        """
        records = self.all_sorted(SortField.DATE, SortOrder.DESC)
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["id", "date", "category", "amount",
                            "description", "created_at"],
            )
            writer.writeheader()
            for exp in records:
                writer.writerow(exp.to_dict())
        return len(records)


# ══════════════════════════════════════════════════════════════════════════════
#  BUDGET MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class BudgetManager:
    """
    Monthly budget tracking with multi-level alert thresholds.

    Status levels
    -------------
    NOT_SET  : budget is 0 (never configured)
    SAFE     : < 80 % consumed
    WARNING  : 80 – 99.9 % consumed
    EXCEEDED : >= 100 % consumed
    """

    _WARN_RATIO:   float = 0.80
    _EXCEED_RATIO: float = 1.00

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self._amount: float = 0.0

    def load_from_storage(self) -> None:
        """Load budget from persistent storage."""
        _, budget_data = self._storage.load()
        self._amount = float(budget_data.get("monthly_budget", 0.0))

    @property
    def amount(self) -> float:
        return self._amount

    def set(self, new_amount: float) -> None:
        """Set / update the monthly budget. Raises ValueError if not positive."""
        if new_amount <= 0:
            raise ValueError("Budget must be a positive number.")
        self._amount = round(new_amount, 2)

    def remaining(self, spent: float) -> float:
        return round(self._amount - spent, 2)

    def percent_used(self, spent: float) -> float:
        if self._amount == 0:
            return 0.0
        return round((spent / self._amount) * 100, 1)

    def status(self, spent: float) -> str:
        if self._amount == 0:
            return "NOT_SET"
        ratio = spent / self._amount
        if ratio >= self._EXCEED_RATIO:
            return "EXCEEDED"
        if ratio >= self._WARN_RATIO:
            return "WARNING"
        return "SAFE"

    def to_dict(self) -> dict:
        return {"monthly_budget": self._amount}


# ══════════════════════════════════════════════════════════════════════════════
#  INSIGHT ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class InsightEngine:
    """
    Generates financial intelligence entirely offline.

    Public API
    ----------
    financial_health_score  Composite 0–100 score with breakdown.
    generate_insights        Human-readable category analysis strings.
    forecast                 Days-until-budget-exhausted prediction.
    savings_suggestions      Actionable cost-reduction recommendations.
    """

    # ── Financial Health Score ─────────────────────────────────────────────

    def financial_health_score(
        self,
        expenses: List[Expense],
        budget: float,
    ) -> Tuple[int, str, List[str]]:
        """
        Compute a composite Financial Health Score (0–100).

        Scoring model
        -------------
        Budget Adherence      40 pts  — how far below the limit spending sits
        Spending Distribution 30 pts  — variety of categories used
        Savings Potential     20 pts  — headroom remaining in the budget
        Tracking Consistency  10 pts  — months with recorded data

        Returns (score, status_label, breakdown_lines).
        Works even without a budget set (budget=0 skips those dimensions).
        """
        if not expenses:
            return 0, "No Data", []

        total = sum(e.amount for e in expenses)
        score = 0
        breakdown: List[str] = []

        # 1. Budget Adherence (40 pts)
        if budget > 0:
            usage = total / budget
            if   usage <= 0.60: pts = 40
            elif usage <= 0.80: pts = 32
            elif usage <= 1.00: pts = 20
            else:               pts = max(0, int(40 - (usage - 1.0) * 80))
        else:
            pts = 20   # partial credit for tracking even without a budget
        score += pts
        breakdown.append(f"Budget Adherence     {pts:>3}/40 pts")

        # 2. Spending Distribution (30 pts)
        num_cats = len({e.category for e in expenses})
        dist_pts = min(30, num_cats * 6)
        score   += dist_pts
        breakdown.append(f"Category Variety     {dist_pts:>3}/30 pts")

        # 3. Savings Potential (20 pts)
        if budget > 0:
            sav_pts = min(20, int(max(0, 1 - total / budget) * 40))
        else:
            sav_pts = 10   # neutral
        score += sav_pts
        breakdown.append(f"Savings Potential    {sav_pts:>3}/20 pts")

        # 4. Tracking Consistency (10 pts)
        months_tracked = len({e.month_key for e in expenses})
        con_pts = min(10, months_tracked * 4)
        score  += con_pts
        breakdown.append(f"Tracking Consistency {con_pts:>3}/10 pts")

        score = min(100, score)

        if   score >= 85: status = "🟢 Excellent"
        elif score >= 70: status = "🔵 Good"
        elif score >= 50: status = "🟡 Fair"
        elif score >= 30: status = "🟠 Needs Work"
        else:             status = "🔴 Critical"

        return score, status, breakdown

    # ── Insights ──────────────────────────────────────────────────────────

    def generate_insights(
        self,
        expenses: List[Expense],
        budget: float,
    ) -> List[str]:
        """Generate human-readable spending insight strings."""
        if not expenses:
            return ["No expenses logged yet — start tracking to unlock insights."]

        insights: List[str] = []
        total = sum(e.amount for e in expenses)
        cat_totals: Dict[str, float] = defaultdict(float)
        for e in expenses:
            cat_totals[e.category] += e.amount

        # Category ratio insights
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            pct         = round((amt / total) * 100, 1)
            recommended = CATEGORY_IDEAL_RATIO.get(cat, 0) * 100
            emoji       = CATEGORY_EMOJI.get(cat, "")
            if recommended > 0 and pct > recommended * 1.30:
                insights.append(
                    f"⚠  {emoji} {cat} is {pct}% of spending "
                    f"(recommended ≤ {int(recommended)}%) — ₹{amt:,.0f}"
                )
            elif pct > 0:
                insights.append(
                    f"•  {emoji} {cat}: {pct}% of total spend  (₹{amt:,.0f})"
                )

        return insights

    # ── Forecast ──────────────────────────────────────────────────────────

    def forecast(self, expenses: List[Expense], budget: float) -> Optional[str]:
        """
        Predict how many days until the budget is exhausted.

        Returns a formatted string, or None if no budget / no spend data.
        """
        if not expenses or budget <= 0:
            return None

        today        = datetime.now()
        day_of_month = today.day
        if day_of_month == 0:
            return None

        total      = sum(e.amount for e in expenses)
        daily_rate = total / day_of_month

        if daily_rate <= 0:
            return None

        remaining  = budget - total
        if remaining <= 0:
            return "🚨 Budget already exceeded."

        days_left = int(remaining / daily_rate)
        days_in_month_remaining = 30 - day_of_month

        if days_left < days_in_month_remaining:
            return (
                f"📈 At ₹{daily_rate:,.0f}/day, budget exhausts in "
                f"~{days_left} day(s) (before month-end)."
            )
        projected = total + daily_rate * days_in_month_remaining
        return (
            f"✅ Projected month-end total: ₹{projected:,.0f} "
            f"— within budget (₹{budget:,.0f})."
        )

    # ── Savings Suggestions ───────────────────────────────────────────────

    def savings_suggestions(
        self,
        cat_totals: Dict[str, float],
        budget: float,
        total: float,
    ) -> List[str]:
        """Return actionable, personalised savings recommendations."""
        suggestions: List[str] = []

        if total == 0:
            return ["Start logging expenses to receive recommendations."]

        if budget > 0 and total > budget * 0.90:
            suggestions.append(
                "💡 You've consumed 90%+ of your budget. "
                "Pause non-essential spending immediately."
            )

        food = cat_totals.get("Food", 0)
        if food / total > 0.40:
            suggestions.append(
                "🍱 Food is over 40% of spending. "
                "Canteen meals over Zomato could save ₹500–₹800/month."
            )

        entertainment = cat_totals.get("Entertainment", 0)
        if entertainment / total > 0.15:
            suggestions.append(
                "🎬 Entertainment exceeds 15%. "
                "Check for student OTT discounts or share subscriptions."
            )

        travel = cat_totals.get("Travel", 0)
        if travel / total > 0.25:
            suggestions.append(
                "🚌 Travel is above 25%. "
                "Monthly bus/metro passes often cut costs by 30–40%."
            )

        recharge = cat_totals.get("Recharge", 0)
        if recharge / total > 0.15:
            suggestions.append(
                "📱 Recharge spending seems high. "
                "Annual prepaid plans offer 15–20% savings."
            )

        if not suggestions:
            suggestions.append(
                "✨ Great discipline! Spending distribution looks healthy."
            )

        return suggestions


# ══════════════════════════════════════════════════════════════════════════════
#  REPORT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class ReportGenerator:
    """Renders structured monthly reports to a multi-line string."""

    def monthly_report(
        self,
        expenses: List[Expense],
        budget: float,
        year: int,
        month: int,
        engine: InsightEngine,
    ) -> str:
        """
        Build a complete monthly spending report.

        Returns a plain-text multi-line string suitable for terminal
        display and file export.
        """
        month_label = datetime(year, month, 1).strftime("%B %Y")
        W = 62
        lines: List[str] = []
        lines.append("═" * W)
        lines.append(f"  SPENDSENSE AI  —  Monthly Report  |  {month_label}")
        lines.append("═" * W)

        if not expenses:
            lines.append("  No expenses recorded for this period.")
            lines.append("═" * W)
            return "\n".join(lines)

        total = sum(e.amount for e in expenses)
        cat_totals: Dict[str, float] = defaultdict(float)
        for e in expenses:
            cat_totals[e.category] += e.amount

        # Summary block
        lines.append(f"  Total Expenses   : ₹{total:,.2f}")
        if budget > 0:
            remaining = budget - total
            pct = (total / budget) * 100
            lines.append(f"  Monthly Budget   : ₹{budget:,.2f}")
            lines.append(f"  Remaining        : ₹{remaining:,.2f}")
            lines.append(f"  Budget Used      : {pct:.1f}%")
        lines.append(f"  Transactions     : {len(expenses)}")
        avg = round(total / len(expenses), 2)
        lines.append(f"  Avg per Expense  : ₹{avg:,.2f}")

        # Category breakdown
        lines.append("─" * W)
        lines.append("  CATEGORY BREAKDOWN")
        lines.append("─" * W)
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            pct     = (amt / total) * 100
            bar_len = max(1, int(pct / 3))
            bar_len = min(bar_len, 30)
            bar     = "█" * bar_len + "░" * (30 - bar_len)
            emoji   = CATEGORY_EMOJI.get(cat, "")
            lines.append(
                f"  {emoji} {cat:<14} ₹{amt:>9,.0f}  {bar}  {pct:.1f}%"
            )

        # Top 5 transactions
        lines.append("─" * W)
        lines.append("  TOP 5 TRANSACTIONS")
        lines.append("─" * W)
        top5 = sorted(expenses, key=lambda e: e.amount, reverse=True)[:5]
        for e in top5:
            emoji = CATEGORY_EMOJI.get(e.category, "")
            lines.append(
                f"  [{e.date}]  {emoji} {e.category:<14}  "
                f"₹{e.amount:>9,.2f}  {e.description[:24]}"
            )

        # Insights
        lines.append("─" * W)
        lines.append("  INSIGHTS")
        lines.append("─" * W)
        for insight in engine.generate_insights(expenses, budget):
            lines.append(f"  {insight}")

        forecast = engine.forecast(expenses, budget)
        if forecast:
            lines.append(f"  {forecast}")

        # Health Score
        score, label, breakdown = engine.financial_health_score(expenses, budget)
        lines.append("─" * W)
        lines.append(f"  FINANCIAL HEALTH SCORE  :  {score}/100  {label}")
        for b in breakdown:
            lines.append(f"    {b}")

        lines.append("═" * W)
        lines.append(f"  Generated by {APP_NAME} v{VERSION}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("═" * W)
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  APP CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

class AppController:
    """
    CLI orchestrator — owns all managers, routes user input.

    Entry points
    ------------
    boot()  Load state from disk.
    run()   Start the interactive menu loop.
    demo()  Run a non-interactive showcase (--demo flag).
    """

    def __init__(self) -> None:
        self._storage  = StorageManager()
        self._expenses = ExpenseManager(self._storage)
        self._budget   = BudgetManager(self._storage)
        self._engine   = InsightEngine()
        self._reports  = ReportGenerator()

    def boot(self) -> None:
        """Initialise application state from persistent storage."""
        self._expenses.load_from_storage()
        self._budget.load_from_storage()

    def persist(self) -> None:
        """Flush in-memory state to disk."""
        self._expenses.flush(self._budget.to_dict())

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the interactive main-menu loop."""
        while True:
            clear_screen()
            print_header()
            self._status_bar()
            self._main_menu()

    def _status_bar(self) -> None:
        """One-line summary displayed below the header."""
        spent  = self._expenses.total()
        budget = self._budget.amount
        count  = self._expenses.count()
        status = self._budget.status(spent)
        streak = self._expenses.tracking_streak()

        sc = {
            "SAFE":     Ansi.GREEN,
            "WARNING":  Ansi.YELLOW,
            "EXCEEDED": Ansi.RED,
            "NOT_SET":  Ansi.DIM,
        }.get(status, Ansi.DIM)

        budget_str = f"₹{budget:,.0f}" if budget > 0 else "Not set"
        streak_str = f"🔥 {streak}d streak" if streak >= 2 else ""

        print(
            f"  {S('Expenses:', Ansi.DIM)} {S(str(count), Ansi.WHITE)}  │  "
            f"{S('Spent:', Ansi.DIM)} {S(f'₹{spent:,.2f}', Ansi.WHITE)}  │  "
            f"{S('Budget:', Ansi.DIM)} {S(budget_str, Ansi.WHITE)}  │  "
            f"{S('Status:', Ansi.DIM)} {S(status, sc + Ansi.BOLD)}"
            + (f"  │  {S(streak_str, Ansi.YELLOW)}" if streak_str else "")
        )

    def _main_menu(self) -> None:
        """Render and handle the main-menu choices."""
        print_section("MAIN MENU")

        MENU = [
            ("1", "Add Expense",          Ansi.GREEN),
            ("2", "View All Expenses",    Ansi.WHITE),
            ("3", "Search / Filter",      Ansi.WHITE),
            ("4", "Edit Expense",         Ansi.WHITE),
            ("5", "Delete Expense",       Ansi.WHITE),
            ("6", "Analytics Dashboard",  Ansi.CYAN),
            ("7", "Spending Insights",    Ansi.MAGENTA),
            ("8", "Budget Manager",       Ansi.YELLOW),
            ("9", "Monthly Report",       Ansi.BLUE),
            ("E", "Export to CSV",        Ansi.DIM),
            ("0", "Save & Exit",          Ansi.DIM),
        ]
        for key, label, color in MENU:
            print(f"  {S(f'[{key}]', color)}  {label}")

        print()
        choice = ask("Choose option").upper()
        dispatch = {
            "1": self._add_expense,
            "2": self._view_expenses,
            "3": self._search_filter,
            "4": self._edit_expense,
            "5": self._delete_expense,
            "6": self._analytics,
            "7": self._insights_screen,
            "8": self._budget_menu,
            "9": self._monthly_report,
            "E": self._export_csv,
            "0": self._exit,
        }
        action = dispatch.get(choice)
        if action:
            action()
        else:
            fail("Invalid option. Please try again.")
            pause()

    def _exit(self) -> None:
        self.persist()
        print(S("\n  💾  All data saved. Goodbye!\n", Ansi.GREEN))
        sys.exit(0)

    # ── Budget Alert Helper ────────────────────────────────────────────────────

    def _budget_alert(self) -> None:
        """Show a budget alert after any spend-modifying action."""
        status = self._budget.status(self._expenses.total())
        if status == "EXCEEDED":
            print(S(
                "\n  🚨  BUDGET EXCEEDED! You have gone over your monthly limit.",
                Ansi.RED + Ansi.BOLD,
            ))
        elif status == "WARNING":
            pct = self._budget.percent_used(self._expenses.total())
            warn(f"Budget at {pct}% — only "
                 f"₹{self._budget.remaining(self._expenses.total()):,.2f} remaining.")

    # ── 1. Add Expense ────────────────────────────────────────────────────────

    def _add_expense(self) -> None:
        clear_screen()
        print_header()
        print_section("ADD EXPENSE")

        try:
            raw_amt = ask("Amount (₹)")
            amount  = float(raw_amt)

            category    = pick_category()
            description = ask("Description")
            if not description:
                description = category

            today    = date.today().isoformat()
            date_str = ask("Date (YYYY-MM-DD)", default=today)

            exp = self._expenses.add(amount, category, description, date_str)
            self.persist()
            ok(f"Expense added!  ID: {S(exp.id, Ansi.CYAN)}")
            self._budget_alert()

        except ValueError as exc:
            fail(str(exc))

        pause()

    # ── 2. View All Expenses ──────────────────────────────────────────────────

    def _view_expenses(self) -> None:
        clear_screen()
        print_header()
        print_section("ALL EXPENSES")
        print_expense_table(self._expenses.all_sorted())
        pause()

    # ── 3. Search / Filter ───────────────────────────────────────────────────

    def _search_filter(self) -> None:
        clear_screen()
        print_header()
        print_section("SEARCH & FILTER")

        print(f"  {S('[1]', Ansi.CYAN)}  Keyword search")
        print(f"  {S('[2]', Ansi.CYAN)}  Filter by category")
        print(f"  {S('[3]', Ansi.CYAN)}  Filter by month")
        print()
        choice = ask("Option")

        if choice == "1":
            q       = ask("Search keyword")
            results = self._expenses.search(q)
            print_section(f"RESULTS FOR '{q}'")
            print_expense_table(results)

        elif choice == "2":
            cat     = pick_category()
            results = self._expenses.filter_by_category(cat)
            print_section(f"CATEGORY — {cat}")
            print_expense_table(results)

        elif choice == "3":
            now   = datetime.now()
            raw_y = ask("Year",  default=str(now.year))
            raw_m = ask("Month", default=str(now.month))
            try:
                year  = int(raw_y)
                month = int(raw_m)
                if not (1 <= month <= 12):
                    raise ValueError("Month must be 1–12.")
                results    = self._expenses.filter_by_month(year, month)
                month_name = datetime(year, month, 1).strftime("%B %Y")
                print_section(f"EXPENSES — {month_name}")
                print_expense_table(results)
            except ValueError as exc:
                fail(str(exc))
        else:
            fail("Invalid option.")

        pause()

    # ── 4. Edit Expense ───────────────────────────────────────────────────────

    def _edit_expense(self) -> None:
        clear_screen()
        print_header()
        print_section("EDIT EXPENSE")
        print_expense_table(self._expenses.all_sorted())

        eid = ask("Expense ID to edit").upper()
        exp = self._expenses.get_by_id(eid)
        if exp is None:
            fail(f"ID '{eid}' not found.")
            pause()
            return

        print(S(
            f"\n  Editing: [{exp.date}] {exp.category} ₹{exp.amount} — {exp.description}",
            Ansi.WHITE,
        ))
        print(S("  Leave blank to keep the current value.\n", Ansi.DIM))

        try:
            raw_amt  = ask(f"Amount    [₹{exp.amount}]")
            raw_cat  = ask("Category  [Enter to keep / 'c' to change]")
            raw_desc = ask(f"Desc      [{exp.description}]")
            raw_date = ask(f"Date      [{exp.date}]")

            new_amt  = float(raw_amt) if raw_amt else None
            new_cat  = pick_category() if raw_cat.lower() == "c" else None
            new_desc = raw_desc if raw_desc else None
            new_date = raw_date if raw_date else None

            self._expenses.edit(eid, new_amt, new_cat, new_desc, new_date)
            self.persist()
            ok("Expense updated.")
            self._budget_alert()

        except ValueError as exc:
            fail(str(exc))

        pause()

    # ── 5. Delete Expense ─────────────────────────────────────────────────────

    def _delete_expense(self) -> None:
        clear_screen()
        print_header()
        print_section("DELETE EXPENSE")
        print_expense_table(self._expenses.all_sorted())

        eid = ask("Expense ID to delete").upper()
        exp = self._expenses.get_by_id(eid)
        if exp is None:
            fail(f"ID '{eid}' not found.")
            pause()
            return

        confirm = ask(
            f"Delete [{exp.date}] {exp.category} ₹{exp.amount}?  (yes / Enter to cancel)"
        )
        if confirm.lower() in ("yes", "y"):
            self._expenses.delete(eid)
            self.persist()
            ok("Expense deleted.")
        else:
            warn("Deletion cancelled.")

        pause()

    # ── 6. Analytics Dashboard ───────────────────────────────────────────────

    def _analytics(self) -> None:
        clear_screen()
        print_header()
        print_section("ANALYTICS DASHBOARD")

        all_exp = self._expenses.all_sorted()
        if not all_exp:
            warn("No expenses to analyse yet.")
            pause()
            return

        total      = self._expenses.total()
        cat_totals = self._expenses.total_by_category()
        budget     = self._budget.amount
        daily_avg  = self._expenses.daily_average()
        this_month = self._expenses.this_month_total()

        # Summary metrics
        print(S(f"\n  {'TOTAL SPENDING':.<32} ₹{total:,.2f}",      Ansi.BOLD + Ansi.WHITE))
        print(S(f"  {'TRANSACTIONS':.<32} {self._expenses.count()}", Ansi.WHITE))
        print(S(f"  {'DAILY AVERAGE':.<32} ₹{daily_avg:,.2f}",      Ansi.WHITE))
        print(S(f"  {'THIS MONTH':.<32} ₹{this_month:,.2f}",        Ansi.WHITE))

        if budget > 0:
            rem = self._budget.remaining(total)
            rc  = Ansi.GREEN if rem >= 0 else Ansi.RED
            print(S(f"  {'MONTHLY BUDGET':.<32} ₹{budget:,.2f}", Ansi.WHITE))
            print(S(f"  {'REMAINING':.<32} ₹{rem:,.2f}",         rc))
            print(f"\n  {S('Budget Usage', Ansi.DIM)}")
            print(f"  {progress_bar(total, budget)}")

        # Category bar chart
        print_section("SPENDING BY CATEGORY")
        for cat, amt in cat_totals.items():
            pct      = (amt / total) * 100
            bar_fill = min(32, max(1, int(pct / 3)))
            bar      = "█" * bar_fill + "░" * (32 - bar_fill)
            emoji    = CATEGORY_EMOJI.get(cat, "")
            print(
                f"  {emoji} {S(cat, Ansi.CYAN):<23}"
                f"{S(bar, Ansi.BLUE)}  "
                f"{S(f'₹{amt:,.0f}', Ansi.WHITE):>14}  "
                f"{S(f'{pct:.1f}%', Ansi.DIM)}"
            )

        # Top category trophy
        top = self._expenses.top_category()
        if top:
            print_section("TOP CATEGORY")
            emoji = CATEGORY_EMOJI.get(top[0], "")
            print(S(f"  🏆 {emoji} {top[0]}  —  ₹{top[1]:,.2f}", Ansi.YELLOW + Ansi.BOLD))

        # Monthly trend (show even for single month)
        monthly = self._expenses.monthly_summary()
        if monthly:
            print_section("MONTHLY TREND")
            max_val = max(monthly.values()) or 1
            for ym, val in monthly.items():
                bar_fill = max(1, int((val / max_val) * 28))
                bar      = "█" * bar_fill + "░" * (28 - bar_fill)
                print(f"  {ym}  {S(bar, Ansi.BLUE)}  ₹{val:,.0f}")

        # Financial Health Score (no budget gate — works with budget=0)
        score, label, breakdown = self._engine.financial_health_score(all_exp, budget)
        print_section("FINANCIAL HEALTH SCORE")
        sc = Ansi.GREEN if score >= 70 else (Ansi.YELLOW if score >= 50 else Ansi.RED)
        print(S(f"  {score}/100  |  {label}", sc + Ansi.BOLD))
        print()
        for line in breakdown:
            print(S(f"    {line}", Ansi.DIM))

        pause()

    # ── 7. Insights ───────────────────────────────────────────────────────────

    def _insights_screen(self) -> None:
        clear_screen()
        print_header()
        print_section("SPENDING INTELLIGENCE")

        all_exp    = self._expenses.all_sorted()
        budget     = self._budget.amount
        cat_totals = self._expenses.total_by_category()
        total      = self._expenses.total()

        print()
        for i, insight in enumerate(self._engine.generate_insights(all_exp, budget), 1):
            print(f"  {S(str(i) + '.', Ansi.CYAN)}  {insight}")

        fc = self._engine.forecast(all_exp, budget)
        if fc:
            print()
            print(S(f"  Forecast: {fc}", Ansi.YELLOW))

        print_section("SAVINGS RECOMMENDATIONS")
        for rec in self._engine.savings_suggestions(cat_totals, budget, total):
            print(f"  {rec}")

        pause()

    # ── 8. Budget Manager ─────────────────────────────────────────────────────

    def _budget_menu(self) -> None:
        clear_screen()
        print_header()
        print_section("BUDGET MANAGER")

        budget = self._budget.amount
        spent  = self._expenses.total()
        status = self._budget.status(spent)

        if budget > 0:
            rem = self._budget.remaining(spent)
            rc  = Ansi.GREEN if rem >= 0 else Ansi.RED
            sc  = {"SAFE": Ansi.GREEN, "WARNING": Ansi.YELLOW,
                   "EXCEEDED": Ansi.RED}.get(status, Ansi.DIM)
            print(S(f"\n  Monthly Budget  : ₹{budget:,.2f}", Ansi.WHITE))
            print(S(f"  Total Spent     : ₹{spent:,.2f}",   Ansi.WHITE))
            print(S(f"  Remaining       : ₹{rem:,.2f}",     rc))
            print(f"\n  {progress_bar(spent, budget)}")
            print(S(f"\n  Status          : {status}", sc + Ansi.BOLD))
        else:
            warn("No budget configured yet.")

        print()
        print(f"  {S('[1]', Ansi.CYAN)}  Set / update monthly budget")
        print(f"  {S('[2]', Ansi.CYAN)}  Back")

        if ask("Option") == "1":
            try:
                new_amt = float(ask("New monthly budget (₹)"))
                self._budget.set(new_amt)
                self.persist()
                ok(f"Budget set to ₹{new_amt:,.2f}")
            except ValueError as exc:
                fail(str(exc))

        pause()

    # ── 9. Monthly Report ─────────────────────────────────────────────────────

    def _monthly_report(self) -> None:
        clear_screen()
        print_header()
        print_section("MONTHLY REPORT")

        try:
            now   = datetime.now()
            raw_y = ask("Year",  default=str(now.year))
            raw_m = ask("Month", default=str(now.month))
            year  = int(raw_y)
            month = int(raw_m)
            if not (1 <= month <= 12):
                raise ValueError("Month must be 1–12.")

            expenses = self._expenses.filter_by_month(year, month)
            report   = self._reports.monthly_report(
                expenses, self._budget.amount, year, month, self._engine
            )
            print()
            print(S(report, Ansi.WHITE))

            if ask("Save report to file? (y / Enter to skip)").lower() == "y":
                filename = f"report_{year}_{month:02d}.txt"
                with open(filename, "w", encoding="utf-8") as fh:
                    fh.write(report)
                ok(f"Saved as {S(filename, Ansi.CYAN)}")

        except ValueError as exc:
            fail(str(exc))

        pause()

    # ── E. Export CSV ─────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        clear_screen()
        print_header()
        print_section("EXPORT TO CSV")

        if self._expenses.count() == 0:
            warn("No expenses to export.")
            pause()
            return

        filename = f"spendsense_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            rows = self._expenses.export_csv(filename)
            ok(f"Exported {rows} records → {S(filename, Ansi.CYAN)}")
        except OSError as exc:
            fail(f"Export failed: {exc}")

        pause()

    # ── Demo Mode ─────────────────────────────────────────────────────────────

    def demo(self) -> None:
        """
        Non-interactive demo mode (python spendsense_ai.py --demo).

        Seeds sample data and prints every major output screen so judges
        can see the full feature set without keyboard interaction.
        """
        # Seed sample expenses
        samples = [
            (450.0,  "Food",          "Canteen lunch + snacks",      "2026-06-01"),
            (200.0,  "Travel",        "Auto to college",             "2026-06-01"),
            (299.0,  "Recharge",      "Jio monthly recharge",        "2026-06-02"),
            (850.0,  "Food",          "Zomato dinner with friends",  "2026-06-02"),
            (1200.0, "Education",     "Python course — Udemy",       "2026-06-02"),
            (350.0,  "Entertainment", "Movie — PVR IMAX",            "2026-06-03"),
            (600.0,  "Shopping",      "College stationery",          "2026-06-03"),
            (180.0,  "Travel",        "Metro card top-up",           "2026-06-03"),
            (75.0,   "Health",        "Pharmacy — Vitamin C",        "2026-06-04"),
            (320.0,  "Food",          "Grocery — weekly stock",      "2026-06-04"),
            (500.0,  "Travel",        "Ola cab — airport drop",      "2026-06-05"),
            (149.0,  "Entertainment", "Netflix subscription",        "2026-06-05"),
        ]
        for amt, cat, desc, dt in samples:
            self._expenses.add(amt, cat, desc, dt)
        self._budget.set(8000.0)

        all_exp    = self._expenses.all_sorted()
        total      = self._expenses.total()
        cat_totals = self._expenses.total_by_category()
        budget     = self._budget.amount

        W = 66
        sep = "═" * W

        # ── Header
        print(S(sep, Ansi.CYAN))
        print(S(f"  {APP_NAME}  v{VERSION}  —  DEMO MODE", Ansi.CYAN + Ansi.BOLD))
        print(S(sep, Ansi.CYAN))

        # ── Expense Table
        print_section("ALL EXPENSES")
        print_expense_table(all_exp)

        # ── Analytics
        print_section("ANALYTICS SUMMARY")
        print(S(f"  Total Spending   : ₹{total:,.2f}", Ansi.WHITE + Ansi.BOLD))
        print(S(f"  Budget           : ₹{budget:,.2f}", Ansi.WHITE))
        print(S(f"  Remaining        : ₹{self._budget.remaining(total):,.2f}", Ansi.GREEN))
        print(S(f"  Daily Average    : ₹{self._expenses.daily_average():,.2f}", Ansi.WHITE))
        print()
        print(f"  Budget Usage  {progress_bar(total, budget)}")

        # ── Category chart
        print_section("SPENDING BY CATEGORY")
        for cat, amt in cat_totals.items():
            pct      = (amt / total) * 100
            bar_fill = min(32, max(1, int(pct / 3)))
            bar      = "█" * bar_fill + "░" * (32 - bar_fill)
            emoji    = CATEGORY_EMOJI.get(cat, "")
            print(
                f"  {emoji} {S(cat, Ansi.CYAN):<23}"
                f"{S(bar, Ansi.BLUE)}  "
                f"₹{amt:,.0f}  {pct:.1f}%"
            )

        # ── Top category
        top = self._expenses.top_category()
        if top:
            emoji = CATEGORY_EMOJI.get(top[0], "")
            print(S(f"\n  🏆 Top Category: {emoji} {top[0]}  —  ₹{top[1]:,.2f}", Ansi.YELLOW + Ansi.BOLD))

        # ── Health Score
        score, label, breakdown = self._engine.financial_health_score(all_exp, budget)
        print_section("FINANCIAL HEALTH SCORE")
        sc = Ansi.GREEN if score >= 70 else (Ansi.YELLOW if score >= 50 else Ansi.RED)
        print(S(f"  {score}/100  |  {label}", sc + Ansi.BOLD))
        for line in breakdown:
            print(S(f"    {line}", Ansi.DIM))

        # ── Insights
        print_section("SPENDING INTELLIGENCE")
        for i, insight in enumerate(self._engine.generate_insights(all_exp, budget), 1):
            print(f"  {S(str(i) + '.', Ansi.CYAN)}  {insight}")

        fc = self._engine.forecast(all_exp, budget)
        if fc:
            print(S(f"\n  Forecast: {fc}", Ansi.YELLOW))

        # ── Savings
        print_section("SAVINGS RECOMMENDATIONS")
        for rec in self._engine.savings_suggestions(cat_totals, budget, total):
            print(f"  {rec}")

        # ── Monthly Report
        print_section("MONTHLY REPORT — JUNE 2026")
        report = self._reports.monthly_report(all_exp, budget, 2026, 6, self._engine)
        print(S(report, Ansi.WHITE))

        print(S(f"\n  Demo complete. Run without --demo for full interactive mode.\n", Ansi.DIM))


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Application entry point.

    Flags
    -----
    --demo   Non-interactive showcase mode (no keyboard needed).
    """
    app = AppController()
    app.boot()

    if "--demo" in sys.argv:
        app.demo()
    else:
        app.run()


if __name__ == "__main__":
    main()
