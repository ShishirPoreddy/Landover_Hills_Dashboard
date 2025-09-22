# app/llm.py
import os, re
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBED_MODEL = "text-embedding-3-small"   # 1536-dim (matches your VECTOR(1536))
CHAT_MODEL  = "gpt-4o-mini"              # cheap/fast; change if you prefer

# --- Embeddings ---
def embed_texts(texts: List[str]) -> List[list]:
    """
    Returns a 1536-dim vector per input text using OpenAI.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing in environment")
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

# --- Simple amount extractor (used in fallback + display) ---
_AMT_RE = re.compile(r'Amount:\s*\$?([0-9,]+(?:\.[0-9]{1,2})?)', re.I)
def _maybe_amount(text: str):
    m = _AMT_RE.search(text or "")
    return m.group(1) if m else None

# --- Question Classification Framework ---
def classify_question(question: str) -> str:
    """
    Classify the question type based on the ai_assistant_budget_questions.json framework.
    
    Args:
        question: User's question
        
    Returns:
        Question type category
    """
    question_lower = question.lower()
    
    # Totals and Aggregates
    if any(keyword in question_lower for keyword in ['total budget', 'total', 'sum', 'aggregate', 'combined']):
        return "totals_and_aggregates"
    
    # Category Comparisons
    if any(keyword in question_lower for keyword in ['compare', 'which category', 'rank', 'most funding', 'highest', 'lowest']):
        return "category_comparisons"
    
    # Line-Item Details
    if any(keyword in question_lower for keyword in ['line item', 'allocated to', 'largest line item', 'show me all line items']):
        return "line_item_details"
    
    # Over Time / Trend Analysis
    if any(keyword in question_lower for keyword in ['change from', 'grew the most', 'decreased from', 'trend', 'over time']):
        return "trend_analysis"
    
    # Cross-Year Comparisons
    if any(keyword in question_lower for keyword in ['increased in', 'year-over-year', 'disappear', 'compared to']):
        return "cross_year_comparisons"
    
    # Breakdowns & Shares
    if any(keyword in question_lower for keyword in ['percentage', 'share', 'top 5', 'breakdown']):
        return "breakdowns_shares"
    
    # Partial FY26 Data Handling
    if any(keyword in question_lower for keyword in ['fy26', '2026', 'partial', 'currently available']):
        return "partial_fy26_data"
    
    # Custom Filters
    if any(keyword in question_lower for keyword in ['over $', 'more than', 'under $', 'list categories', 'show me all expenditures']):
        return "custom_filters"
    
    # Natural-Language Trends
    if any(keyword in question_lower for keyword in ['biggest drivers', 'summarize', 'plain english', 'why does', 'tell me']):
        return "natural_language_trends"
    
    # What-If / Hypothetical
    if any(keyword in question_lower for keyword in ['if', 'would', 'hypothetical', 'what if']):
        return "what_if_hypothetical"
    
    return "general"

def get_enhanced_system_prompt(question_type: str, total: Optional[float] = None, concise: bool = True) -> str:
    """
    Get enhanced system prompt based on question type and framework.
    
    Args:
        question_type: Classified question type
        total: Optional total amount for amount questions
        concise: If True, provide concise single-sentence responses
        
    Returns:
        Enhanced system prompt
    """
    base_prompt = "You are an expert municipal budget analyst assistant. You answer questions about municipal budgets with precision and clarity."
    
    if concise:
        # Concise response instructions
        base_prompt += " Provide a single, clear sentence that directly answers the question. "
        
        if total is not None:
            base_prompt += f"The total amount is ${total:,.2f}. "
        
        type_prompts = {
            "totals_and_aggregates": "Start with the exact total and briefly explain what it represents.",
            "category_comparisons": "State which category received the most funding and the amount.",
            "line_item_details": "Provide the specific amount or identify the largest line item.",
            "trend_analysis": "State the key change and the percentage or amount difference.",
            "cross_year_comparisons": "Summarize the main year-over-year change in one sentence.",
            "breakdowns_shares": "State the percentage and what it represents.",
            "partial_fy26_data": "Note that this is partial data and provide the available total.",
            "custom_filters": "State how many items meet the criteria and the total amount.",
            "natural_language_trends": "Provide a clear, one-sentence summary of the key insight.",
            "what_if_hypothetical": "State the calculated result based on the hypothetical scenario."
        }
        
        return base_prompt + type_prompts.get(question_type, "Provide a direct answer.")
    
    else:
        # Detailed response instructions for insights
        type_prompts = {
            "totals_and_aggregates": (
                "Provide detailed breakdown of the total, including major components, "
                "percentages, and context. Always cite evidence IDs like [1], [2]."
            ),
            "category_comparisons": (
                "Provide detailed comparisons between categories, departments, or line items. Include rankings, percentages, "
                "and clear explanations of differences. Use evidence to support your comparisons."
            ),
            "line_item_details": (
                "Focus on specific line items and their details. Provide exact amounts, show the largest items when requested, "
                "and give comprehensive lists when asked for 'all line items'."
            ),
            "trend_analysis": (
                "Analyze changes over time, growth patterns, and trends. Explain what drove increases or decreases, "
                "and provide context for the changes you observe."
            ),
            "cross_year_comparisons": (
                "Compare data across different fiscal years. Highlight increases, decreases, and new or discontinued categories. "
                "Provide year-over-year change percentages when relevant."
            ),
            "breakdowns_shares": (
                "Calculate and explain percentages, shares, and breakdowns. Provide clear rankings (top 5, etc.) and "
                "explain what each percentage represents in the overall budget context."
            ),
            "partial_fy26_data": (
                "Handle FY26 data carefully since it may be incomplete. Clearly state what data is available, "
                "what the partial totals represent, and note any limitations due to incomplete data."
            ),
            "custom_filters": (
                "Apply specific filters as requested (amount thresholds, item counts, etc.). Provide filtered lists "
                "that meet the exact criteria specified in the question."
            ),
            "natural_language_trends": (
                "Explain budget data in plain, understandable language. Summarize key insights, explain why certain "
                "patterns exist, and provide context that helps users understand the budget structure."
            ),
            "what_if_hypothetical": (
                "Handle hypothetical scenarios carefully. Make calculations based on the specified changes, "
                "but clearly note that these are hypothetical projections based on current data."
            )
        }
        
        if total is not None:
            return f"{base_prompt} {type_prompts.get(question_type, '')} When a total amount is provided (${total:,.2f}), incorporate it into your analysis."
        else:
            return f"{base_prompt} {type_prompts.get(question_type, '')}"

# --- Compose a final answer with the evidence (LLM, with fallback) ---
def answer_with_citations(question: str, evidence: List[Dict], total: Optional[float] = None, 
                         filters: Optional[Dict] = None) -> str:
    """
    Generate answer with citations, including direct totals when available.
    
    Args:
        question: User's question
        evidence: List of evidence dictionaries
        total: Optional total amount for amount questions
        filters: Optional filters applied to get the total
        
    Returns:
        Formatted answer with citations
    """
    try:
        # Classify the question type
        question_type = classify_question(question)
        
        # Build context from evidence
        context = "\n\n".join(
            f"[{i+1}] FY {e.get('fiscal_year','—')} • {e.get('department','—')}\n{e.get('chunk_text','')}"
            for i, e in enumerate(evidence[:6])
        ) or "No evidence."
        
        # Get enhanced system prompt based on question type (concise by default)
        sys = get_enhanced_system_prompt(question_type, total, concise=True)
        
        # Build user prompt with additional context
        user_parts = [f"Question: {question}"]
        
        if total is not None:
            user_parts.append(f"Total: ${total:,.2f}")
        
        if filters:
            user_parts.append(f"Filters Applied: {filters}")
        
        user_parts.append(f"Evidence:\n{context}")
        
        user = "\n\n".join(user_parts)
        
        chat = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role":"system","content":sys},{"role":"user","content":user}],
            temperature=0.2
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        # Enhanced fallback: natural full sentences
        if total is not None:
            # Create natural sentence based on question type and filters
            if filters:
                filter_parts = []
                if filters.get("fiscal_year"):
                    filter_parts.append(f"FY{filters['fiscal_year']}")
                if filters.get("department"):
                    filter_parts.append(filters["department"].replace("_", " ").title())
                if filters.get("line_item"):
                    filter_parts.append(filters["line_item"])
                
                if len(filter_parts) == 1:
                    answer = f"The total budget for {filter_parts[0]} is ${total:,.2f}."
                elif len(filter_parts) == 2:
                    answer = f"The total budget for {filter_parts[1]} in {filter_parts[0]} is ${total:,.2f}."
                else:
                    answer = f"The total budget is ${total:,.2f}."
            else:
                answer = f"The total budget is ${total:,.2f}."
        else:
            # Handle non-total questions
            if evidence:
                answer = f"Based on the available data, here are the relevant findings for your question."
            else:
                answer = f"I couldn't find specific data matching your question."
        
        return answer

def generate_detailed_insights(question: str, evidence: List[Dict], total: Optional[float] = None, 
                             filters: Optional[Dict] = None, question_type: str = "general") -> str:
    """
    Generate detailed insights for expandable view.
    
    Args:
        question: User's question
        evidence: List of evidence dictionaries
        total: Optional total amount for amount questions
        filters: Optional filters applied to get the total
        question_type: Classified question type
        
    Returns:
        Detailed insights with citations
    """
    try:
        # Build context from evidence
        context = "\n\n".join(
            f"[{i+1}] FY {e.get('fiscal_year','—')} • {e.get('department','—')}\n{e.get('chunk_text','')}"
            for i, e in enumerate(evidence[:6])
        ) or "No evidence."
        
        # Get detailed system prompt
        sys = get_enhanced_system_prompt(question_type, total, concise=False)
        
        # Build user prompt with additional context
        user_parts = [f"Question: {question}"]
        
        if total is not None:
            user_parts.append(f"Total: ${total:,.2f}")
        
        if filters:
            user_parts.append(f"Filters Applied: {filters}")
        
        user_parts.append(f"Evidence:\n{context}")
        
        user = "\n\n".join(user_parts)
        
        chat = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role":"system","content":sys},{"role":"user","content":user}],
            temperature=0.2
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        # Enhanced fallback: natural detailed response
        if total is not None:
            answer = f"**Detailed Analysis**\n\n"
            
            if filters:
                filter_parts = []
                if filters.get("fiscal_year"):
                    filter_parts.append(f"FY{filters['fiscal_year']}")
                if filters.get("department"):
                    filter_parts.append(filters["department"].replace("_", " ").title())
                if filters.get("line_item"):
                    filter_parts.append(filters["line_item"])
                
                if len(filter_parts) == 1:
                    answer += f"The total budget for {filter_parts[0]} is **${total:,.2f}**.\n\n"
                elif len(filter_parts) == 2:
                    answer += f"The total budget for {filter_parts[1]} in {filter_parts[0]} is **${total:,.2f}**.\n\n"
                else:
                    answer += f"The total budget is **${total:,.2f}**.\n\n"
            else:
                answer += f"The total budget is **${total:,.2f}**.\n\n"
            
            # Add context about the data
            if evidence:
                answer += f"This total is based on {len(evidence)} budget line items. "
                answer += "The data includes various categories such as salaries, equipment, and operational expenses.\n\n"
                
                # Show top categories
                dept_counts = {}
                for evi in evidence:
                    dept = evi.get("department", "Unknown")
                    dept_counts[dept] = dept_counts.get(dept, 0) + 1
                
                if dept_counts:
                    answer += "**Breakdown by Department:**\n"
                    for dept, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                        answer += f"- {dept.replace('_', ' ').title()}: {count} line items\n"
        else:
            answer = f"**Detailed Analysis**\n\n"
            if evidence:
                answer += f"Based on the available data, I found {len(evidence)} relevant budget items. "
                answer += "Here's what the data shows:\n\n"
                
                # Group by department
                dept_data = {}
                for evi in evidence:
                    dept = evi.get("department", "Unknown")
                    if dept not in dept_data:
                        dept_data[dept] = []
                    dept_data[dept].append(evi)
                
                for dept, items in list(dept_data.items())[:3]:
                    answer += f"**{dept.replace('_', ' ').title()}**: {len(items)} budget items\n"
            else:
                answer += "I couldn't find specific data matching your question in the budget records."
        
        return answer
