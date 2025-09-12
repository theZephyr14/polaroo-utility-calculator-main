#!/usr/bin/env python3
"""
Simple test to verify Supabase connection works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_connection():
    """Test basic Supabase connection."""
    try:
        from src.supabase_client import get_supabase_manager
        
        print("🔍 [TEST] Testing Supabase connection...")
        
        manager = get_supabase_manager()
        
        # Test basic connection
        properties = manager.get_all_properties()
        print(f"✅ [TEST] Connected! Found {len(properties)} properties")
        
        # Test property allowance
        allowance = manager.get_property_allowance("Aribau 1º 1ª")
        print(f"✅ [TEST] Property allowance: €{allowance}")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n🎉 SUPABASE CONNECTION WORKS!")
        print("You can now run: python -m src.api_supabase")
    else:
        print("\n❌ CONNECTION FAILED!")
        print("Check your Supabase setup and try again.")
    
    sys.exit(0 if success else 1)
