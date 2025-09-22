#!/usr/bin/env python3
"""
Upload FY26 budget data to Supabase
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_fy26_data():
    """Upload FY26 data to Supabase."""
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in .env file")
        return
    
    try:
        # Connect to Supabase
        print("Connecting to Supabase...")
        engine = create_engine(database_url)
        
        # Read FY26 CSV data
        fy26_path = "/Users/shishirporeddy/ECON432/Resume/FY26_Budget.csv"
        if not os.path.exists(fy26_path):
            print(f"Error: FY26 CSV file not found at {fy26_path}")
            return
        
        print("Reading FY26 data...")
        df = pd.read_csv(fy26_path)
        
        # Clean and prepare data
        data_to_insert = []
        for _, row in df.iterrows():
            if pd.notna(row.get('FY26 Amount')) and row.get('FY26 Amount', 0) > 0:
                data_to_insert.append({
                    'fiscal_year': 2026,
                    'department': row.get('Category', 'Unknown'),
                    'line_item': row.get('Line Item', 'Unknown'),
                    'amount': float(row.get('FY26 Amount', 0))
                })
        
        print(f"Prepared {len(data_to_insert)} records for upload")
        
        # Clear existing FY26 data (optional)
        with engine.connect() as conn:
            print("Clearing existing FY26 data...")
            conn.execute(text("DELETE FROM budget_facts WHERE fiscal_year = 2026"))
            conn.commit()
        
        # Insert new data
        with engine.connect() as conn:
            print("Uploading FY26 data...")
            for record in data_to_insert:
                conn.execute(text("""
                    INSERT INTO budget_facts (fiscal_year, department, line_item, amount)
                    VALUES (:fiscal_year, :department, :line_item, :amount)
                """), record)
            conn.commit()
        
        print(f"Successfully uploaded {len(data_to_insert)} FY26 records to Supabase!")
        
        # Verify upload
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM budget_facts WHERE fiscal_year = 2026"))
            count = result.scalar()
            print(f"Verification: {count} FY26 records now in database")
            
            # Show sample data
            result = conn.execute(text("""
                SELECT department, line_item, amount 
                FROM budget_facts 
                WHERE fiscal_year = 2026 
                ORDER BY amount DESC 
                LIMIT 5
            """))
            print("\nTop 5 FY26 budget items:")
            for row in result:
                print(f"  {row.department}: {row.line_item} - ${row.amount:,.2f}")
        
    except Exception as e:
        print(f"Error uploading data: {e}")

if __name__ == "__main__":
    upload_fy26_data()

