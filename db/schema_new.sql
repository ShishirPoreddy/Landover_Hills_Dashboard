-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  source_url TEXT,
  file_name TEXT,
  fiscal_year INT,
  department TEXT,
  raw_text TEXT,
  processed_at TIMESTAMP DEFAULT NOW(),
  metadata_status TEXT DEFAULT 'pending',
  doc_type TEXT,
  checksum TEXT
);

-- Create budget_facts table (main data table)
CREATE TABLE IF NOT EXISTS budget_facts (
  id SERIAL PRIMARY KEY,
  document_id INT REFERENCES documents(id),
  fiscal_year INT NOT NULL,
  department TEXT NOT NULL,
  line_item TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create chunks table for RAG
CREATE TABLE IF NOT EXISTS chunks (
  id SERIAL PRIMARY KEY,
  document_id INT REFERENCES documents(id),
  chunk_text TEXT,
  embedding VECTOR(1536)
);

-- Create validation_findings table
CREATE TABLE IF NOT EXISTS validation_findings (
  id SERIAL PRIMARY KEY,
  document_id INT REFERENCES documents(id),
  rule TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
  note TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create summaries table
CREATE TABLE IF NOT EXISTS summaries (
  id SERIAL PRIMARY KEY,
  department TEXT NOT NULL,
  fiscal_year INT NOT NULL,
  text TEXT NOT NULL,
  generated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(department, fiscal_year)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_fiscal_year ON documents(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department);
CREATE INDEX IF NOT EXISTS idx_budget_facts_fiscal_year ON budget_facts(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_budget_facts_department ON budget_facts(department);
CREATE INDEX IF NOT EXISTS idx_budget_facts_line_item ON budget_facts(line_item);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_validation_findings_document ON validation_findings(document_id);
CREATE INDEX IF NOT EXISTS idx_summaries_dept_year ON summaries(department, fiscal_year);

-- Insert a document record for the combined CSV
INSERT INTO documents (file_name, fiscal_year, department, raw_text, metadata_status, doc_type, checksum)
VALUES ('LandoverHills_One_Budget_FY24_FY26.csv', 2024, 'ALL', 'Combined budget data for FY24-FY26', 'complete', 'budget_ordinance', 'combined_csv_v1')
ON CONFLICT DO NOTHING;

