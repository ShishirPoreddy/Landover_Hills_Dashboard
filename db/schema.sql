-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  source_url TEXT,
  file_name TEXT,
  fiscal_year INT,
  department TEXT,
  raw_text TEXT,
  processed_at TIMESTAMP DEFAULT NOW(),
  metadata_status TEXT DEFAULT 'pending',  -- 'pending', 'partial', 'complete'
  doc_type TEXT,  -- 'budget ordinance', 'minutes', 'report', etc.
  checksum TEXT  -- for idempotency
);

CREATE TABLE IF NOT EXISTS budget_facts (
  id SERIAL PRIMARY KEY,
  document_id INT REFERENCES documents(id),
  year INT,
  fiscal_year INT,  -- alias for year, for consistency
  department TEXT,
  line_item TEXT,
  amount NUMERIC
);

CREATE TABLE IF NOT EXISTS chunks (
  id SERIAL PRIMARY KEY,
  document_id INT REFERENCES documents(id),
  chunk_text TEXT,
  embedding VECTOR(1536)  -- size should match your embedding model
);

-- New tables for validation and summaries
CREATE TABLE IF NOT EXISTS validation_findings (
  id SERIAL PRIMARY KEY,
  document_id INT REFERENCES documents(id),
  rule TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
  note TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS summaries (
  id SERIAL PRIMARY KEY,
  department TEXT NOT NULL,
  fiscal_year INT NOT NULL,
  text TEXT NOT NULL,
  generated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(department, fiscal_year)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_fiscal_year ON documents(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department);
CREATE INDEX IF NOT EXISTS idx_budget_facts_fiscal_year ON budget_facts(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_budget_facts_department ON budget_facts(department);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_validation_findings_document ON validation_findings(document_id);
CREATE INDEX IF NOT EXISTS idx_summaries_dept_year ON summaries(department, fiscal_year);
