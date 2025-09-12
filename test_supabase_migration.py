#!/usr/bin/env python3
"""
Test script for Supabase migration.

This script tests the complete migration to Supabase by:
1. Setting up the database
2. Testing all major functions
3. Verifying data integrity
4. Testing the new API endpoints
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.supabase_client import get_supabase_manager, Property, ProcessingSession, PropertyResult
from src.polaroo_scrape_supabase import process_property_invoices, process_multiple_properties
from src.load_supabase import create_processing_session, update_processing_session

async def test_database_connection():
    """Test database connection and basic operations."""
    print("🔍 [TEST] Testing database connection...")
    
    try:
        manager = get_supabase_manager()
        
        # Test basic connection
        properties = manager.get_all_properties()
        print(f"✅ [TEST] Database connected, found {len(properties)} properties")
        
        # Test property allowance function
        test_property = "Aribau 1º 1ª"
        allowance = manager.get_property_allowance(test_property)
        print(f"✅ [TEST] Property allowance for {test_property}: €{allowance}")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Database connection failed: {e}")
        return False

async def test_property_operations():
    """Test property-related operations."""
    print("\n🔍 [TEST] Testing property operations...")
    
    try:
        manager = get_supabase_manager()
        
        # Get all properties
        properties = manager.get_all_properties()
        print(f"✅ [TEST] Retrieved {len(properties)} properties")
        
        # Test specific property
        test_property = manager.get_property_by_name("Aribau 1º 1ª")
        if test_property:
            print(f"✅ [TEST] Found property: {test_property.name} ({test_property.room_count} rooms)")
        else:
            print("❌ [TEST] Property not found")
            return False
        
        # Test allowance calculation
        allowance = manager.get_property_allowance("Aribau 1º 1ª")
        print(f"✅ [TEST] Allowance calculation: €{allowance}")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Property operations failed: {e}")
        return False

async def test_processing_session():
    """Test processing session operations."""
    print("\n🔍 [TEST] Testing processing session operations...")
    
    try:
        manager = get_supabase_manager()
        
        # Create a test session
        session = ProcessingSession(
            session_name="Test Migration Session",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 6, 30),
            status="processing"
        )
        
        session_id = manager.create_processing_session(session)
        if not session_id:
            print("❌ [TEST] Failed to create processing session")
            return False
        
        print(f"✅ [TEST] Created processing session: {session_id}")
        
        # Update session
        updates = {
            "status": "completed",
            "total_properties": 1,
            "successful_properties": 1,
            "failed_properties": 0,
            "total_cost": 100.0,
            "total_overuse": 50.0
        }
        
        success = manager.update_processing_session(session_id, updates)
        if not success:
            print("❌ [TEST] Failed to update processing session")
            return False
        
        print("✅ [TEST] Updated processing session")
        
        # Retrieve session
        retrieved_session = manager.get_processing_session(session_id)
        if not retrieved_session:
            print("❌ [TEST] Failed to retrieve processing session")
            return False
        
        print(f"✅ [TEST] Retrieved session: {retrieved_session.session_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Processing session operations failed: {e}")
        return False

async def test_file_storage():
    """Test file storage operations."""
    print("\n🔍 [TEST] Testing file storage operations...")
    
    try:
        manager = get_supabase_manager()
        
        # Test file upload
        test_content = b"Test PDF content for migration testing"
        test_property = "Aribau 1º 1ª"
        test_invoice = "TEST_001"
        
        file_path = manager.upload_file(
            file_bytes=test_content,
            property_name=test_property,
            invoice_number=test_invoice,
            file_name="test_migration.pdf"
        )
        
        if not file_path:
            print("❌ [TEST] Failed to upload test file")
            return False
        
        print(f"✅ [TEST] Uploaded test file: {file_path}")
        
        # Test file download
        downloaded_content = manager.download_file(file_path)
        if not downloaded_content:
            print("❌ [TEST] Failed to download test file")
            return False
        
        if downloaded_content == test_content:
            print("✅ [TEST] File download successful, content matches")
        else:
            print("❌ [TEST] Downloaded content doesn't match original")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] File storage operations failed: {e}")
        return False

async def test_invoice_processing():
    """Test invoice processing (without browser)."""
    print("\n🔍 [TEST] Testing invoice processing...")
    
    try:
        # Test with a mock property (this won't actually scrape, just test the data flow)
        manager = get_supabase_manager()
        
        # Create a test property result
        property_result = PropertyResult(
            property_name="Test Property",
            room_count=1,
            allowance=50.0,
            processing_status="processing"
        )
        
        property_result_id = manager.create_property_result(property_result)
        if not property_result_id:
            print("❌ [TEST] Failed to create property result")
            return False
        
        print(f"✅ [TEST] Created property result: {property_result_id}")
        
        # Create test invoices
        from src.supabase_client import Invoice
        
        test_invoices = [
            Invoice(
                property_result_id=property_result_id,
                invoice_number="TEST_001",
                service_type="electricity",
                amount=25.50,
                is_selected=True
            ),
            Invoice(
                property_result_id=property_result_id,
                invoice_number="TEST_002",
                service_type="water",
                amount=15.75,
                is_selected=True
            )
        ]
        
        invoice_ids = manager.create_invoices_batch(test_invoices)
        if not invoice_ids:
            print("❌ [TEST] Failed to create test invoices")
            return False
        
        print(f"✅ [TEST] Created {len(invoice_ids)} test invoices")
        
        # Retrieve invoices
        retrieved_invoices = manager.get_invoices_by_property_result(property_result_id)
        if len(retrieved_invoices) != 2:
            print(f"❌ [TEST] Expected 2 invoices, got {len(retrieved_invoices)}")
            return False
        
        print("✅ [TEST] Retrieved invoices successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Invoice processing failed: {e}")
        return False

async def test_api_compatibility():
    """Test API compatibility."""
    print("\n🔍 [TEST] Testing API compatibility...")
    
    try:
        # Test legacy functions
        from src.load_supabase import upload_raw, upsert_monthly
        
        # Test raw upload
        test_data = b"Test raw report data"
        file_path = upload_raw(date.today(), test_data, "test_report.csv")
        if file_path:
            print("✅ [TEST] Legacy upload_raw function works")
        else:
            print("❌ [TEST] Legacy upload_raw function failed")
            return False
        
        # Test monthly upsert
        test_monthly_data = [
            {
                "Property": "Test Property",
                "Electricity Cost": 25.50,
                "Water Cost": 15.75,
                "Total Cost": 41.25,
                "Allowance": 50.0,
                "Total Extra": 0.0
            }
        ]
        
        upsert_monthly(test_monthly_data)
        print("✅ [TEST] Legacy upsert_monthly function works")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] API compatibility failed: {e}")
        return False

async def test_system_settings():
    """Test system settings operations."""
    print("\n🔍 [TEST] Testing system settings...")
    
    try:
        manager = get_supabase_manager()
        
        # Test setting a value
        success = manager.set_system_setting(
            "test_setting", 
            "test_value", 
            "Test setting for migration"
        )
        if not success:
            print("❌ [TEST] Failed to set system setting")
            return False
        
        # Test getting a value
        value = manager.get_system_setting("test_setting")
        if value != "test_value":
            print(f"❌ [TEST] Expected 'test_value', got '{value}'")
            return False
        
        print("✅ [TEST] System settings operations work")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] System settings failed: {e}")
        return False

async def run_all_tests():
    """Run all migration tests."""
    print("=" * 60)
    print("🧪 SUPABASE MIGRATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Property Operations", test_property_operations),
        ("Processing Session", test_processing_session),
        ("File Storage", test_file_storage),
        ("Invoice Processing", test_invoice_processing),
        ("API Compatibility", test_api_compatibility),
        ("System Settings", test_system_settings),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ [TEST] {test_name} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Migration is successful!")
        return True
    else:
        print(f"\n⚠️ {failed} tests failed. Please review the issues above.")
        return False

async def main():
    """Main test function."""
    success = await run_all_tests()
    
    if success:
        print("\n🚀 NEXT STEPS:")
        print("1. Run the new API: python -m src.api_supabase")
        print("2. Test the API endpoints with curl or Postman")
        print("3. Update the frontend to use the new API")
        print("4. Deploy to production")
    else:
        print("\n🔧 FIXES NEEDED:")
        print("1. Review failed tests above")
        print("2. Check Supabase configuration")
        print("3. Verify database schema was created correctly")
        print("4. Test individual components")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
