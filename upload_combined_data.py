#!/usr/bin/env python3
"""
Upload combined budget data (FY24-FY26) to new Supabase database
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import re

load_dotenv()

def extract_fiscal_year(fiscal_year_str):
    """Extract year number from FY24, FY25, FY26 format"""
    match = re.search(r'FY(\d{2})', fiscal_year_str)
    if match:
        year = int(match.group(1))
        return 2000 + year if year < 50 else 1900 + year
    return None

def upload_combined_data():
    """Upload the combined CSV data to Supabase"""
    
    # Get database URL from environment
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL environment variable not set.")
        print("Please add your Supabase connection string to .env file:")
        print("DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres")
        return False
    
    # Path to the combined CSV
    csv_path = "/Users/shishirporeddy/ECON432/Resume/LandoverHills_One_Budget_FY24_FY26.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: CSV file not found at {csv_path}")
        return False
    
    try:
        # Create database connection
        engine = create_engine(DATABASE_URL)
        
        # Read the CSV
        print("📊 Reading combined budget data...")
        df = pd.read_csv(csv_path)
        
        # Clean and transform the data
        print("🔄 Processing data...")
        
        # Extract fiscal year as integer
        df['fiscal_year'] = df['Fiscal Year'].apply(extract_fiscal_year)
        
        # Rename columns to match database schema
        df = df.rename(columns={
            'Category': 'department',
            'Line Item': 'line_item',
            'Amount': 'amount'
        })
        
        # Ensure amount is numeric
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        
        # Select and reorder columns
        df = df[['fiscal_year', 'department', 'line_item', 'amount']]
        
        # Remove any rows with missing fiscal year
        df = df.dropna(subset=['fiscal_year'])
        
        print(f"📈 Data summary:")
        print(f"   Total records: {len(df)}")
        print(f"   Fiscal years: {sorted(df['fiscal_year'].unique())}")
        print(f"   Departments: {len(df['department'].unique())}")
        print(f"   Total budget: ${df['amount'].sum():,.2f}")
        
        # Connect to database and upload
        with engine.connect() as connection:
            print("🗄️  Connecting to Supabase database...")
            
            # Clear existing data
            print("🧹 Clearing existing budget data...")
            connection.execute(text("DELETE FROM budget_facts"))
            connection.commit()
            
            # Insert new data
            print("📤 Uploading data to budget_facts table...")
            df.to_sql('budget_facts', con=connection, if_exists='append', index=False)
            connection.commit()
            
            # Verify upload
            result = connection.execute(text("SELECT COUNT(*) as count FROM budget_facts"))
            count = result.fetchone()[0]
            
            print(f"✅ Successfully uploaded {count} records to Supabase!")
            
            # Show breakdown by fiscal year
            result = connection.execute(text("""
                SELECT fiscal_year, COUNT(*) as records, SUM(amount) as total
                FROM budget_facts 
                GROUP BY fiscal_year 
                ORDER BY fiscal_year
            """))
            
            print("\n📊 Data breakdown by fiscal year:")
            for row in result:
                print(f"   FY{row[0]}: {row[1]} records, ${row[2]:,.2f}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error uploading data: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting combined budget data upload to Supabase...")
    success = upload_combined_data()
    
    if success:
        print("\n🎉 Upload completed successfully!")
        print("You can now start the server with: python demo_simple.py")
    else:
        print("\n💥 Upload failed. Please check the error messages above.")

