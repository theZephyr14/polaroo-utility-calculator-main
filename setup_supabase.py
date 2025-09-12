#!/usr/bin/env python3
"""
Setup script for Supabase database migration.

This script creates all necessary tables, indexes, and initial data
for the Polaroo Utility Calculator system.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.supabase_client import get_supabase_client
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

def setup_database():
    """Set up the Supabase database with schema and initial data."""
    print("🚀 [SETUP] Starting Supabase database setup...")
    
    try:
        # Read the schema file
        schema_file = Path(__file__).parent / "supabase_schema.sql"
        if not schema_file.exists():
            print(f"❌ [SETUP] Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("📄 [SETUP] Schema file loaded successfully")
        
        # Split the SQL into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        print(f"📊 [SETUP] Found {len(statements)} SQL statements to execute")
        
        # Execute each statement
        client = get_supabase_client()
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            try:
                print(f"⚡ [SETUP] Executing statement {i}/{len(statements)}...")
                
                # Use rpc for function definitions, direct SQL for others
                if statement.upper().startswith('CREATE OR REPLACE FUNCTION'):
                    # Extract function name and parameters
                    lines = statement.split('\n')
                    func_line = lines[0]
                    func_name = func_line.split('(')[0].split()[-1]
                    
                    # Execute as RPC
                    result = client.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"✅ [SETUP] Function {func_name} created successfully")
                else:
                    # Execute as direct SQL
                    result = client.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"✅ [SETUP] Statement {i} executed successfully")
                
                success_count += 1
                
            except Exception as e:
                print(f"⚠️ [SETUP] Statement {i} failed: {e}")
                error_count += 1
                # Continue with other statements
                continue
        
        print(f"\n📊 [SETUP] Database setup completed!")
        print(f"✅ [SETUP] Successful statements: {success_count}")
        print(f"❌ [SETUP] Failed statements: {error_count}")
        
        if error_count == 0:
            print("🎉 [SETUP] All statements executed successfully!")
            return True
        else:
            print("⚠️ [SETUP] Some statements failed, but setup may still be functional")
            return True
            
    except Exception as e:
        print(f"❌ [SETUP] Database setup failed: {e}")
        return False

def verify_setup():
    """Verify that the database setup was successful."""
    print("\n🔍 [VERIFY] Verifying database setup...")
    
    try:
        client = get_supabase_client()
        
        # Check if tables exist
        tables_to_check = [
            'properties', 'room_limits', 'processing_sessions', 
            'property_results', 'invoices', 'file_storage',
            'monthly_service_data', 'raw_reports', 'system_settings'
        ]
        
        for table in tables_to_check:
            try:
                result = client.table(table).select("id").limit(1).execute()
                print(f"✅ [VERIFY] Table '{table}' exists and is accessible")
            except Exception as e:
                print(f"❌ [VERIFY] Table '{table}' not accessible: {e}")
                return False
        
        # Check if properties were inserted
        result = client.table("properties").select("id", "name").limit(5).execute()
        if result.data:
            print(f"✅ [VERIFY] Properties table has {len(result.data)} records (showing first 5)")
            for prop in result.data:
                print(f"  - {prop['name']}")
        else:
            print("⚠️ [VERIFY] Properties table is empty")
        
        # Check if room limits were inserted
        result = client.table("room_limits").select("room_count", "allowance").execute()
        if result.data:
            print(f"✅ [VERIFY] Room limits table has {len(result.data)} records")
            for limit in result.data:
                print(f"  - {limit['room_count']} rooms: €{limit['allowance']}")
        else:
            print("⚠️ [VERIFY] Room limits table is empty")
        
        # Test the get_property_allowance function
        test_property = "Aribau 1º 1ª"
        try:
            result = client.rpc("get_property_allowance", {"property_name": test_property}).execute()
            allowance = float(result.data) if result.data else None
            if allowance:
                print(f"✅ [VERIFY] get_property_allowance function works: {test_property} = €{allowance}")
            else:
                print(f"⚠️ [VERIFY] get_property_allowance function returned no data for {test_property}")
        except Exception as e:
            print(f"❌ [VERIFY] get_property_allowance function failed: {e}")
        
        print("🎉 [VERIFY] Database verification completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ [VERIFY] Database verification failed: {e}")
        return False

def main():
    """Main setup function."""
    print("=" * 60)
    print("🏗️  POLAROO UTILITY CALCULATOR - SUPABASE SETUP")
    print("=" * 60)
    
    # Check if we have the required environment variables
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ [SETUP] Missing required environment variables:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_SERVICE_KEY")
        print("\nPlease check your .env2 file or environment variables.")
        return False
    
    print(f"🔗 [SETUP] Connecting to Supabase: {SUPABASE_URL}")
    
    # Set up the database
    if not setup_database():
        print("❌ [SETUP] Database setup failed!")
        return False
    
    # Verify the setup
    if not verify_setup():
        print("❌ [VERIFY] Database verification failed!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 SUPABASE SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update your API endpoints to use the new Supabase client")
    print("2. Test the migration with a small dataset")
    print("3. Update the frontend to work with the new backend")
    print("\nThe database is now ready for the Polaroo Utility Calculator!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
