from __future__ import annotations

from typing import Any, Dict, List


PO4_COLUMNS = [
    "Item No",
    "Discipline",
    "Category",
    "Description",
    "Qty",
    "Unit",
    "Formula",
    "Source Link",
    "Notes",
]

PO5_COLUMNS = [
    "Category",
    "Qty",
    "Unit",
    "Material Rate",
    "Labor Rate",
    "Material Total",
    "Labor Total",
    "Subtotal",
]

PO6_FIELDS = [
    "Direct Cost",
    "Factor F",
    "VAT",
    "Final Bid Amount",
]

FACTOR_F_COLUMNS = [
    "Cost Bracket Min",
    "Cost Bracket Max",
    "FactorF_Building",
    "FactorF_Roads",
]


def build_workbook_template() -> Dict[str, Any]:
    return {
        "sheets": {
            "PO-4": {"type": "table", "columns": PO4_COLUMNS},
            "PO-5": {"type": "table", "columns": PO5_COLUMNS},
            "PO-6": {"type": "summary", "fields": PO6_FIELDS},
            "FactorF_Table": {"type": "lookup", "columns": FACTOR_F_COLUMNS},
            "Proofs": {"type": "audit", "columns": ["Element ID", "Formula", "Proof JSON", "Source Link"]},
            "Manual Review": {
                "type": "queue",
                "columns": ["Severity", "Code", "Message", "Source File", "Resolution Status"],
            },
        },
        "named_ranges": {
            "DIRECT_COST": "sum(PO-5!Subtotal)",
            "FACTOR_F": "lookup(DIRECT_COST, FactorF_Table)",
            "FINAL_BID": "DIRECT_COST * FACTOR_F",
        },
    }


def workbook_tabs() -> List[str]:
    return ["PO-4", "PO-5", "PO-6", "Proofs", "Manual Review", "FactorF_Table"]
