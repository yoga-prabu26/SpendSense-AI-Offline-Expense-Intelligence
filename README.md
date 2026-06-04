# SPENDSENSE AI 🧠💸
### *Offline Student Expense Intelligence System*

> **"Because knowing where your money went is the first step to keeping more of it."**


## 🎯 The Problem

College students in India lose track of thousands of rupees every month —
UPI payments, canteen bills, Jio recharges, Ola rides. Existing tools need
internet, apps, or accounts. There was no simple, **offline, terminal-native**
solution built specifically for students.

**SPENDSENSE AI** fixes that. One Python file. Zero installs. Run it anywhere.

---

## 🚀 Quick Start

```bash
# No pip install needed — pure Python standard library
python spendsense_ai.py          # interactive mode
python spendsense_ai.py --demo   # non-interactive showcase
```

The app auto-loads `expenses.json` on startup (12 sample expenses included).

---

## ✨ Features

### Core (Required by hackathon)
| Feature | Status |
|---|---|
| Add expense — date, amount, category, description | ✅ |
| View all expenses (sorted, colour-coded table) | ✅ |
| Total amount spent | ✅ |
| Highest-spending category | ✅ |
| Monthly budget with warning & exceeded alerts | ✅ |

### Advanced 
| Feature                          |              Description                    |
|---|---|
| 🧠 **Financial Health Score**       Composite 0–100 scoring across 4 dimensions |
| 📊 **Spending Intelligence**        Category ratio analysis vs recommended allocations |
| 📈 **Budget Forecasting**           Predicts days until budget exhaustion (daily rate model) |
| 💡 **Savings Recommendations**      Personalised, category-specific cost-reduction tips |
| 📄 **Monthly Report Generator**     Full formatted report — display + save to `.txt` |
| 📤 **CSV Export**                   One-key export for Google Sheets / Excel |
| 🔍 **Full-text Search**             Search descriptions and categories simultaneously |
| 🗓️ **Date & Category Filter**       Slice expenses any way you need |
| ✏️ **Expense Editing**              Update any field of any expense by ID |
| 🔥 **Tracking Streak**              Daily tracking streak counter in the status bar |
| 🎬 **--demo flag**                  Full non-interactive showcase for judges |
| 💾 **Auto JSON Persistence**        Save / load without any user action |
| 🎨 **Premium Terminal UI**          Unicode tables, colour bars, emoji, progress indicators |

---

## 📸 Actual Program Output

```
══════════════════════════════════════════════════════════════════
  SPENDSENSE AI  v4.0  —  DEMO MODE
══════════════════════════════════════════════════════════════════

  ◆ ALL EXPENSES
──────────────────────────────────────────────────────────────────

  #    ID         Date         Category             Amount  Description
──────────────────────────────────────────────────────────────────
  1    0EB401F5    2026-06-05   🚌 Travel             ₹500.00  Ola cab — airport drop
  2    A67396B7    2026-06-05   🎬 Entertainment      ₹149.00  Netflix subscription
  3    0C809EE8    2026-06-04   💊 Health              ₹75.00  Pharmacy — Vitamin C
  4    A2F2FC9A    2026-06-04   🍱 Food               ₹320.00  Grocery — weekly stock
  5    DB8F57AA    2026-06-03   🎬 Entertainment      ₹350.00  Movie — PVR IMAX
  6    956200FF    2026-06-03   🛍 Shopping           ₹600.00  College stationery
  7    D0BE3EC2    2026-06-03   🚌 Travel             ₹180.00  Metro card top-up
  8    DBB1E06D    2026-06-02   📱 Recharge           ₹299.00  Jio monthly recharge
  9    66C77B7D    2026-06-02   🍱 Food               ₹850.00  Zomato dinner with friends
  10   3D70DF84    2026-06-02   📚 Education        ₹1,200.00  Python course — Udemy
  11   9CFCB601    2026-06-01   🍱 Food               ₹450.00  Canteen lunch + snacks
  12   40C7143A    2026-06-01   🚌 Travel             ₹200.00  Auto to college
──────────────────────────────────────────────────────────────────
                                                       TOTAL  ₹5,173.00

  ◆ ANALYTICS SUMMARY
──────────────────────────────────────────────────────────────────
  Total Spending   : ₹5,173.00
  Budget           : ₹8,000.00
  Remaining        : ₹2,827.00
  Daily Average    : ₹1,293.25

  Budget Usage  [███████████████████░░░░░░░░░░░] 64.7%

  ◆ SPENDING BY CATEGORY
──────────────────────────────────────────────────────────────────
  🍱 Food          ██████████░░░░░░░░░░░░░░░░░░░░░░  ₹1,620  31.3%
  📚 Education     ███████░░░░░░░░░░░░░░░░░░░░░░░░░  ₹1,200  23.2%
  🚌 Travel        █████░░░░░░░░░░░░░░░░░░░░░░░░░░░  ₹880    17.0%
  🛍 Shopping      ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ₹600    11.6%
  🎬 Entertainment ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ₹499     9.6%
  📱 Recharge      █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ₹299     5.8%
  💊 Health        █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ₹75      1.4%

  🏆 Top Category: 🍱 Food  —  ₹1,620.00

  ◆ FINANCIAL HEALTH SCORE
──────────────────────────────────────────────────────────────────
  80/100  |  🔵 Good
    Budget Adherence      32/40 pts
    Category Variety      30/30 pts
    Savings Potential     14/20 pts
    Tracking Consistency   4/10 pts

  ◆ SPENDING INTELLIGENCE
──────────────────────────────────────────────────────────────────
  1.  •  🍱 Food: 31.3% of total spend  (₹1,620)
  2.  ⚠  📚 Education is 23.2% (recommended ≤ 15%) — ₹1,200
  3.  •  🚌 Travel: 17.0% of total spend  (₹880)
  4.  ⚠  🛍 Shopping is 11.6% (recommended ≤ 5%) — ₹600

  Forecast: 📈 At ₹1,293/day, budget exhausts in ~2 day(s).

  ◆ SAVINGS RECOMMENDATIONS
──────────────────────────────────────────────────────────────────
  ✨ Great discipline! Spending distribution looks healthy.
```

*(This is real output from `python spendsense_ai.py --demo` — not fabricated.)*

---

## 🏗️ Architecture

```
spendsense_ai.py  (single file, zero dependencies)
│
├── Expense            Validated dataclass — UUID ID, __post_init__ guards
├── StorageManager     Atomic JSON read/write — full file replacement per save
├── ExpenseManager     CRUD + search / filter / sort / CSV export / streak
├── BudgetManager      Tracking, thresholds, percent_used, status levels
├── InsightEngine      Health score, category insights, forecast, suggestions
├── ReportGenerator    Formatted monthly report (screen + .txt export)
└── AppController      CLI routing, status bar, demo mode, session lifecycle
```

**Seven classes. One responsibility each. Every public method is type-hinted and docstringed.**

---

## 🔧 Technical Decisions

| Decision | Rationale |
|---|---|
| Pure stdlib | Zero setup friction; works on any Python 3.8+ machine |
| `dataclasses` + `__post_init__` | Model-level validation mirrors production patterns |
| UUID hex IDs (8 chars) | Collision-safe, typeable, survives deletion re-indexing |
| Atomic JSON writes | Full file replacement — no partial-write corruption risk |
| ANSI codes without `rich`/`colorama` | Premium terminal UI with zero dependencies |
| `--demo` flag | Judges see full output without interactive keyboard session |
| `SortField` / `SortOrder` enums | No magic strings; extensible without touching call sites |
| `tracking_streak()` | Gamification — encourages daily use; memorable judge differentiator |

---

## 📁 File Structure

```
spendsense-ai/
├── spendsense_ai.py    ← Single-file application (run this)
├── expenses.json       ← Auto-created data store (12 samples included)
├── README.md           ← This file
└── CASE_STUDY.md       ← Product case study document
```

Optional outputs created by the app:
```
report_2026_06.txt                     ← saved monthly report
spendsense_export_20260604_143022.csv  ← CSV export
```

---

## 🔮 If I Had More Time

1. **Recurring expense templates** — auto-log Jio recharge, Netflix monthly
2. **UPI SMS parser** — extract amount and merchant from payment SMS
3. **Annual trend view** — 12-month ASCII chart for pattern recognition
4. **Multi-profile support** — different expense sets for hostel vs home
5. **Web UI layer** — same Python logic, Flask routes added on top

-

*SPENDSENSE AI v4.0 — Built for the hacthon*
