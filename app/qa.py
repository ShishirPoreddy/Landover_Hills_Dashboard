#!/usr/bin/env python3
"""
Q&A System for Municipal Records

Provides direct answering capabilities with numeric totals and evidence.
Handles amount questions, filters parsing, and aggregation queries.

Usage:
    from app.qa import is_amount_question, parse_filters, get_direct_answer
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import text
from .db import engine

# Department patterns for filtering (matching actual database values)
DEPT_PATTERNS = [
    r"PUBLIC WORKS", r"POLICE DEPARTMENT", r"PARKS", r"FINANCE", r"ADMINISTRATION", 
    r"FIRE", r"TRANSPORTATION", r"ROADS", r"STREETS", r"WATER", r"SEWER", 
    r"SEWAGE", r"SANITATION", r"GENERAL GOVERNMENT", r"PLANNING", r"RECREATION",
    r"LIBRARY", r"HEALTH", r"SOCIAL SERVICES", r"EMERGENCY", r"UTILITIES",
    r"PUBLIC SAFETY", r"COMMUNITY DEVELOPMENT", r"HUMAN RESOURCES",
    r"GENERAL OFFICE", r"GENERAL GOVT. INSURANCE", r"MAYOR & COUNCIL", 
    r"MAYOR AND COUNCIL", r"PROFESSIONAL SERVICES", r"PUBLIC ASSOCIATIONS",
    r"ENFORCEMENT FEES", r"ELECTIONS", r"COMMUNITY PROMOTIONS", r"ANNEXATION",
    r"LICENSE FEES", r"MISC. REVENUES", r"MISCELLANEOUS GRANTS", 
    r"MUNICIPAL BUILDING", r"MUNICIPAL BUILDING GRANT", r"POLICE GRANTS",
    r"TAXES", r"TRASH REMOVAL", r"GRANTS"
]

# Amount question patterns
AMOUNT_PATTERNS = [
    r"how much",
    r"what is the total",
    r"total amount",
    r"budget for",
    r"allocated to",
    r"spent on",
    r"cost of",
    r"expense for",
    r"funding for",
    r"dollar amount",
    r"dollars",
    r"budget",
    r"allocation",
    r"expenditure"
]

# Line item patterns
LINE_ITEM_PATTERNS = [
    r"road repairs", r"overtime", r"equipment", r"salaries", r"benefits",
    r"maintenance", r"utilities", r"supplies", r"training", r"travel",
    r"contracts", r"services", r"materials", r"fuel", r"insurance"
]

def is_amount_question(question: str) -> bool:
    """
    Determine if a question is asking for a numeric amount/total.
    
    Args:
        question: The user's question
        
    Returns:
        True if the question appears to be asking for an amount
    """
    question_lower = question.lower()
    
    # Check for amount-related keywords
    for pattern in AMOUNT_PATTERNS:
        if re.search(pattern, question_lower):
            return True
    
    # Check for currency symbols or number patterns
    if re.search(r'\$|dollars?|amount|total|budget', question_lower):
        return True
    
    return False

def parse_filters(question: str) -> Dict[str, Optional[str]]:
    """
    Parse question to extract fiscal year, department, and line item filters.
    
    Args:
        question: The user's question
        
    Returns:
        Dictionary with fiscal_year, department, and line_item filters
    """
    filters = {
        "fiscal_year": None,
        "department": None,
        "line_item": None
    }
    
    question_lower = question.lower()
    
    # Extract fiscal year
    year_patterns = [
        r"fy\s*(\d{2,4})",
        r"fiscal\s+year\s+(\d{2,4})",
        r"(\d{4})\s*budget",
        r"(\d{4})\s*fiscal",
        r"budget\s+(\d{4})",
        r"in\s+(\d{4})",
        r"for\s+(\d{4})",
        r"fy(\d{2})",
        r"fiscal\s+year\s+(\d{2})"
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, question_lower)
        if match:
            year = int(match.group(1))
            # Handle 2-digit years
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            filters["fiscal_year"] = year
            break
    
    # Extract department - handle both exact matches and partial matches
    department_mapping = {
        "police": "POLICE DEPARTMENT",
        "police department": "POLICE DEPARTMENT", 
        "public works": "PUBLIC WORKS",
        "administration": "ADMINISTRATION",
        "taxes": "TAXES",
        "grants": "GRANTS",
        "professional services": "PROFESSIONAL SERVICES",
        "general office": "GENERAL OFFICE",
        "enforcement fees": "ENFORCEMENT FEES",
        "license fees": "LICENSE FEES",
        "trash removal": "TRASH REMOVAL",
        "misc revenues": "MISC. REVENUES",
        "miscellaneous grants": "MISCELLANEOUS GRANTS"
    }
    
    # Check for department matches (case insensitive)
    for key, value in department_mapping.items():
        if re.search(rf'\b{re.escape(key)}\b', question_lower):
            filters["department"] = value
            break
    
    # If no mapping found, try exact pattern matching
    if not filters["department"]:
        for pattern in DEPT_PATTERNS:
            if re.search(rf'\b{re.escape(pattern.lower())}\b', question_lower):
                filters["department"] = pattern
                break
    
    # Extract line item
    for pattern in LINE_ITEM_PATTERNS:
        if re.search(rf'\b{re.escape(pattern)}\b', question_lower):
            filters["line_item"] = pattern
            break
    
    return filters

def get_category_comparison(question: str) -> Optional[Dict[str, Any]]:
    """
    Get comparison data for category comparison questions.
    
    Args:
        question: User's question
        
    Returns:
        Dictionary with comparison data
    """
    filters = parse_filters(question)
    
    if not filters.get("fiscal_year"):
        return None
    
    fiscal_year = filters["fiscal_year"]
    
    with engine.begin() as conn:
        # Get top categories by amount
        query = text("""
            SELECT department, SUM(amount) as total_amount
            FROM budget_facts
            WHERE fiscal_year = :fiscal_year
            GROUP BY department
            ORDER BY total_amount DESC
            LIMIT 10
        """)
        
        result = conn.execute(query, {"fiscal_year": fiscal_year})
        categories = [dict(row) for row in result.mappings().all()]
        
        if not categories:
            return None
        
        return {
            "comparison_type": "category_ranking",
            "fiscal_year": fiscal_year,
            "categories": categories,
            "total_budget": sum(cat["total_amount"] for cat in categories),
            "evidence": categories[:5]  # Top 5 as evidence
        }

def get_trend_analysis(question: str) -> Optional[Dict[str, Any]]:
    """
    Get trend analysis data for questions about changes over time.
    
    Args:
        question: User's question
        
    Returns:
        Dictionary with trend data
    """
    filters = parse_filters(question)
    
    # Extract years from question - look for multiple years
    import re
    year_matches = re.findall(r'(?:fy|fiscal year|year)\s*(\d{2,4})', question.lower())
    years = []
    
    for year_str in year_matches:
        year = int(year_str)
        # Handle 2-digit years
        if year < 100:
            year = 2000 + year if year < 50 else 1900 + year
        years.append(year)
    
    # Remove duplicates and sort
    years = sorted(list(set(years)))
    
    if len(years) < 2:
        return None
    
    with engine.begin() as conn:
        # Get data for both years
        query = text("""
            SELECT fiscal_year, department, SUM(amount) as total_amount
            FROM budget_facts
            WHERE fiscal_year IN :years
            GROUP BY fiscal_year, department
            ORDER BY fiscal_year, total_amount DESC
        """)
        
        result = conn.execute(query, {"years": tuple(years)})
        data = [dict(row) for row in result.mappings().all()]
        
        if not data:
            return None
        
        # Calculate changes
        changes = []
        for dept in set(row["department"] for row in data):
            dept_data = [row for row in data if row["department"] == dept]
            if len(dept_data) == 2:
                old_amount = next(row["total_amount"] for row in dept_data if row["fiscal_year"] == years[0])
                new_amount = next(row["total_amount"] for row in dept_data if row["fiscal_year"] == years[1])
                change_pct = ((new_amount - old_amount) / old_amount * 100) if old_amount > 0 else 0
                
                changes.append({
                    "department": dept,
                    "old_amount": old_amount,
                    "new_amount": new_amount,
                    "change_amount": new_amount - old_amount,
                    "change_percentage": change_pct
                })
        
        # Sort by change amount
        changes.sort(key=lambda x: abs(x["change_amount"]), reverse=True)
        
        return {
            "trend_type": "year_over_year",
            "years": years,
            "changes": changes,
            "evidence": changes[:5]
        }

def get_breakdown_analysis(question: str) -> Optional[Dict[str, Any]]:
    """
    Get breakdown analysis for percentage and share questions.
    
    Args:
        question: User's question
        
    Returns:
        Dictionary with breakdown data
    """
    filters = parse_filters(question)
    
    if not filters.get("fiscal_year"):
        return None
    
    fiscal_year = filters["fiscal_year"]
    
    with engine.begin() as conn:
        # Get total budget first
        total_query = text("""
            SELECT SUM(amount) as total_budget
            FROM budget_facts
            WHERE fiscal_year = :fiscal_year
        """)
        
        total_result = conn.execute(total_query, {"fiscal_year": fiscal_year})
        total_budget = total_result.scalar()
        
        if not total_budget:
            return None
        
        # Get department breakdown
        dept_query = text("""
            SELECT department, SUM(amount) as total_amount
            FROM budget_facts
            WHERE fiscal_year = :fiscal_year
            GROUP BY department
            ORDER BY total_amount DESC
        """)
        
        dept_result = conn.execute(dept_query, {"fiscal_year": fiscal_year})
        departments = [dict(row) for row in dept_result.mappings().all()]
        
        # Calculate percentages for each department
        for dept in departments:
            dept["percentage"] = (dept["total_amount"] / total_budget * 100) if total_budget > 0 else 0
        
        return {
            "breakdown_type": "department_percentages",
            "fiscal_year": fiscal_year,
            "total_budget": total_budget,
            "departments": departments,
            "evidence": departments[:5]
        }

def get_direct_answer(question: str) -> Optional[Dict[str, Any]]:
    """
    Get a direct numeric answer for amount questions.
    
    Args:
        question: The user's question
        
    Returns:
        Dictionary with total, evidence, and filters, or None if not applicable
    """
    if not is_amount_question(question):
        return None
    
    filters = parse_filters(question)
    
    # Build SQL query based on filters
    where_conditions = []
    params = {}
    
    if filters["fiscal_year"]:
        where_conditions.append("bf.fiscal_year = :fiscal_year")
        params["fiscal_year"] = filters["fiscal_year"]
    
    if filters["department"]:
        where_conditions.append("UPPER(bf.department) = UPPER(:department)")
        params["department"] = filters["department"]
    
    if filters["line_item"]:
        where_conditions.append("LOWER(bf.line_item) LIKE :line_item")
        params["line_item"] = f"%{filters['line_item'].lower()}%"
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Get total amount
    with engine.begin() as conn:
        total_query = f"""
            SELECT SUM(bf.amount) as total, COUNT(*) as count
            FROM budget_facts bf
            {where_clause}
        """
        result = conn.execute(text(total_query), params).mappings().first()
        
        if not result or result["total"] is None:
            return None
        
        total = float(result["total"])
        count = result["count"]
    
    # Get top evidence items
    evidence_query = f"""
        SELECT 
            bf.id,
            bf.fiscal_year,
            bf.department,
            bf.line_item,
            bf.amount,
            d.file_name
        FROM budget_facts bf
        LEFT JOIN documents d ON bf.document_id = d.id
        {where_clause}
        ORDER BY bf.amount DESC
        LIMIT 5
    """
    
    with engine.begin() as conn:
        evidence = conn.execute(text(evidence_query), params).mappings().all()
    
    # Format evidence for response
    evidence_list = []
    for item in evidence:
        evidence_list.append({
            "id": item["id"],
            "fiscal_year": item["fiscal_year"],
            "department": item["department"],
            "line_item": item["line_item"],
            "amount": float(item["amount"]),
            "file_name": item["file_name"]
        })
    
    return {
        "total": total,
        "count": count,
        "evidence": evidence_list,
        "filters": filters
    }

def get_year_over_year_comparison(department: str, fiscal_year: int) -> Optional[Dict[str, Any]]:
    """
    Get year-over-year comparison for a department.
    
    Args:
        department: Department name
        fiscal_year: Current fiscal year
        
    Returns:
        Dictionary with current, previous, and change data
    """
    with engine.begin() as conn:
        # Get current year total
        current_query = """
            SELECT SUM(amount) as total
            FROM budget_facts
            WHERE department = :department AND fiscal_year = :fiscal_year
        """
        current_result = conn.execute(text(current_query), {
            "department": department,
            "fiscal_year": fiscal_year
        }).scalar_one()
        
        # Get previous year total
        prev_year = fiscal_year - 1
        prev_query = """
            SELECT SUM(amount) as total
            FROM budget_facts
            WHERE department = :department AND fiscal_year = :fiscal_year
        """
        prev_result = conn.execute(text(prev_query), {
            "department": department,
            "fiscal_year": prev_year
        }).scalar_one()
        
        if current_result is None or prev_result is None:
            return None
        
        current_total = float(current_result)
        prev_total = float(prev_result)
        
        if prev_total == 0:
            change_pct = 0
        else:
            change_pct = (current_total - prev_total) / prev_total
        
        return {
            "department": department,
            "current_year": fiscal_year,
            "previous_year": prev_year,
            "current_total": current_total,
            "previous_total": prev_total,
            "change_amount": current_total - prev_total,
            "change_pct": change_pct
        }

def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:,.2f}"

def format_percentage(percentage: float) -> str:
    """Format percentage string."""
    return f"{percentage:.1%}"

# Unit tests for critical functions
def test_parse_filters():
    """Test parse_filters function with common queries."""
    test_cases = [
        ("How much for Public Works in 2024?", {"fiscal_year": 2024, "department": "Public Works", "line_item": None}),
        ("Total road repairs FY25", {"fiscal_year": 2025, "department": None, "line_item": "road repairs"}),
        ("Police overtime 2025", {"fiscal_year": 2025, "department": "Police", "line_item": "overtime"}),
        ("What is the budget for Administration?", {"fiscal_year": None, "department": "Administration", "line_item": None}),
        ("How much was spent on equipment?", {"fiscal_year": None, "department": None, "line_item": "equipment"}),
    ]
    
    for question, expected in test_cases:
        result = parse_filters(question)
        assert result == expected, f"Failed for '{question}': got {result}, expected {expected}"
    
    print("✓ parse_filters tests passed")

def test_is_amount_question():
    """Test is_amount_question function."""
    amount_questions = [
        "How much is allocated to road repairs?",
        "What is the total budget?",
        "How much did we spend on police?",
        "What's the dollar amount for parks?",
        "Total funding for public works"
    ]
    
    non_amount_questions = [
        "What is the purpose of this budget?",
        "When was this document created?",
        "Who approved this budget?",
        "What are the main priorities?"
    ]
    
    for question in amount_questions:
        assert is_amount_question(question), f"Should be amount question: {question}"
    
    for question in non_amount_questions:
        assert not is_amount_question(question), f"Should not be amount question: {question}"
    
    print("✓ is_amount_question tests passed")

if __name__ == "__main__":
    # Run tests
    test_parse_filters()
    test_is_amount_question()
    print("All Q&A tests passed!")



