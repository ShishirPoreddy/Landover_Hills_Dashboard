from sqlalchemy import text, bindparam, Integer
import re
from .db import engine
from .llm import embed_texts
from .qa import get_direct_answer
from pgvector.sqlalchemy import Vector as VectorType  # <-- SQLAlchemy type

DEPT_HINTS = [
    "Public Works","Police","Parks","Finance","Administration","Fire",
    "Transportation","Roads","Streets","Water","Sewer","Sanitation","General Government"
]

def _extract_year(q: str):
    m = re.search(r'(?i)\bFY\s*([0-9]{2,4})\b', q)
    if m:
        y = m.group(1)
        return int("20"+y[-2:]) if len(y)==2 else int(y)
    m = re.search(r'\b(20[0-9]{2})\b', q)
    return int(m.group(1)) if m else None

def _extract_dept(q: str):
    for d in DEPT_HINTS:
        if re.search(rf'(?i)\b{re.escape(d)}\b', q):
            return d
    return None

def retrieve(question: str, k: int = 5):
    # 1) try vector similarity (NO ::vector cast here)
    try:
        qvec = embed_texts([question])[0]
        stmt = text("""
            SELECT
              c.id,
              c.chunk_text,
              d.id          AS document_id,
              d.file_name   AS file_name,
              d.fiscal_year AS fiscal_year,
              d.department  AS department
            FROM public.chunks c
            LEFT JOIN public.documents d ON d.id = c.document_id
            ORDER BY c.embedding <-> :q
            LIMIT :k
        """).bindparams(
            bindparam("q", type_=VectorType(1536)),
            bindparam("k", type_=Integer())
        )
        with engine.begin() as conn:
            rows = conn.execute(stmt, {"q": qvec, "k": int(k)}).mappings().all()
        if rows:
            return rows
    except Exception as e:
        print("Vector retrieve failed:", e)

    # 2) tokenized text fallback
    year = _extract_year(question)
    dept = _extract_dept(question)

    sql = """
      SELECT
        c.id, c.chunk_text,
        d.id AS document_id, d.file_name, d.fiscal_year, d.department
      FROM public.chunks c
      LEFT JOIN public.documents d ON d.id = c.document_id
      WHERE 1=1
    """
    params = {}
    if dept:
        sql += " AND c.chunk_text ILIKE :dept"; params["dept"] = f"%{dept}%"
    if year:
        sql += " AND c.chunk_text ILIKE :year"; params["year"] = f"%{year}%"
    if not dept and not year:
        import re as _re
        tokens = [t for t in _re.findall(r"\\w+", question) if len(t) > 3][:4]
        for i, tok in enumerate(tokens):
            sql += f" AND c.chunk_text ILIKE :tok{i}"
            params[f"tok{i}"] = f"%{tok}%"
    sql += " LIMIT :k"; params["k"] = int(k)

    with engine.begin() as conn:
        return conn.execute(text(sql), params).mappings().all()

def get_aggregated_answer(question: str):
    """
    Get aggregated answer for amount questions.
    This is an alias for get_direct_answer from qa.py for compatibility.
    """
    return get_direct_answer(question)

def get_comparison_data(question: str):
    """
    Get year-over-year comparison data for budget questions.
    """
    from .qa import parse_filters
    
    filters = parse_filters(question)
    if not filters.get("fiscal_year") or not filters.get("department"):
        return None
    
    fiscal_year = filters["fiscal_year"]
    department = filters["department"]
    
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
            "difference": current_total - prev_total,
            "change_pct": change_pct
        }
