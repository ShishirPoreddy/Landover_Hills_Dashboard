#!/usr/bin/env python3
"""
Upload all budget data (FY24, FY25, FY26) to Supabase
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_all_budget_data():
    """Upload all budget data to Supabase."""
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in .env file")
        return
    
    try:
        # Connect to Supabase
        print("Connecting to Supabase...")
        engine = create_engine(database_url)
        
        # Clear existing data
        with engine.connect() as conn:
            print("Clearing existing budget data...")
            conn.execute(text("DELETE FROM budget_facts"))
            conn.commit()
        
        all_data = []
        
        # Load FY24 data
        fy24_path = "/Users/shishirporeddy/ECON432/Resume/FY24_Cleaned_CSV - FY24 Amended Budget Ordinance.csv"
        if os.path.exists(fy24_path):
            print("Loading FY24 data...")
            df24 = pd.read_csv(fy24_path)
            for _, row in df24.iterrows():
                if pd.notna(row.get('Amount')) and row.get('Amount', 0) > 0:
                    all_data.append({
                        'fiscal_year': 2024,
                        'department': row.get('Category', 'Unknown'),
                        'line_item': row.get('Line_Item', 'Unknown'),
                        'amount': float(row.get('Amount', 0))
                    })
            print(f"Loaded {len([d for d in all_data if d['fiscal_year'] == 2024])} FY24 records")
        
        # Load FY25 data
        fy25_path = "/Users/shishirporeddy/ECON432/Resume/FY25_Cleaned_CSV - Sheet1.csv"
        if os.path.exists(fy25_path):
            print("Loading FY25 data...")
            df25 = pd.read_csv(fy25_path)
            for _, row in df25.iterrows():
                if pd.notna(row.get('Amount')) and row.get('Amount', 0) > 0:
                    all_data.append({
                        'fiscal_year': 2025,
                        'department': row.get('Category', 'Unknown'),
                        'line_item': row.get('Line_Item', 'Unknown'),
                        'amount': float(row.get('Amount', 0))
                    })
            print(f"Loaded {len([d for d in all_data if d['fiscal_year'] == 2025])} FY25 records")
        
        # Load FY26 data
        fy26_path = "/Users/shishirporeddy/ECON432/Resume/FY26_Budget.csv"
        if os.path.exists(fy26_path):
            print("Loading FY26 data...")
            df26 = pd.read_csv(fy26_path)
            for _, row in df26.iterrows():
                if pd.notna(row.get('FY26 Amount')) and row.get('FY26 Amount', 0) > 0:
                    all_data.append({
                        'fiscal_year': 2026,
                        'department': row.get('Category', 'Unknown'),
                        'line_item': row.get('Line Item', 'Unknown'),
                        'amount': float(row.get('FY26 Amount', 0))
                    })
            print(f"Loaded {len([d for d in all_data if d['fiscal_year'] == 2026])} FY26 records")
        
        print(f"Total records to upload: {len(all_data)}")
        
        # Upload all data
        with engine.connect() as conn:
            print("Uploading all budget data...")
            for record in all_data:
                conn.execute(text("""
                    INSERT INTO budget_facts (fiscal_year, department, line_item, amount)
                    VALUES (:fiscal_year, :department, :line_item, :amount)
                """), record)
            conn.commit()
        
        print(f"Successfully uploaded {len(all_data)} records to Supabase!")
        
        # Verify upload
        with engine.connect() as conn:
            result = conn.execute(text("SELECT fiscal_year, COUNT(*) FROM budget_facts GROUP BY fiscal_year ORDER BY fiscal_year"))
            print("\nVerification by fiscal year:")
            for row in result:
                print(f"  FY{row.fiscal_year}: {row.count} records")
            
            # Show total budget by year
            result = conn.execute(text("""
                SELECT fiscal_year, SUM(amount) as total_budget 
                FROM budget_facts 
                GROUP BY fiscal_year 
                ORDER BY fiscal_year
            """))
            print("\nTotal budget by year:")
            for row in result:
                print(f"  FY{row.fiscal_year}: ${row.total_budget:,.2f}")
        
    except Exception as e:
        print(f"Error uploading data: {e}")

if __name__ == "__main__":
    upload_all_budget_data()

