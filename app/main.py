# app/main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from .rag import retrieve, get_aggregated_answer, get_comparison_data
from .llm import answer_with_citations, classify_question, generate_detailed_insights
from .qa import get_category_comparison, get_trend_analysis, get_breakdown_analysis, parse_filters
from .db import engine
import os
import httpx
import re

app = FastAPI(title="Landover Agents API")

def get_intent_from_question(question: str):
    """
    Use LLM to convert natural language question into structured intent.
    Returns a JSON intent that can be processed by deterministic APIs.
    """
    system_prompt = """You are a municipal budget analyst chatbot.

SOURCE OF TRUTH
- Numeric answers MUST come from API/tool calls that wrap Postgres views:
  - v_year_totals (sum per year)
  - v_year_yoy (YoY deltas per year)
  - v_category_totals (sum per category within a year)
  - v_line_items (sum per line item per category/year)
  - Optional: v_category_shares (percent of year total per category)
- FY26 is PARTIAL. If any answer involves FY26, append: "Note: FY26 data is partial."

OUTPUT CONTRACT
- ALWAYS return a single JSON object matching one of the schemas below.
- Do not include prose outside JSON. Do not invent numbers. The app will call tools and format the final message.

ALLOWED YEARS: ["FY24","FY25","FY26"]
ALLOWED ACTIONS:
1) {"action":"year_total","year":<Year>}
2) {"action":"yoy_difference","year_from":<Year>,"year_to":<Year>}
3) {"action":"yoy_all"}                         -- ask for every year difference
4) {"action":"category_rank","year":<Year>,"top_n":<int default=10>}
5) {"action":"category_share","year":<Year>,"category":<string>}
6) {"action":"line_item_total","year":<Year>,"category":<string>,"line_item":<string>}
7) {"action":"help"}                            -- if the request is unclear, ask ONE precise follow-up (in field "question")

GUARDRAILS
- If a required field is missing (e.g., no year), fill the smallest reasonable default:
  - For unqualified totals/rankings, default to the latest complete year "FY25".
  - Always include "partial_data": true when "year" == "FY26".
- If the user's category/line item doesn't exist or is ambiguous, return {"action":"help","question":"..."}.
- Normalize simple typos ("fy 25" -> "FY25"), but never hallucinate categories.
- No free-form math. The host app computes deltas/percent after the tool call."""

    few_shot_examples = """USER: What is the total budget for FY25?
ASSISTANT:
{"action":"year_total","year":"FY25"}

USER: How much did the budget change from FY24 to FY25?
ASSISTANT:
{"action":"yoy_difference","year_from":"FY24","year_to":"FY25"}

USER: What was the budget difference every year?
ASSISTANT:
{"action":"yoy_all"}

USER: Which category got the most in FY25?
ASSISTANT:
{"action":"category_rank","year":"FY25","top_n":5}

USER: What percentage of FY25 came from Taxes?
ASSISTANT:
{"action":"category_share","year":"FY25","category":"TAXES"}

USER: How much did Administration spend on Payroll Taxes in FY24?
ASSISTANT:
{"action":"line_item_total","year":"FY24","category":"ADMINISTRATION","line_item":"Payroll Taxes"}

USER: What's the total this year?
ASSISTANT:
{"action":"year_total","year":"FY26","partial_data":true}"""

    try:
        # For now, let's use simple pattern matching as a fallback
        # This will be replaced with proper LLM intent recognition once the API is working
        question_lower = question.lower()
        
        # Simple pattern matching fallback
        if "total budget" in question_lower or "total for" in question_lower:
            year_match = re.search(r"fy(\d{2,4})", question_lower)
            year = f"FY{year_match.group(1)}" if year_match else "FY25"
            return {"action": "year_total", "year": year}
        
        elif "difference" in question_lower:
            # Extract both years from the question
            year_matches = re.findall(r"fy(\d{2,4})", question_lower)
            if len(year_matches) >= 2:
                year1 = f"FY{year_matches[0]}"
                year2 = f"FY{year_matches[1]}"
                return {"action": "yoy_difference", "year_from": year1, "year_to": year2}
            elif len(year_matches) == 1:
                # If only one year specified, assume comparison with previous year
                year = f"FY{year_matches[0]}"
                if year == "FY25":
                    return {"action": "yoy_difference", "year_from": "FY24", "year_to": "FY25"}
                elif year == "FY26":
                    return {"action": "yoy_difference", "year_from": "FY25", "year_to": "FY26"}
            else:
                # Default to FY24 to FY25 if no years found
                return {"action": "yoy_difference", "year_from": "FY24", "year_to": "FY25"}
        
        elif "percentage" in question_lower or "make up" in question_lower:
            year_match = re.search(r"fy(\d{2,4})", question_lower)
            year = f"FY{year_match.group(1)}" if year_match else "FY25"
            if "taxes" in question_lower:
                return {"action": "category_share", "year": year, "category": "TAXES"}
            elif "police" in question_lower:
                return {"action": "category_share", "year": year, "category": "POLICE DEPARTMENT"}
            elif "public works" in question_lower:
                return {"action": "category_share", "year": year, "category": "PUBLIC WORKS"}
            elif "administration" in question_lower:
                return {"action": "category_share", "year": year, "category": "ADMINISTRATION"}
            elif "grants" in question_lower:
                return {"action": "category_share", "year": year, "category": "GRANTS"}
            else:
                # If no specific category mentioned, default to taxes
                return {"action": "category_share", "year": year, "category": "TAXES"}
        
        elif "most funding" in question_lower or "highest" in question_lower:
            year_match = re.search(r"fy(\d{2,4})", question_lower)
            year = f"FY{year_match.group(1)}" if year_match else "FY25"
            return {"action": "category_rank", "year": year, "top_n": 5}
        
        elif "show me" in question_lower or "spending" in question_lower:
            year_match = re.search(r"fy(\d{2,4})", question_lower)
            year = f"FY{year_match.group(1)}" if year_match else "FY25"
            if "public works" in question_lower:
                return {"action": "category_rank", "year": year, "top_n": 10}
        
        # Percent change questions
        elif "percent change" in question_lower or "change from" in question_lower:
            # Extract both years
            year_matches = re.findall(r"fy(\d{2,4})", question_lower)
            if len(year_matches) >= 2:
                year_from = f"FY{year_matches[0]}"
                year_to = f"FY{year_matches[1]}"
                
                # Extract category
                category = None
                if "taxes" in question_lower:
                    category = "TAXES"
                elif "police" in question_lower:
                    category = "POLICE DEPARTMENT"
                elif "public works" in question_lower:
                    category = "PUBLIC WORKS"
                elif "administration" in question_lower:
                    category = "ADMINISTRATION"
                elif "grants" in question_lower:
                    category = "GRANTS"
                
                if category:
                    return {
                        "action": "percent_change",
                        "category": category,
                        "year_from": year_from,
                        "year_to": year_to,
                        "partial_data": year_to == "FY26"
                    }
        
        # Scenario cuts
        elif any(phrase in question_lower for phrase in ["cut", "reduce", "budget cut"]):
            # Extract percentage
            percent_match = re.search(r"(\d+)%", question_lower)
            cut_pct = float(percent_match.group(1)) if percent_match else 0
            
            # Extract year
            year_match = re.search(r"fy(\d{2,4})", question_lower)
            year = f"FY{year_match.group(1)}" if year_match else "FY25"
            
            # Determine scope
            if "all departments" in question_lower or "across" in question_lower:
                return {
                    "action": "scenario_cut",
                    "year": year,
                    "cut_pct": cut_pct,
                    "scope": "all"
                }
            else:
                # Extract category for specific cut
                category = None
                if "police" in question_lower:
                    category = "POLICE DEPARTMENT"
                elif "taxes" in question_lower:
                    category = "TAXES"
                elif "administration" in question_lower:
                    category = "ADMINISTRATION"
                elif "public works" in question_lower:
                    category = "PUBLIC WORKS"
                elif "grants" in question_lower:
                    category = "GRANTS"
                
                if category:
                    return {
                        "action": "scenario_cut",
                        "year": year,
                        "cut_pct": cut_pct,
                        "scope": "category",
                        "category": category
                    }
        
        # What-if / Forecasting scenarios (legacy support)
        elif any(phrase in question_lower for phrase in ["if ", "what if", "increase", "decrease", "lose", "gain", "hypothetical"]):
            # Extract percentage change
            percent_match = re.search(r"(\d+)%", question_lower)
            percentage = float(percent_match.group(1)) if percent_match else 0
            
            # Extract category
            category = None
            if "taxes" in question_lower:
                category = "TAXES"
            elif "police" in question_lower:
                category = "POLICE DEPARTMENT"
            elif "public works" in question_lower:
                category = "PUBLIC WORKS"
            elif "administration" in question_lower:
                category = "ADMINISTRATION"
            elif "grants" in question_lower:
                category = "GRANTS"
            
            # Extract year
            year_match = re.search(r"fy(\d{2,4})", question_lower)
            year = f"FY{year_match.group(1)}" if year_match else "FY25"
            
            if category and percentage:
                return {
                    "action": "what_if_scenario", 
                    "year": year, 
                    "category": category, 
                    "percentage_change": percentage,
                    "scenario_type": "increase" if "increase" in question_lower or "gain" in question_lower else "decrease"
                }
        
        else:
            return {"action": "help", "question": "I couldn't understand your question. Could you rephrase it?"}
            
    except Exception as e:
        print(f"DEBUG: Error getting intent: {e}")
        return {"action": "help", "question": "I encountered an error. Could you rephrase your question?"}

def try_budget_api_answer(question: str):
    """
    New intent-based budget question handler.
    Uses LLM to parse intent, then calls deterministic APIs.
    """
    try:
        print(f"DEBUG: try_budget_api_answer called with: {question}")
        
        # Get structured intent from LLM
        intent = get_intent_from_question(question)
        print(f"DEBUG: Got intent: {intent}")
        
        # Handle the intent with deterministic API calls
        result = handle_intent_deterministically(intent)
        print(f"DEBUG: Got result: {result}")
        
        return result
        
    except Exception as e:
        print(f"Error in try_budget_api_answer: {e}")
        return None

def handle_intent_deterministically(intent):
    """
    Handle structured intent with deterministic database queries.
    """
    try:
        action = intent.get("action")
        
        if action == "year_total":
            year = intent.get("year", "FY25")
            with engine.begin() as conn:
                result = conn.execute(text("SELECT total FROM v_year_totals WHERE fiscal_year = :year"), {"year": year})
                row = result.fetchone()
                if row:
                    total = row[0]
                    partial_note = " Note: FY26 data is partial." if year == "FY26" else ""
                    return {
                        "answer": f"Total {year} budget: ${total:,}. Source: v_year_totals({year}).{partial_note}",
                        "evidence": [{"fiscal_year": year, "total": total}],
                        "total": total,
                        "filters": {"fiscal_year": year},
                        "question_type": "year_total"
                    }
        
        elif action == "yoy_difference":
            year_from = intent.get("year_from", "FY24")
            year_to = intent.get("year_to", "FY25")
            with engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT fiscal_year, total FROM v_year_totals 
                    WHERE fiscal_year IN (:year_from, :year_to)
                    ORDER BY fiscal_year
                """), {"year_from": year_from, "year_to": year_to})
                rows = result.fetchall()
                
                if len(rows) == 2:
                    from_total = rows[0][1] if rows[0][0] == year_from else rows[1][1]
                    to_total = rows[1][1] if rows[1][0] == year_to else rows[0][1]
                    delta = to_total - from_total
                    partial_note = " Note: FY26 data is partial." if year_to == "FY26" or year_from == "FY26" else ""
                    return {
                        "answer": f"Change from {year_from} to {year_to}: ${delta:,} (${from_total:,} → ${to_total:,}). Source: v_year_yoy.{partial_note}",
                        "evidence": [
                            {"fiscal_year": year_from, "total": from_total},
                            {"fiscal_year": year_to, "total": to_total}
                        ],
                        "total": to_total,
                        "filters": {"year_from": year_from, "year_to": year_to},
                        "question_type": "yoy_difference"
                    }
        
        elif action == "yoy_all":
            with engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT fiscal_year, total, yoy_change FROM v_year_yoy ORDER BY fiscal_year
                """))
                rows = result.fetchall()
                
                lines = []
                for row in rows:
                    fiscal_year, total, yoy_change = row
                    if yoy_change is None:
                        lines.append(f"{fiscal_year}: base ${total:,}")
                    else:
                        sign = "+" if yoy_change >= 0 else "−"
                        lines.append(f"{fiscal_year}: {sign}${abs(yoy_change):,} (total ${total:,})")
                
                partial_note = " Note: FY26 data is partial." if any(row[0] == "FY26" for row in rows) else ""
                return {
                    "answer": f"Year-over-year changes:\n- " + "\n- ".join(lines) + f"\nSource: v_year_yoy.{partial_note}",
                    "evidence": [{"fiscal_year": row[0], "total": row[1], "yoy_change": row[2]} for row in rows],
                    "filters": {"action": "yoy_all"},
                    "question_type": "yoy_all"
                }
        
        elif action == "category_rank":
            year = intent.get("year", "FY25")
            top_n = intent.get("top_n", 10)
            with engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT category, total FROM v_category_totals 
                    WHERE fiscal_year = :year ORDER BY total DESC LIMIT :limit
                """), {"year": year, "limit": top_n})
                rows = result.fetchall()
                
                if rows:
                    lines = [f"{i+1}. {row[0]}: ${row[1]:,}" for i, row in enumerate(rows)]
                    partial_note = " Note: FY26 data is partial." if year == "FY26" else ""
                    return {
                        "answer": f"Top {top_n} categories in {year}:\n" + "\n".join(lines) + f"\nSource: v_category_totals({year}).{partial_note}",
                        "evidence": [{"category": row[0], "total": row[1], "fiscal_year": year} for row in rows],
                        "filters": {"year": year, "top_n": top_n},
                        "question_type": "category_rank"
                    }
        
        elif action == "category_share":
            year = intent.get("year", "FY25")
            category = intent.get("category", "").upper()
            with engine.begin() as conn:
                # Try to get percentage from v_category_shares first
                result = conn.execute(text("""
                    SELECT pct_of_year, total FROM v_category_shares 
                    WHERE fiscal_year = :year AND UPPER(category) = UPPER(:category)
                """), {"year": year, "category": category})
                row = result.fetchone()
                
                if row:
                    percentage, total = row
                    partial_note = " Note: FY26 data is partial." if year == "FY26" else ""
                    return {
                        "answer": f"{category} in {year}: ${total:,} ({percentage}% of total). Source: v_category_shares({year}).{partial_note}",
                        "evidence": [{"category": category, "total": total, "percentage": percentage, "fiscal_year": year}],
                        "total": total,
                        "filters": {"year": year, "category": category},
                        "question_type": "category_share"
                    }
                else:
                    # Calculate percentage manually if view doesn't exist
                    result = conn.execute(text("""
                        SELECT c.total as category_total, y.total as year_total
                        FROM v_category_totals c
                        JOIN v_year_totals y ON y.fiscal_year = c.fiscal_year
                        WHERE c.fiscal_year = :year AND UPPER(c.category) = UPPER(:category)
                    """), {"year": year, "category": category})
                    row = result.fetchone()
                    
                    if row:
                        category_total, year_total = row
                        percentage = round((category_total / year_total) * 100, 1)
                        partial_note = " Note: FY26 data is partial." if year == "FY26" else ""
                        return {
                            "answer": f"{category} in {year}: ${category_total:,} ({percentage}% of total). Source: v_category_totals({year}).{partial_note}",
                            "evidence": [{"category": category, "total": category_total, "percentage": percentage, "fiscal_year": year}],
                            "total": category_total,
                            "filters": {"year": year, "category": category},
                            "question_type": "category_share"
                        }
        
        elif action == "line_item_total":
            year = intent.get("year", "FY25")
            category = intent.get("category", "").upper()
            line_item = intent.get("line_item", "")
            with engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT total FROM v_line_items 
                    WHERE fiscal_year = :year AND UPPER(category) = UPPER(:category) 
                    AND UPPER(line_item) = UPPER(:line_item)
                """), {"year": year, "category": category, "line_item": line_item})
                row = result.fetchone()
                
                if row:
                    total = row[0]
                    partial_note = " Note: FY26 data is partial." if year == "FY26" else ""
                    return {
                        "answer": f"{year} {category} → {line_item}: ${total:,}. Source: v_line_items.{partial_note}",
                        "evidence": [{"category": category, "line_item": line_item, "total": total, "fiscal_year": year}],
                        "total": total,
                        "filters": {"year": year, "category": category, "line_item": line_item},
                        "question_type": "line_item_total"
                    }
        
        elif action == "what_if_scenario":
            year = intent.get("year", "FY25")
            category = intent.get("category", "")
            percentage_change = intent.get("percentage_change", 0)
            scenario_type = intent.get("scenario_type", "increase")
            
            with engine.begin() as conn:
                # Get current category total
                result = conn.execute(text("""
                    SELECT total FROM v_category_totals 
                    WHERE fiscal_year = :year AND UPPER(category) = UPPER(:category)
                """), {"year": year, "category": category})
                row = result.fetchone()
                
                if row:
                    current_total = row[0]
                    
                    # Calculate new total based on scenario
                    if scenario_type == "increase":
                        new_total = current_total * (1 + percentage_change / 100)
                        change_amount = new_total - current_total
                        change_text = "increased"
                    else:
                        new_total = current_total * (1 - percentage_change / 100)
                        change_amount = current_total - new_total
                        change_text = "decreased"
                    
                    # Get year total to calculate new percentage
                    year_result = conn.execute(text("""
                        SELECT total FROM v_year_totals WHERE fiscal_year = :year
                    """), {"year": year})
                    year_row = year_result.fetchone()
                    
                    if year_row:
                        year_total = year_row[0]
                        current_percentage = (current_total / year_total) * 100
                        new_percentage = (new_total / year_total) * 100
                        
                        return {
                            "answer": f"If {category} {change_text} by {percentage_change}% in {year}: "
                                    f"New total would be ${new_total:,.0f} (change of ${change_amount:,.0f}). "
                                    f"This would change its share from {current_percentage:.1f}% to {new_percentage:.1f}% of the total budget.",
                            "evidence": [
                                {
                                    "category": category,
                                    "fiscal_year": year,
                                    "current_total": current_total,
                                    "new_total": new_total,
                                    "percentage_change": percentage_change,
                                    "scenario_type": scenario_type,
                                    "current_percentage": current_percentage,
                                    "new_percentage": new_percentage
                                }
                            ],
                            "total": new_total,
                            "filters": {"year": year, "category": category, "scenario_type": scenario_type},
                            "question_type": "what_if_scenario"
                        }
                    else:
                        return {
                            "answer": f"Could not calculate the impact because year total data for {year} is not available.",
                            "evidence": [],
                            "filters": {"year": year, "category": category},
                            "question_type": "what_if_scenario"
                        }
                else:
                    return {
                        "answer": f"Could not find {category} data for {year} to perform the scenario analysis.",
                        "evidence": [],
                        "filters": {"year": year, "category": category},
                        "question_type": "what_if_scenario"
                    }
        
        elif action == "percent_change":
            year_from = intent.get("year_from", "FY24")
            year_to = intent.get("year_to", "FY25")
            category = intent.get("category", "")
            
            with engine.begin() as conn:
                # Get totals for both years
                result_from = conn.execute(text("""
                    SELECT total FROM v_category_totals 
                    WHERE fiscal_year = :year AND UPPER(category) = UPPER(:category)
                """), {"year": year_from, "category": category})
                row_from = result_from.fetchone()
                
                result_to = conn.execute(text("""
                    SELECT total FROM v_category_totals 
                    WHERE fiscal_year = :year AND UPPER(category) = UPPER(:category)
                """), {"year": year_to, "category": category})
                row_to = result_to.fetchone()
                
                if row_from and row_to:
                    total_from = row_from[0]
                    total_to = row_to[0]
                    
                    # Calculate percent change
                    if total_from == 0:
                        if total_to == 0:
                            percent_change = 0.0
                            change_text = "0.0%"
                        else:
                            percent_change = "not defined (no prior amount)"
                            change_text = f"not defined (no prior amount) - absolute change: ${total_to:,.0f}"
                    else:
                        percent_change = ((total_to - total_from) / abs(total_from)) * 100
                        change_text = f"{percent_change:.1f}%"
                    
                    abs_change = total_to - total_from
                    partial_note = " Note: FY26 data is partial." if year_to == "FY26" else ""
                    
                    return {
                        "answer": f"{category} changed by {change_text} from {year_from} to {year_to}, moving from ${total_from:,.0f} to ${total_to:,.0f} (${abs_change:,.0f}). Source: v_category_totals({year_from},{year_to}).{partial_note}",
                        "evidence": [
                            {
                                "category": category,
                                "year_from": year_from,
                                "year_to": year_to,
                                "total_from": total_from,
                                "total_to": total_to,
                                "percent_change": percent_change,
                                "abs_change": abs_change
                            }
                        ],
                        "total": total_to,
                        "filters": {"year_from": year_from, "year_to": year_to, "category": category},
                        "question_type": "percent_change"
                    }
                else:
                    return {
                        "answer": f"Could not find {category} data for {year_from} or {year_to} to calculate percent change.",
                        "evidence": [],
                        "filters": {"year_from": year_from, "year_to": year_to, "category": category},
                        "question_type": "percent_change"
                    }
        
        elif action == "scenario_cut":
            year = intent.get("year", "FY25")
            cut_pct = intent.get("cut_pct", 0)
            scope = intent.get("scope", "all")
            category = intent.get("category", "")
            
            with engine.begin() as conn:
                if scope == "all":
                    # Get all categories and year total
                    result = conn.execute(text("""
                        SELECT category, total FROM v_category_totals 
                        WHERE fiscal_year = :year ORDER BY total DESC
                    """), {"year": year})
                    rows = result.fetchall()
                    
                    year_result = conn.execute(text("""
                        SELECT total FROM v_year_totals WHERE fiscal_year = :year
                    """), {"year": year})
                    year_row = year_result.fetchone()
                    
                    if rows and year_row:
                        old_total = year_row[0]
                        new_totals = []
                        new_total = 0
                        
                        for row in rows:
                            category_name, old_amount = row
                            new_amount = old_amount * (1 - cut_pct / 100)
                            new_totals.append({
                                "category": category_name,
                                "old_total": old_amount,
                                "new_total": new_amount,
                                "savings": old_amount - new_amount
                            })
                            new_total += new_amount
                        
                        savings = old_total - new_total
                        partial_note = " Note: FY26 data is partial." if year == "FY26" else ""
                        
                        # Create category list (top 5 by savings)
                        category_list = []
                        for i, item in enumerate(sorted(new_totals, key=lambda x: x["savings"], reverse=True)[:5]):
                            category_list.append(f"- {item['category']}: old ${item['old_total']:,.0f}, new ${item['new_total']:,.0f}")
                        
                        category_text = "\n".join(category_list)
                        if len(new_totals) > 5:
                            category_text += "\n- Others scale similarly."
                        
                        return {
                            "answer": f"A {cut_pct}% across-the-board reduction in {year} would save ${savings:,.0f} and reduce the total from ${old_total:,.0f} to ${new_total:,.0f}. By category:\n{category_text}\nSource: v_category_totals({year}).{partial_note}",
                            "evidence": new_totals,
                            "total": new_total,
                            "filters": {"year": year, "cut_pct": cut_pct, "scope": scope},
                            "question_type": "scenario_cut"
                        }
                
                elif scope == "category" and category:
                    # Get category total and year total
                    result = conn.execute(text("""
                        SELECT total FROM v_category_totals 
                        WHERE fiscal_year = :year AND UPPER(category) = UPPER(:category)
                    """), {"year": year, "category": category})
                    row = result.fetchone()
                    
                    year_result = conn.execute(text("""
                        SELECT total FROM v_year_totals WHERE fiscal_year = :year
                    """), {"year": year})
                    year_row = year_result.fetchone()
                    
                    if row and year_row:
                        old_category_total = row[0]
                        old_year_total = year_row[0]
                        new_category_total = old_category_total * (1 - cut_pct / 100)
                        new_year_total = old_year_total - (old_category_total - new_category_total)
                        savings = old_category_total - new_category_total
                        
                        partial_note = " Note: FY26 data is partial." if year == "FY26" else ""
                        
                        return {
                            "answer": f"A {cut_pct}% cut to {category} in {year} would save ${savings:,.0f} and reduce the total budget from ${old_year_total:,.0f} to ${new_year_total:,.0f}. {category} would go from ${old_category_total:,.0f} to ${new_category_total:,.0f}. Source: v_category_totals({year}).{partial_note}",
                            "evidence": [
                                {
                                    "category": category,
                                    "year": year,
                                    "old_category_total": old_category_total,
                                    "new_category_total": new_category_total,
                                    "old_year_total": old_year_total,
                                    "new_year_total": new_year_total,
                                    "savings": savings,
                                    "cut_pct": cut_pct
                                }
                            ],
                            "total": new_year_total,
                            "filters": {"year": year, "cut_pct": cut_pct, "scope": scope, "category": category},
                            "question_type": "scenario_cut"
                        }
        
        elif action == "help":
            return {
                "answer": intent.get("question", "Could you please rephrase your question?"),
                "evidence": [],
                "filters": {"action": "help"},
                "question_type": "help"
            }
        
        # If no action matched, return None to fall back to LLM
        return None
        
    except Exception as e:
        print(f"Error in handle_intent_deterministically: {e}")
        return None

# Add CORS middleware for local dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Ask(BaseModel):
    question: str

class SummaryResponse(BaseModel):
    text: str
    generated_at: str

class FindingResponse(BaseModel):
    id: int
    document_id: int
    rule: str
    severity: str
    note: str
    created_at: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(payload: Ask):
    """
    Enhanced Q&A endpoint with framework-based question handling.
    Supports all question types from the ai_assistant_budget_questions.json framework.
    Now uses PostgreSQL views for accurate numeric answers.
    """
    try:
        # First, try to answer with direct budget API data
        budget_answer = try_budget_api_answer(payload.question)
        if budget_answer:
            # Debug logging for budget API responses
            print(f"DEBUG budget_answer: {budget_answer}")
            return budget_answer
        
        # Fall back to LLM-based approach for complex questions
        question_type = classify_question(payload.question)
        
        # Handle different question types
        if question_type == "category_comparisons":
            comparison_data = get_category_comparison(payload.question)
            if comparison_data:
                evidence = comparison_data.get("evidence", [])
                categories = comparison_data.get("categories", [])
                
                # Create specific responses for different comparison questions
                if "most funding" in payload.question.lower():
                    if categories:
                        top_category = categories[0]
                        dept_name = top_category["department"].replace("_", " ").title()
                        amount = top_category["total_amount"]
                        fiscal_year = comparison_data.get("fiscal_year")
                        answer = f"{dept_name} received the most funding in FY{fiscal_year} with ${amount:,.2f}."
                    else:
                        answer = "I couldn't determine which category received the most funding."
                elif "compare" in payload.question.lower():
                    # Handle comparison questions
                    filters = parse_filters(payload.question)
                    target_dept = filters.get("department")
                    if target_dept and categories:
                        for cat in categories:
                            if cat["department"] == target_dept:
                                dept_name = cat["department"].replace("_", " ").title()
                                amount = cat["total_amount"]
                                fiscal_year = comparison_data.get("fiscal_year")
                                answer = f"{dept_name} had a budget of ${amount:,.2f} in FY{fiscal_year}."
                                break
                        else:
                            answer = f"I couldn't find budget data for {target_dept.replace('_', ' ').title()}."
                    else:
                        answer = "I found budget comparison data, but couldn't identify the specific departments to compare."
                elif "rank" in payload.question.lower():
                    # Handle ranking questions
                    filters = parse_filters(payload.question)
                    target_dept = filters.get("department")
                    if target_dept and categories:
                        for i, cat in enumerate(categories):
                            if cat["department"] == target_dept:
                                rank = i + 1
                                dept_name = cat["department"].replace("_", " ").title()
                                amount = cat["total_amount"]
                                fiscal_year = comparison_data.get("fiscal_year")
                                answer = f"{dept_name} ranked #{rank} in FY{fiscal_year} with ${amount:,.2f}."
                                break
                        else:
                            answer = f"I couldn't find {target_dept.replace('_', ' ').title()} in the budget rankings."
                    else:
                        answer = "I couldn't determine the ranking for the specified department."
                else:
                    # Default comparison response
                    answer = answer_with_citations(
                        payload.question,
                        evidence,
                        total=comparison_data.get("total_budget"),
                        filters={"question_type": "category_comparison"}
                    )
                
                return {
                    "answer": answer,
                    "evidence": evidence,
                    "comparison_data": comparison_data,
                    "question_type": question_type
                }
        
        elif question_type == "trend_analysis":
            trend_data = get_trend_analysis(payload.question)
            if trend_data:
                evidence = trend_data.get("evidence", [])
                changes = trend_data.get("changes", [])
                years = trend_data.get("years", [])
                
                # Create specific responses for trend questions
                if "how did" in payload.question.lower() and "change" in payload.question.lower():
                    # Handle specific department change questions
                    filters = parse_filters(payload.question)
                    target_dept = filters.get("department")
                    if target_dept and changes:
                        for change in changes:
                            if change["department"] == target_dept:
                                dept_name = change["department"].replace("_", " ").title()
                                change_pct = change["change_percentage"]
                                change_amount = change["change_amount"]
                                old_amount = change["old_amount"]
                                new_amount = change["new_amount"]
                                
                                if change_pct > 0:
                                    answer = f"{dept_name} funding increased by {change_pct:.1f}% from ${old_amount:,.2f} to ${new_amount:,.2f} between FY{years[0]} and FY{years[1]}."
                                elif change_pct < 0:
                                    answer = f"{dept_name} funding decreased by {abs(change_pct):.1f}% from ${old_amount:,.2f} to ${new_amount:,.2f} between FY{years[0]} and FY{years[1]}."
                                else:
                                    answer = f"{dept_name} funding remained unchanged at ${old_amount:,.2f} between FY{years[0]} and FY{years[1]}."
                                break
                        else:
                            answer = f"I couldn't find trend data for {target_dept.replace('_', ' ').title()}."
                    else:
                        answer = "I found trend data, but couldn't identify the specific department to analyze."
                elif "grew the most" in payload.question.lower():
                    # Find the department with the largest positive change
                    positive_changes = [c for c in changes if c["change_percentage"] > 0]
                    if positive_changes:
                        top_growth = max(positive_changes, key=lambda x: x["change_percentage"])
                        dept_name = top_growth["department"].replace("_", " ").title()
                        growth_pct = top_growth["change_percentage"]
                        answer = f"{dept_name} grew the most with a {growth_pct:.1f}% increase between FY{years[0]} and FY{years[1]}."
                    else:
                        answer = f"No departments showed growth between FY{years[0]} and FY{years[1]}."
                elif "decreased" in payload.question.lower():
                    # Find departments with decreases
                    negative_changes = [c for c in changes if c["change_percentage"] < 0]
                    if negative_changes:
                        largest_decrease = min(negative_changes, key=lambda x: x["change_percentage"])
                        dept_name = largest_decrease["department"].replace("_", " ").title()
                        decrease_pct = abs(largest_decrease["change_percentage"])
                        answer = f"{dept_name} had the largest decrease of {decrease_pct:.1f}% between FY{years[0]} and FY{years[1]}."
                    else:
                        answer = f"No departments showed decreases between FY{years[0]} and FY{years[1]}."
                else:
                    # Default trend response
                    answer = answer_with_citations(
                        payload.question,
                        evidence,
                        filters={"question_type": "trend_analysis"}
                    )
                
                return {
                    "answer": answer,
                    "evidence": evidence,
                    "trend_data": trend_data,
                    "question_type": question_type
                }
        
        elif question_type == "breakdowns_shares":
            breakdown_data = get_breakdown_analysis(payload.question)
            if breakdown_data:
                evidence = breakdown_data.get("evidence", [])
                
                # Create specific responses for different breakdown questions
                if "percentage" in payload.question.lower():
                    # Find the specific department mentioned in the question
                    filters = parse_filters(payload.question)
                    target_dept = filters.get("department")
                    
                    if target_dept:
                        # Find the percentage for the target department
                        departments = breakdown_data.get("departments", [])
                        for dept in departments:
                            if dept.get("department") == target_dept:
                                percentage = dept.get("percentage", 0)
                                answer = f"{percentage:.1f}% of the FY{breakdown_data.get('fiscal_year')} budget came from {target_dept.replace('_', ' ').title()}."
                                break
                        else:
                            answer = f"I couldn't find {target_dept.replace('_', ' ').title()} in the FY{breakdown_data.get('fiscal_year')} budget data."
                    else:
                        answer = "I couldn't identify which department you're asking about for the percentage calculation."
                elif "top 5" in payload.question.lower():
                    # Handle top 5 questions
                    departments = breakdown_data.get("departments", [])[:5]
                    fiscal_year = breakdown_data.get("fiscal_year")
                    
                    if departments:
                        answer = f"The top 5 categories by amount in FY{fiscal_year} are: "
                        dept_list = []
                        for i, dept in enumerate(departments):
                            dept_name = dept["department"].replace("_", " ").title()
                            amount = dept["total_amount"]
                            dept_list.append(f"{dept_name} (${amount:,.2f})")
                        answer += ", ".join(dept_list) + "."
                    else:
                        answer = f"I couldn't find budget data for FY{fiscal_year}."
                elif "share" in payload.question.lower():
                    # Handle share questions (like "what share of Administration went to Health Insurance")
                    filters = parse_filters(payload.question)
                    target_dept = filters.get("department")
                    
                    if target_dept:
                        # This would need more complex logic to find line items within a department
                        answer = f"I can see {target_dept.replace('_', ' ').title()} budget data, but I need more specific information about the line item you're asking about."
                    else:
                        answer = "I couldn't identify which department you're asking about for the share calculation."
                else:
                    # Default breakdown response
                    answer = answer_with_citations(
                        payload.question,
                        evidence,
                        total=breakdown_data.get("total_budget"),
                        filters={"question_type": "breakdown_analysis"}
                    )
                
                return {
                    "answer": answer,
                    "evidence": evidence,
                    "breakdown_data": breakdown_data,
                    "question_type": question_type
                }
        
        # Try to get direct answer for amount questions
        direct_answer = get_aggregated_answer(payload.question)
        
        if direct_answer and direct_answer.get("total") is not None:
            # Return direct answer with total
            evidence = direct_answer.get("evidence", [])
            answer = answer_with_citations(
                payload.question, 
                evidence, 
                total=direct_answer.get("total"),
                filters=direct_answer.get("filters")
            )
            return {
                "answer": answer,
                "evidence": evidence,
                "filters": direct_answer.get("filters"),
                "total": direct_answer.get("total"),
                "question_type": question_type
            }
        
        # Fallback to regular retrieval
        ev = retrieve(payload.question, k=5)
        evidence = [dict(r) for r in ev]
        answer = answer_with_citations(payload.question, evidence)
        return {
            "answer": answer, 
            "evidence": evidence,
            "question_type": question_type
        }
    
    except Exception as e:
        # shows full error in server logs, returns a 500 with message
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/insights")
def get_insights(payload: Ask):
    """
    Get detailed insights for a question (expandable view).
    """
    try:
        # Classify the question type
        question_type = classify_question(payload.question)
        
        # Get the same data as the main endpoint but generate detailed insights
        # Try to get direct answer first for amount questions
        direct_answer = get_aggregated_answer(payload.question)
        
        if direct_answer and direct_answer.get("total") is not None:
            evidence = direct_answer.get("evidence", [])
            detailed_insights = generate_detailed_insights(
                payload.question,
                evidence,
                total=direct_answer.get("total"),
                filters=direct_answer.get("filters"),
                question_type=question_type
            )
            return {
                "insights": detailed_insights,
                "evidence": evidence,
                "filters": direct_answer.get("filters"),
                "total": direct_answer.get("total"),
                "question_type": question_type
            }
        
        # Fallback to regular retrieval
        ev = retrieve(payload.question, k=5)
        evidence = [dict(r) for r in ev]
        detailed_insights = generate_detailed_insights(
            payload.question,
            evidence,
            question_type=question_type
        )
        return {
            "insights": detailed_insights,
            "evidence": evidence,
            "question_type": question_type
        }
    
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summaries", response_model=SummaryResponse)
def get_summary(
    year: Optional[int] = Query(None, description="Fiscal year"),
    department: Optional[str] = Query(None, description="Department name")
):
    """Get budget summary for a specific department and year."""
    try:
        where_conditions = []
        params = {}
        
        if year:
            where_conditions.append("fiscal_year = :year")
            params["year"] = year
        
        if department:
            where_conditions.append("department = :department")
            params["department"] = department
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        with engine.begin() as conn:
            result = conn.execute(text(f"""
                SELECT text, generated_at
                FROM summaries
                {where_clause}
                ORDER BY generated_at DESC
                LIMIT 1
            """), params).mappings().first()
            
            if not result:
                raise HTTPException(status_code=404, detail="Summary not found")
            
            return SummaryResponse(
                text=result["text"],
                generated_at=result["generated_at"].isoformat()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/findings", response_model=List[FindingResponse])
def get_findings(
    year: Optional[int] = Query(None, description="Fiscal year to filter by"),
    severity: Optional[str] = Query(None, description="Severity level (low, medium, high)")
):
    """Get validation findings, optionally filtered by year and severity."""
    try:
        where_conditions = []
        params = {}
        
        if year:
            where_conditions.append("""
                EXISTS (
                    SELECT 1 FROM documents d 
                    WHERE d.id = vf.document_id AND d.fiscal_year = :year
                )
            """)
            params["year"] = year
        
        if severity:
            where_conditions.append("severity = :severity")
            params["severity"] = severity
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        with engine.begin() as conn:
            results = conn.execute(text(f"""
                SELECT id, document_id, rule, severity, note, created_at
                FROM validation_findings vf
                {where_clause}
                ORDER BY created_at DESC
            """), params).mappings().all()
            
            return [FindingResponse(**dict(row)) for row in results]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/departments")
def get_departments():
    """Get list of all departments with budget data."""
    try:
        with engine.begin() as conn:
            results = conn.execute(text("""
                SELECT DISTINCT department
                FROM budget_facts
                WHERE department IS NOT NULL
                ORDER BY department
            """)).mappings().all()
            
            return [row["department"] for row in results]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/years")
def get_years():
    """Get list of all fiscal years with budget data."""
    try:
        with engine.begin() as conn:
            results = conn.execute(text("""
                SELECT DISTINCT fiscal_year
                FROM budget_facts
                WHERE fiscal_year IS NOT NULL
                ORDER BY fiscal_year DESC
            """)).mappings().all()
            
            return [row["fiscal_year"] for row in results]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats():
    """Get basic statistics about the budget data."""
    try:
        with engine.begin() as conn:
            stats = conn.execute(text("""
                SELECT 
                    COUNT(DISTINCT d.id) as total_documents,
                    COUNT(DISTINCT bf.department) as total_departments,
                    COUNT(DISTINCT bf.fiscal_year) as total_years,
                    COUNT(bf.id) as total_budget_facts,
                    SUM(bf.amount) as total_budget_amount
                FROM documents d
                LEFT JOIN budget_facts bf ON d.id = bf.document_id
            """)).mappings().first()
            
            return dict(stats)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/budget-facts")
def get_budget_facts():
    """Get all budget facts for the frontend dashboard."""
    try:
        with engine.begin() as conn:
            results = conn.execute(text("""
                SELECT 
                    bf.id,
                    bf.fiscal_year,
                    bf.department,
                    bf.line_item,
                    bf.amount
                FROM budget_facts bf
                ORDER BY bf.fiscal_year, bf.department, bf.amount DESC
            """)).mappings().all()
            
            return [dict(row) for row in results]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New Budget API Endpoints using Supabase Views
@app.get("/api/budget/year-totals")
async def get_year_totals():
    """Get total budget amounts for all fiscal years"""
    try:
        with engine.begin() as conn:
            result = conn.execute(text("SELECT fiscal_year, total FROM v_year_totals ORDER BY fiscal_year"))
            data = [dict(row) for row in result.mappings().all()]
        
        return {
            "success": True,
            "data": data,
            "message": "Year totals retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch year totals: {str(e)}")

@app.get("/api/budget/yoy")
async def get_yoy():
    """Get year-over-year budget changes"""
    try:
        with engine.begin() as conn:
            result = conn.execute(text("SELECT fiscal_year, total, yoy_change FROM v_year_yoy ORDER BY fiscal_year"))
            data = [dict(row) for row in result.mappings().all()]
        
        return {
            "success": True,
            "data": data,
            "message": "Year-over-year data retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch YoY data: {str(e)}")

@app.get("/api/budget/category")
async def get_category_ranking(year: str = "FY25", limit: int = 10):
    """Get category rankings for a specific year"""
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT category, total 
                FROM v_category_totals 
                WHERE fiscal_year = :year 
                ORDER BY total DESC 
                LIMIT :limit
            """), {"year": year, "limit": limit})
            data = [dict(row) for row in result.mappings().all()]
        
        return {
            "success": True,
            "year": year,
            "partial": year == "FY26",
            "data": data,
            "message": f"Category rankings for {year} retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch category rankings: {str(e)}")

@app.get("/api/budget/shares")
async def get_category_shares(year: str = "FY25"):
    """Get category shares (percentages) for a specific year"""
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT category, total, pct_of_year 
                FROM v_category_shares 
                WHERE fiscal_year = :year 
                ORDER BY total DESC
            """), {"year": year})
            data = [dict(row) for row in result.mappings().all()]
        
        return {
            "success": True,
            "year": year,
            "partial": year == "FY26",
            "data": data,
            "message": f"Category shares for {year} retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch category shares: {str(e)}")

@app.get("/api/budget/line-item")
async def get_line_item_total(year: str = "FY24", category: str = "ADMINISTRATION", line_item: str = "Payroll Taxes"):
    """Get total for a specific line item"""
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT total 
                FROM v_line_items 
                WHERE fiscal_year = :year 
                AND category = :category 
                AND line_item = :line_item
            """), {"year": year, "category": category, "line_item": line_item})
            row = result.fetchone()
            total = row[0] if row else 0
        
        # Debug logging as suggested by ChatGPT
        print(f"DEBUG line-item API: year={year}, category={category}, line_item={line_item}, total={total}")
        
        return {
            "success": True,
            "year": year,
            "category": category,
            "lineItem": line_item,
            "total": total,
            "formatted": f"${total:,}" if total else "$0",
            "partial": year == "FY26",
            "message": f"Line item total for {line_item} in {category} ({year}) retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch line item total: {str(e)}")

@app.get("/api/budget/category-yoy")
async def get_category_yoy(year1: str = "FY24", year2: str = "FY25", category: str = ""):
    """Get year-over-year change for a specific category"""
    try:
        if not category:
            raise HTTPException(status_code=400, detail="Category parameter is required")
        
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT fiscal_year, category, total, prev_total, change_amount, change_percentage
                FROM v_category_yoy 
                WHERE fiscal_year = :year2 AND category = :category
            """), {"year2": year2, "category": category})
            row = result.fetchone()
            
            if not row:
                return {
                    "success": True,
                    "year1": year1,
                    "year2": year2,
                    "category": category,
                    "data": None,
                    "message": f"No data found for {category} in {year2}"
                }
            
            data = dict(row)
        
        return {
            "success": True,
            "year1": year1,
            "year2": year2,
            "category": category,
            "data": data,
            "message": f"Category YoY change for {category} from {year1} to {year2} retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch category YoY: {str(e)}")

# Mount static files
if os.path.exists("public"):
    app.mount("/", StaticFiles(directory="public", html=True), name="static")

