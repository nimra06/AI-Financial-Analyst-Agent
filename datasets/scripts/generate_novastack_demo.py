#!/usr/bin/env python3
"""Generate enterprise-scale NovaStack demo CSVs for video / upload demos."""

from __future__ import annotations

import csv
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

random.seed(42)

OUT_DIR = ROOT / "datasets" / "sample" / "demo"
DOWNLOADS = Path.home() / "Downloads"

DEPARTMENTS = [
    "Engineering",
    "Product",
    "Sales",
    "Marketing",
    "Customer Success",
    "G&A",
    "Finance",
    "People Ops",
    "Data Platform",
    "Security",
    "Legal",
    "Operations",
]
REGIONS = ["Americas", "EMEA", "APAC", "LatAm"]
PRODUCT_LINES = [
    "Platform Core",
    "Analytics Pro",
    "Insights Add-on",
    "API Usage",
    "Professional Services",
]
EXPENSE_CATEGORIES = [
    ("Payroll & Benefits", "6100"),
    ("Contractors", "6105"),
    ("Sales Commissions", "6200"),
    ("Paid Media", "6210"),
    ("Events & Sponsorships", "6215"),
    ("Software Subscriptions", "6300"),
    ("Cloud Hosting", "6310"),
    ("Customer Support Tools", "6315"),
    ("R&D Contractors", "6400"),
    ("Legal & Compliance", "6500"),
    ("Accounting & Audit", "6510"),
    ("Insurance", "6520"),
    ("Office & Facilities", "6600"),
    ("Travel", "6610"),
    ("Meals & Entertainment", "6615"),
    ("Recruiting", "6620"),
    ("Training", "6625"),
    ("Depreciation", "6700"),
    ("Amortization", "6710"),
    ("Bank Fees", "6800"),
    ("Bad Debt", "6810"),
    ("Miscellaneous", "6999"),
]
VENDORS = [
    "AWS", "Google Cloud", "Salesforce", "HubSpot", "LinkedIn", "Gusto", "Rippling",
    "WeWork", "Zoom", "Atlassian", "Datadog", "Snowflake", "Okta", "CrowdStrike",
    "Deloitte", "Stripe", "Twilio", "Intercom", "Figma", "Notion",
]

HEADERS = [
    "reporting_period",
    "fiscal_year",
    "fiscal_quarter",
    "fiscal_month",
    "entity",
    "legal_entity_code",
    "currency",
    "row_type",
    "gl_account",
    "gl_account_name",
    "cost_center",
    "department",
    "region",
    "product_line",
    "customer_segment",
    "category",
    "subcategory",
    "vendor_name",
    "invoice_id",
    "revenue",
    "cogs",
    "opex",
    "amount",
    "budget_revenue",
    "budget_opex",
    "budget_amount",
    "variance_amount",
    "headcount_allocated",
    "fte_count",
    "transaction_count",
    "active_customers",
    "arr_millions",
    "net_revenue_retention_pct",
    "logo_churn_pct",
    "gross_margin_pct",
    "ebitda",
    "cash_collections",
    "deferred_revenue",
    "americas_pct",
    "emea_pct",
    "apac_pct",
    "source_system",
    "last_updated",
    "preparer",
    "notes",
]


def fiscal_q(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def month_range(start: tuple[int, int], count: int) -> list[date]:
    y, m = start
    out: list[date] = []
    for _ in range(count):
        out.append(date(y, m, 1))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def monthly_totals(months: list[date]) -> list[dict]:
    rows: list[dict] = []
    customers = 118
    headcount = 42
    for d in months:
        t = (d.year - 2022) * 12 + (d.month - 1)
        growth = 1.0 + t * 0.018
        seasonal = 1.0 + 0.06 * ((d.month - 6) / 6) ** 2
        if d.year == 2025 and d.month == 3:
            seasonal *= 0.92
        if d.year == 2025 and d.month == 12:
            seasonal *= 1.08
        noise = random.uniform(0.985, 1.015)
        revenue = round(98000 * growth * seasonal * noise, 2)
        cogs = round(revenue * random.uniform(0.238, 0.252), 2)
        opex = round(revenue * random.uniform(0.62, 0.68), 2)
        gross = revenue - cogs
        ebitda = gross - opex
        customers = max(95, customers + random.randint(-2, 4))
        headcount = max(38, headcount + (1 if random.random() > 0.72 else 0))
        rows.append(
            {
                "date": d,
                "revenue": revenue,
                "cogs": cogs,
                "opex": opex,
                "gross": gross,
                "ebitda": ebitda,
                "budget_revenue": round(revenue * random.uniform(1.01, 1.06), 2),
                "budget_opex": round(opex * random.uniform(1.0, 1.05), 2),
                "customers": customers,
                "headcount": headcount,
                "nrr": round(random.uniform(102, 118), 1),
                "churn": round(random.uniform(1.8, 3.2), 2),
            }
        )
    return rows


def split_weights(n: int) -> list[float]:
    raw = [random.random() for _ in range(n)]
    s = sum(raw)
    return [x / s for x in raw]


def build_main_csv(months: list[date], totals: list[dict]) -> list[dict]:
    """Enterprise export: revenue by product + expense GL lines (no double-counted summary)."""
    out: list[dict] = []
    inv_seq = 100000

    for tot in totals:
        d = tot["date"]
        ds = d.strftime("%Y-%m-%d")
        fy, fq = d.year, fiscal_q(d)
        br, bo = tot["budget_revenue"], tot["budget_opex"]
        americas = round(random.uniform(62, 72), 1)
        emea = round(random.uniform(18, 26), 1)
        apac = round(100 - americas - emea, 1)

        # Revenue by product line (sums to monthly revenue)
        rev_weights = split_weights(len(PRODUCT_LINES))
        cogs_weights = split_weights(len(PRODUCT_LINES))
        for pl, rw, cw in zip(PRODUCT_LINES, rev_weights, cogs_weights):
            rev = round(tot["revenue"] * rw, 2)
            cogs = round(tot["cogs"] * cw, 2)
            seg = random.choice(["Enterprise", "Mid-Market", "SMB", "Strategic"])
            dept = random.choice(["Sales", "Customer Success", "Product"])
            region = random.choice(REGIONS)
            inv_seq += 1
            out.append(
                {
                    "reporting_period": ds,
                    "fiscal_year": fy,
                    "fiscal_quarter": fq,
                    "fiscal_month": d.month,
                    "entity": "NovaStack Analytics Inc.",
                    "legal_entity_code": "NS-US-01",
                    "currency": "USD",
                    "row_type": "REVENUE_DETAIL",
                    "gl_account": "4000",
                    "gl_account_name": "Subscription Revenue",
                    "cost_center": f"CC-{dept[:3].upper()}-{region[:2]}",
                    "department": dept,
                    "region": region,
                    "product_line": pl,
                    "customer_segment": seg,
                    "category": "",
                    "subcategory": pl,
                    "vendor_name": "",
                    "invoice_id": f"REV-{d.year}{d.month:02d}-{inv_seq}",
                    "revenue": f"{rev:.2f}",
                    "cogs": f"{cogs:.2f}",
                    "opex": "",
                    "amount": "",
                    "budget_revenue": f"{br * rw:.2f}",
                    "budget_opex": "",
                    "budget_amount": "",
                    "variance_amount": f"{rev - br * rw:.2f}",
                    "headcount_allocated": "",
                    "fte_count": "",
                    "transaction_count": random.randint(120, 480),
                    "active_customers": "",
                    "arr_millions": "",
                    "net_revenue_retention_pct": "",
                    "logo_churn_pct": "",
                    "gross_margin_pct": "",
                    "ebitda": "",
                    "cash_collections": "",
                    "deferred_revenue": "",
                    "americas_pct": "",
                    "emea_pct": "",
                    "apac_pct": "",
                    "source_system": "NetSuite",
                    "last_updated": f"{d.year}-{d.month:02d}-28",
                    "preparer": "fp&a@novastack.io",
                    "notes": "",
                }
            )

        # Expense GL lines (~22 categories × ~2-3 splits for dept/region = many rows)
        exp_weights = split_weights(len(EXPENSE_CATEGORIES))
        for (cat_name, gl_base), ew in zip(EXPENSE_CATEGORIES, exp_weights):
            base_amt = tot["opex"] * ew
            splits = random.randint(2, 4)
            split_w = split_weights(splits)
            for sw in split_w:
                amt = round(base_amt * sw, 2)
                dept = random.choice(DEPARTMENTS)
                region = random.choice(REGIONS)
                vendor = random.choice(VENDORS) if random.random() > 0.35 else ""
                inv_seq += 1
                out.append(
                    {
                        "reporting_period": ds,
                        "fiscal_year": fy,
                        "fiscal_quarter": fq,
                        "fiscal_month": d.month,
                        "entity": "NovaStack Analytics Inc.",
                        "legal_entity_code": "NS-US-01",
                        "currency": "USD",
                        "row_type": "OPEX_GL",
                        "gl_account": f"{gl_base}-{random.randint(10, 99)}",
                        "gl_account_name": cat_name,
                        "cost_center": f"CC-{dept[:3].upper()}-{region[:2]}",
                        "department": dept,
                        "region": region,
                        "product_line": "",
                        "customer_segment": "",
                        "category": cat_name,
                        "subcategory": f"{cat_name} - {dept}",
                        "vendor_name": vendor,
                        "invoice_id": f"AP-{d.year}{d.month:02d}-{inv_seq}",
                        "revenue": "0",
                        "cogs": "0",
                        "opex": "",
                        "amount": f"{amt:.2f}",
                        "budget_revenue": "",
                        "budget_opex": "",
                        "budget_amount": f"{bo * ew * sw:.2f}",
                        "variance_amount": f"{amt - bo * ew * sw:.2f}",
                        "headcount_allocated": round(amt / max(tot["headcount"], 1), 2),
                        "fte_count": random.randint(1, 12) if "Payroll" in cat_name else "",
                        "transaction_count": random.randint(1, 45),
                        "active_customers": "",
                        "arr_millions": "",
                        "net_revenue_retention_pct": "",
                        "logo_churn_pct": "",
                        "gross_margin_pct": "",
                        "ebitda": "",
                        "cash_collections": "",
                        "deferred_revenue": "",
                        "americas_pct": "",
                        "emea_pct": "",
                        "apac_pct": "",
                        "source_system": "NetSuite",
                        "last_updated": f"{d.year}-{d.month:02d}-28",
                        "preparer": "accounting@novastack.io",
                        "notes": vendor and f"Vendor: {vendor}" or "",
                    }
                )

        # One consolidated KPI row per month (revenue/cogs/opex zero — metrics only for export realism)
        out.append(
            {
                "reporting_period": ds,
                "fiscal_year": fy,
                "fiscal_quarter": fq,
                "fiscal_month": d.month,
                "entity": "NovaStack Analytics Inc.",
                "legal_entity_code": "NS-CONSOL",
                "currency": "USD",
                "row_type": "KPI_SNAPSHOT",
                "gl_account": "STAT-001",
                "gl_account_name": "Monthly KPIs",
                "cost_center": "CC-EXEC",
                "department": "Consolidated",
                "region": "Global",
                "product_line": "All",
                "customer_segment": "All",
                "category": "",
                "subcategory": "",
                "vendor_name": "",
                "invoice_id": "",
                "revenue": "0",
                "cogs": "0",
                "opex": "0",
                "amount": "",
                "budget_revenue": f"{br:.2f}",
                "budget_opex": f"{bo:.2f}",
                "budget_amount": "",
                "variance_amount": "",
                "headcount_allocated": "",
                "fte_count": tot["headcount"],
                "transaction_count": "",
                "active_customers": tot["customers"],
                "arr_millions": round(tot["revenue"] * 12 / 1_000_000, 2),
                "net_revenue_retention_pct": tot["nrr"],
                "logo_churn_pct": tot["churn"],
                "gross_margin_pct": round(tot["gross"] / tot["revenue"] * 100, 2),
                "ebitda": f"{tot['ebitda']:.2f}",
                "cash_collections": f"{tot['revenue'] * random.uniform(0.94, 1.02):.2f}",
                "deferred_revenue": f"{tot['revenue'] * random.uniform(0.35, 0.55):.2f}",
                "americas_pct": americas,
                "emea_pct": emea,
                "apac_pct": apac,
                "source_system": "Looker",
                "last_updated": f"{d.year}-{d.month:02d}-28",
                "preparer": "bi@novastack.io",
                "notes": "Consolidated KPI row — not included in GL roll-up",
            }
        )

    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    months = month_range((2022, 1), 48)
    totals = monthly_totals(months)
    rows = build_main_csv(months, totals)

    targets = [
        OUT_DIR / "NovaStack_Monthly_Financials_2025.csv",
        DOWNLOADS / "NovaStack_Monthly_Financials_2025.csv",
    ]
    for p in targets:
        write_csv(p, rows)

    from analytics.ingest import load_and_clean

    for p in targets[:1]:
        with p.open("rb") as fh:
            r = load_and_clean(fh, p.name)
        print(f"Validated {p.name}: {len(rows)} raw rows -> {len(r.monthly)} months")

    size_kb = targets[0].stat().st_size / 1024
    print(f"Rows: {len(rows)}, columns: {len(HEADERS)}, size: {size_kb:.0f} KB")
    print(f"Written to {targets[0]} and {targets[1]}")


if __name__ == "__main__":
    main()
