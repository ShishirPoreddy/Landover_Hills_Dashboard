# app/db.py
import os
from sqlalchemy import create_engine, event
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Register pgvector for psycopg2 so lists/tuples map to 'vector'
@event.listens_for(engine, "connect")
def register_vector(dbapi_conn, conn_record):
    try:
        from pgvector.psycopg2 import register_vector
        register_vector(dbapi_conn)
    except Exception as e:
        # Don't crash app if adapter missing; just log
        print("pgvector register warning:", e)

