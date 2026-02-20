# finance_server.py
import json
from datetime import datetime, date
from typing import Dict, List, Optional
import httpx
from fastmcp import FastMCP

mcp = FastMCP("FinanceAssistant 💰")

# ── Simulated local expense database ────────────────────────────
# In a real project, this would be a SQLite or PostgreSQL query
EXPENSES = [
    {
        "date": "2026-02-01",
        "category": "Food",
        "amount": 45000,
        "note": "Grocery store",
    },
    {
        "date": "2026-02-03",
        "category": "Transport",
        "amount": 12000,
        "note": "Bus pass",
    },
    {"date": "2026-02-05", "category": "Food", "amount": 28000, "note": "Restaurant"},
    {
        "date": "2026-02-10",
        "category": "Utilities",
        "amount": 89000,
        "note": "Electricity bill",
    },
    {"date": "2026-02-12", "category": "Food", "amount": 15000, "note": "Lunch"},
    {
        "date": "2026-02-14",
        "category": "Leisure",
        "amount": 55000,
        "note": "Cinema + dinner",
    },
    {"date": "2026-02-17", "category": "Transport", "amount": 8500, "note": "Taxi"},
    {
        "date": "2026-02-18",
        "category": "Food",
        "amount": 62000,
        "note": "Grocery store",
    },
    {
        "date": "2026-02-19",
        "category": "Leisure",
        "amount": 30000,
        "note": "Book purchase",
    },
]


@mcp.tool
def get_expenses(
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict:
    """
    Retrieve personal expense records, optionally filtered by category or date range.
    Categories available: Food, Transport, Utilities, Leisure.
    Dates should be in YYYY-MM-DD format.
    Use this when the user asks about their spending, expenses, or transactions.
    """
    filtered = EXPENSES.copy()

    if category:
        filtered = [e for e in filtered if e["category"].lower() == category.lower()]

    if start_date:
        filtered = [e for e in filtered if e["date"] >= start_date]

    if end_date:
        filtered = [e for e in filtered if e["date"] <= end_date]

    total = sum(e["amount"] for e in filtered)

    return {
        "expenses": filtered,
        "total_KRW": total,
        "count": len(filtered),
        "currency": "KRW (Korean Won)",
    }


@mcp.tool
def summarize_by_category() -> Dict:
    """
    Summarize all expenses grouped by category with totals and percentages.
    Use this when the user asks for a spending breakdown or budget overview.
    """
    totals: Dict[str, int] = {}
    for expense in EXPENSES:
        cat = expense["category"]
        totals[cat] = totals.get(cat, 0) + expense["amount"]

    grand_total = sum(totals.values())
    summary = [
        {
            "category": cat,
            "total_KRW": amount,
            "percentage": round(amount / grand_total * 100, 1),
        }
        for cat, amount in sorted(totals.items(), key=lambda x: -x[1])
    ]

    return {
        "summary": summary,
        "grand_total_KRW": grand_total,
        "period": "February 2026",
    }


@mcp.tool
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict:
    """
    Convert an amount between currencies using live exchange rates.
    Use this when the user wants to know the value in a different currency.
    Supports major currencies: KRW, USD, EUR, JPY, GBP, etc.
    """
    try:
        # Using frankfurter.app — free, no API key
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.frankfurter.app/latest",
                params={"from": from_currency.upper(), "to": to_currency.upper()},
            )
            data = response.json()

        rate = data["rates"][to_currency.upper()]
        converted = round(amount * rate, 2)

        return {
            "original_amount": amount,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "exchange_rate": rate,
            "converted_amount": converted,
        }
    except Exception as e:
        return {"error": f"Currency conversion failed: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
