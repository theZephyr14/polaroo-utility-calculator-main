"""
Legacy Supabase functions - now using the new Supabase client system.

This module provides backward compatibility while migrating to the new
comprehensive Supabase integration.
"""

import io
import hashlib
from datetime import date
from typing import List, Dict, Any
from src.supabase_client import get_supabase_manager, FileStorage
from src.config import STORAGE_BUCKET, STORAGE_PREFIX

def _client():
    """Legacy client function - now uses the new manager."""
    return get_supabase_manager().client

def _md5(b: bytes) -> str:
    """Calculate MD5 hash of bytes."""
    return hashlib.md5(b).hexdigest()

def upload_raw(report_date: date, file_bytes: bytes, filename: str) -> str:
    """
    Upload raw report file to Supabase Storage.
    
    This function maintains backward compatibility while using the new system.
    """
    try:
        manager = get_supabase_manager()
        
        # Clean the filename for storage
        clean_filename = manager.client.rpc("clean_file_path", {"input_path": filename}).execute().data
        
        # Generate file path
        md5 = _md5(file_bytes)
        file_path = f"{STORAGE_PREFIX}/{report_date.isoformat()}/{md5}_{clean_filename}"
        
        # Upload to Supabase Storage
        storage_result = manager.client.storage.from_(STORAGE_BUCKET).upload(
            path=file_path,
            file=io.BytesIO(file_bytes),
            file_options={
                "cache-control": "3600",
                "content-type": "application/octet-stream",
                "upsert": True
            }
        )
        
        if storage_result:
            # Store metadata in the new file_storage table
            file_storage = FileStorage(
                property_name="raw_report",
                file_name=clean_filename,
                file_path=file_path,
                file_size=len(file_bytes),
                content_type="application/octet-stream",
                md5_hash=md5
            )
            
            data = {
                "property_name": file_storage.property_name,
                "file_name": file_storage.file_name,
                "file_path": file_storage.file_path,
                "file_size": file_storage.file_size,
                "content_type": file_storage.content_type,
                "storage_bucket": file_storage.storage_bucket,
                "md5_hash": file_storage.md5_hash
            }
            
            manager.client.table("file_storage").insert(data).execute()
            print(f"✅ [UPLOAD] Raw report uploaded: {file_path}")
            return file_path
        else:
            print(f"❌ [UPLOAD] Failed to upload raw report: {filename}")
            return ""
            
    except Exception as e:
        print(f"❌ [UPLOAD] Error uploading raw report {filename}: {e}")
        return ""

def upsert_kpis(kpi: Dict[str, Any]):
    """
    Upsert KPIs to the database.
    
    This function is maintained for backward compatibility.
    The new system uses processing_sessions and property_results tables.
    """
    try:
        manager = get_supabase_manager()
        
        # Convert legacy KPI format to new format if needed
        # For now, just log that this was called
        print(f"📊 [KPIS] Legacy upsert_kpis called with data: {list(kpi.keys())}")
        
        # If you need to store KPIs in the new system, you can add logic here
        # For example, store in system_settings or create a kpis table
        
    except Exception as e:
        print(f"❌ [KPIS] Error upserting KPIs: {e}")

def upsert_monthly(rows: List[Dict[str, Any]]):
    """
    Upsert monthly service data.
    
    This function now uses the new monthly_service_data table.
    """
    if not rows:
        return
    
    try:
        manager = get_supabase_manager()
        
        # Convert legacy format to new format
        converted_rows = []
        for row in rows:
            converted_row = {
                "property_name": row.get("Property", row.get("property_name", "Unknown")),
                "report_date": row.get("report_date", date.today().isoformat()),
                "electricity_cost": float(row.get("Electricity Cost", row.get("electricity_cost", 0))),
                "water_cost": float(row.get("Water Cost", row.get("water_cost", 0))),
                "total_cost": float(row.get("Total Cost", row.get("total_cost", 0))),
                "allowance": float(row.get("Allowance", row.get("allowance", 50))),
                "total_extra": float(row.get("Total Extra", row.get("total_extra", 0))),
                "electricity_extra": float(row.get("elec_extra", row.get("electricity_extra", 0))),
                "water_extra": float(row.get("water_extra", 0))
            }
            converted_rows.append(converted_row)
        
        # Insert in batches
        batch_size = 1000
        for i in range(0, len(converted_rows), batch_size):
            batch = converted_rows[i:i + batch_size]
            manager.client.table("monthly_service_data").upsert(batch).execute()
        
        print(f"✅ [MONTHLY] Upserted {len(converted_rows)} monthly service records")
        
    except Exception as e:
        print(f"❌ [MONTHLY] Error upserting monthly data: {e}")

def upsert_assets(rows: List[Dict[str, Any]]):
    """
    Upsert asset costs data.
    
    This function is maintained for backward compatibility.
    Asset costs can be stored in the new system if needed.
    """
    if not rows:
        return
    
    try:
        manager = get_supabase_manager()
        
        # For now, just log that this was called
        print(f"🏢 [ASSETS] Legacy upsert_assets called with {len(rows)} records")
        
        # If you need to store asset costs in the new system, you can add logic here
        # For example, create an asset_costs table or store in system_settings
        
    except Exception as e:
        print(f"❌ [ASSETS] Error upserting asset costs: {e}")

# New functions for the updated system
def create_processing_session(session_name: str = None, start_date: date = None, end_date: date = None):
    """Create a new processing session."""
    from src.supabase_client import ProcessingSession
    
    manager = get_supabase_manager()
    session = ProcessingSession(
        session_name=session_name,
        start_date=start_date or date.today(),
        end_date=end_date or date.today()
    )
    
    session_id = manager.create_processing_session(session)
    if session_id:
        print(f"✅ [SESSION] Created processing session: {session_id}")
        return session_id
    else:
        print(f"❌ [SESSION] Failed to create processing session")
        return None

def update_processing_session(session_id: str, **updates):
    """Update a processing session."""
    manager = get_supabase_manager()
    success = manager.update_processing_session(session_id, updates)
    if success:
        print(f"✅ [SESSION] Updated processing session: {session_id}")
    else:
        print(f"❌ [SESSION] Failed to update processing session: {session_id}")
    return success

def get_processing_session(session_id: str):
    """Get a processing session."""
    manager = get_supabase_manager()
    return manager.get_processing_session(session_id)
