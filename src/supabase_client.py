"""
Supabase client and data models for Polaroo Utility Calculator.

This module provides a comprehensive Supabase integration that replaces
all local storage and processing with cloud-based database operations.
"""

import io
import hashlib
import uuid
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, STORAGE_BUCKET, STORAGE_PREFIX

# Initialize Supabase client
def get_supabase_client() -> Client:
    """Get the Supabase client instance."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# =============================================
# DATA MODELS
# =============================================

@dataclass
class Property:
    id: Optional[str] = None
    name: str = ""
    room_count: int = 1
    special_allowance: Optional[float] = None
    building_key: str = ""
    floor_code: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class ProcessingSession:
    id: Optional[str] = None
    session_name: Optional[str] = None
    start_date: date = date.today()
    end_date: date = date.today()
    status: str = "pending"  # pending, processing, completed, failed
    total_properties: int = 0
    successful_properties: int = 0
    failed_properties: int = 0
    total_cost: float = 0.0
    total_overuse: float = 0.0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class PropertyResult:
    id: Optional[str] = None
    session_id: Optional[str] = None
    property_id: Optional[str] = None
    property_name: str = ""
    room_count: int = 1
    allowance: float = 0.0
    total_electricity_cost: float = 0.0
    total_water_cost: float = 0.0
    total_cost: float = 0.0
    overuse: float = 0.0
    selected_invoices_count: int = 0
    downloaded_files_count: int = 0
    llm_reasoning: Optional[str] = None
    processing_status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Invoice:
    id: Optional[str] = None
    property_result_id: Optional[str] = None
    invoice_number: str = ""
    service_type: str = ""  # electricity, water, gas
    amount: float = 0.0
    invoice_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    provider: Optional[str] = None
    contract_code: Optional[str] = None
    is_selected: bool = False
    is_downloaded: bool = False
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class FileStorage:
    id: Optional[str] = None
    property_name: str = ""
    invoice_number: Optional[str] = None
    file_name: str = ""
    file_path: str = ""
    file_size: int = 0
    content_type: str = "application/pdf"
    storage_bucket: str = STORAGE_BUCKET
    md5_hash: Optional[str] = None
    created_at: Optional[datetime] = None

# =============================================
# SUPABASE OPERATIONS
# =============================================

class SupabaseManager:
    """Main class for all Supabase operations."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # =============================================
    # PROPERTY OPERATIONS
    # =============================================
    
    def get_property_by_name(self, name: str) -> Optional[Property]:
        """Get a property by name."""
        try:
            result = self.client.table("properties").select("*").eq("name", name).execute()
            if result.data:
                data = result.data[0]
                return Property(
                    id=data["id"],
                    name=data["name"],
                    room_count=data["room_count"],
                    special_allowance=data.get("special_allowance"),
                    building_key=data["building_key"],
                    floor_code=data.get("floor_code", ""),
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
                )
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting property {name}: {e}")
            return None
    
    def get_all_properties(self) -> List[Property]:
        """Get all properties."""
        try:
            result = self.client.table("properties").select("*").execute()
            properties = []
            for data in result.data:
                properties.append(Property(
                    id=data["id"],
                    name=data["name"],
                    room_count=data["room_count"],
                    special_allowance=data.get("special_allowance"),
                    building_key=data["building_key"],
                    floor_code=data.get("floor_code", ""),
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
                ))
            return properties
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting all properties: {e}")
            return []
    
    def get_property_allowance(self, property_name: str) -> float:
        """Get the allowance for a property using the database function."""
        try:
            result = self.client.rpc("get_property_allowance", {"property_name": property_name}).execute()
            return float(result.data) if result.data else 50.0
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting allowance for {property_name}: {e}")
            return 50.0
    
    # =============================================
    # PROCESSING SESSION OPERATIONS
    # =============================================
    
    def create_processing_session(self, session: ProcessingSession) -> Optional[str]:
        """Create a new processing session."""
        try:
            data = asdict(session)
            # Remove None values and convert dates
            data = {k: v for k, v in data.items() if v is not None}
            if 'start_date' in data:
                data['start_date'] = data['start_date'].isoformat()
            if 'end_date' in data:
                data['end_date'] = data['end_date'].isoformat()
            
            result = self.client.table("processing_sessions").insert(data).execute()
            if result.data:
                return result.data[0]["id"]
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error creating processing session: {e}")
            return None
    
    def update_processing_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update a processing session."""
        try:
            # Convert dates to strings
            if 'start_date' in updates and isinstance(updates['start_date'], date):
                updates['start_date'] = updates['start_date'].isoformat()
            if 'end_date' in updates and isinstance(updates['end_date'], date):
                updates['end_date'] = updates['end_date'].isoformat()
            if 'completed_at' in updates and isinstance(updates['completed_at'], datetime):
                updates['completed_at'] = updates['completed_at'].isoformat()
            
            result = self.client.table("processing_sessions").update(updates).eq("id", session_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"❌ [SUPABASE] Error updating processing session {session_id}: {e}")
            return False
    
    def get_processing_session(self, session_id: str) -> Optional[ProcessingSession]:
        """Get a processing session by ID."""
        try:
            result = self.client.table("processing_sessions").select("*").eq("id", session_id).execute()
            if result.data:
                data = result.data[0]
                return ProcessingSession(
                    id=data["id"],
                    session_name=data.get("session_name"),
                    start_date=datetime.fromisoformat(data["start_date"]).date(),
                    end_date=datetime.fromisoformat(data["end_date"]).date(),
                    status=data["status"],
                    total_properties=data["total_properties"],
                    successful_properties=data["successful_properties"],
                    failed_properties=data["failed_properties"],
                    total_cost=float(data["total_cost"]),
                    total_overuse=float(data["total_overuse"]),
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
                    completed_at=datetime.fromisoformat(data["completed_at"].replace('Z', '+00:00')) if data.get("completed_at") else None
                )
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting processing session {session_id}: {e}")
            return None
    
    # =============================================
    # PROPERTY RESULT OPERATIONS
    # =============================================
    
    def create_property_result(self, result: PropertyResult) -> Optional[str]:
        """Create a property result."""
        try:
            data = asdict(result)
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            db_result = self.client.table("property_results").insert(data).execute()
            if db_result.data:
                return db_result.data[0]["id"]
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error creating property result: {e}")
            return None
    
    def update_property_result(self, result_id: str, updates: Dict[str, Any]) -> bool:
        """Update a property result."""
        try:
            result = self.client.table("property_results").update(updates).eq("id", result_id).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"❌ [SUPABASE] Error updating property result {result_id}: {e}")
            return False
    
    def get_property_results_by_session(self, session_id: str) -> List[PropertyResult]:
        """Get all property results for a session."""
        try:
            result = self.client.table("property_results").select("*").eq("session_id", session_id).execute()
            results = []
            for data in result.data:
                results.append(PropertyResult(
                    id=data["id"],
                    session_id=data["session_id"],
                    property_id=data.get("property_id"),
                    property_name=data["property_name"],
                    room_count=data["room_count"],
                    allowance=float(data["allowance"]),
                    total_electricity_cost=float(data["total_electricity_cost"]),
                    total_water_cost=float(data["total_water_cost"]),
                    total_cost=float(data["total_cost"]),
                    overuse=float(data["overuse"]),
                    selected_invoices_count=data["selected_invoices_count"],
                    downloaded_files_count=data["downloaded_files_count"],
                    llm_reasoning=data.get("llm_reasoning"),
                    processing_status=data["processing_status"],
                    error_message=data.get("error_message"),
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')) if data.get("updated_at") else None
                ))
            return results
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting property results for session {session_id}: {e}")
            return []
    
    # =============================================
    # INVOICE OPERATIONS
    # =============================================
    
    def create_invoice(self, invoice: Invoice) -> Optional[str]:
        """Create an invoice."""
        try:
            data = asdict(invoice)
            # Remove None values and convert dates
            data = {k: v for k, v in data.items() if v is not None}
            if 'invoice_date' in data and isinstance(data['invoice_date'], date):
                data['invoice_date'] = data['invoice_date'].isoformat()
            if 'period_start' in data and isinstance(data['period_start'], date):
                data['period_start'] = data['period_start'].isoformat()
            if 'period_end' in data and isinstance(data['period_end'], date):
                data['period_end'] = data['period_end'].isoformat()
            
            result = self.client.table("invoices").insert(data).execute()
            if result.data:
                return result.data[0]["id"]
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error creating invoice: {e}")
            return None
    
    def create_invoices_batch(self, invoices: List[Invoice]) -> List[str]:
        """Create multiple invoices in a batch."""
        try:
            data_list = []
            for invoice in invoices:
                data = asdict(invoice)
                # Remove None values and convert dates
                data = {k: v for k, v in data.items() if v is not None}
                if 'invoice_date' in data and isinstance(data['invoice_date'], date):
                    data['invoice_date'] = data['invoice_date'].isoformat()
                if 'period_start' in data and isinstance(data['period_start'], date):
                    data['period_start'] = data['period_start'].isoformat()
                if 'period_end' in data and isinstance(data['period_end'], date):
                    data['period_end'] = data['period_end'].isoformat()
                data_list.append(data)
            
            result = self.client.table("invoices").insert(data_list).execute()
            if result.data:
                return [item["id"] for item in result.data]
            return []
        except Exception as e:
            print(f"❌ [SUPABASE] Error creating invoices batch: {e}")
            return []
    
    def get_invoices_by_property_result(self, property_result_id: str) -> List[Invoice]:
        """Get all invoices for a property result."""
        try:
            result = self.client.table("invoices").select("*").eq("property_result_id", property_result_id).execute()
            invoices = []
            for data in result.data:
                invoices.append(Invoice(
                    id=data["id"],
                    property_result_id=data["property_result_id"],
                    invoice_number=data["invoice_number"],
                    service_type=data["service_type"],
                    amount=float(data["amount"]),
                    invoice_date=datetime.fromisoformat(data["invoice_date"]).date() if data.get("invoice_date") else None,
                    period_start=datetime.fromisoformat(data["period_start"]).date() if data.get("period_start") else None,
                    period_end=datetime.fromisoformat(data["period_end"]).date() if data.get("period_end") else None,
                    provider=data.get("provider"),
                    contract_code=data.get("contract_code"),
                    is_selected=data["is_selected"],
                    is_downloaded=data["is_downloaded"],
                    file_path=data.get("file_path"),
                    file_size=data.get("file_size"),
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None
                ))
            return invoices
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting invoices for property result {property_result_id}: {e}")
            return []
    
    # =============================================
    # FILE STORAGE OPERATIONS
    # =============================================
    
    def upload_file(self, file_bytes: bytes, property_name: str, invoice_number: str = None, 
                   file_name: str = None, content_type: str = "application/pdf") -> Optional[str]:
        """Upload a file to Supabase Storage."""
        try:
            # Clean the property name for file path
            clean_property = self.client.rpc("clean_file_path", {"input_path": property_name}).execute().data
            
            # Generate file path
            if file_name is None:
                timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
                file_name = f"invoice_{clean_property}_{invoice_number or 'unknown'}_{timestamp}.pdf"
            
            file_path = f"{STORAGE_PREFIX}/{clean_property}/{file_name}"
            
            # Upload to Supabase Storage
            storage_result = self.client.storage.from_(STORAGE_BUCKET).upload(
                path=file_path,
                file=io.BytesIO(file_bytes),
                file_options={
                    "cache-control": "3600",
                    "content-type": content_type,
                    "upsert": True
                }
            )
            
            if storage_result:
                # Store metadata in database
                file_storage = FileStorage(
                    property_name=property_name,
                    invoice_number=invoice_number,
                    file_name=file_name,
                    file_path=file_path,
                    file_size=len(file_bytes),
                    content_type=content_type,
                    md5_hash=hashlib.md5(file_bytes).hexdigest()
                )
                
                data = asdict(file_storage)
                data = {k: v for k, v in data.items() if v is not None}
                
                db_result = self.client.table("file_storage").insert(data).execute()
                if db_result.data:
                    return file_path
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error uploading file for {property_name}: {e}")
            return None
    
    def get_file_url(self, file_path: str) -> Optional[str]:
        """Get a public URL for a file."""
        try:
            result = self.client.storage.from_(STORAGE_BUCKET).get_public_url(file_path)
            return result
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting file URL for {file_path}: {e}")
            return None
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """Download a file from Supabase Storage."""
        try:
            result = self.client.storage.from_(STORAGE_BUCKET).download(file_path)
            return result
        except Exception as e:
            print(f"❌ [SUPABASE] Error downloading file {file_path}: {e}")
            return None
    
    # =============================================
    # SYSTEM OPERATIONS
    # =============================================
    
    def get_system_setting(self, key: str) -> Optional[str]:
        """Get a system setting value."""
        try:
            result = self.client.table("system_settings").select("setting_value").eq("setting_key", key).execute()
            if result.data:
                return result.data[0]["setting_value"]
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting system setting {key}: {e}")
            return None
    
    def set_system_setting(self, key: str, value: str, description: str = None) -> bool:
        """Set a system setting value."""
        try:
            data = {
                "setting_key": key,
                "setting_value": value,
                "description": description
            }
            result = self.client.table("system_settings").upsert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"❌ [SUPABASE] Error setting system setting {key}: {e}")
            return False
    
    def get_api_credential(self, service_name: str) -> Optional[str]:
        """Get an API credential."""
        try:
            result = self.client.table("api_credentials").select("api_key").eq("service_name", service_name).eq("is_active", True).execute()
            if result.data:
                return result.data[0]["api_key"]
            return None
        except Exception as e:
            print(f"❌ [SUPABASE] Error getting API credential for {service_name}: {e}")
            return None

# =============================================
# CONVENIENCE FUNCTIONS
# =============================================

def get_supabase_manager() -> SupabaseManager:
    """Get a SupabaseManager instance."""
    return SupabaseManager()

def clean_file_path(path: str) -> str:
    """Clean a file path for Supabase Storage."""
    try:
        client = get_supabase_client()
        result = client.rpc("clean_file_path", {"input_path": path}).execute()
        return result.data
    except Exception as e:
        print(f"❌ [SUPABASE] Error cleaning file path {path}: {e}")
        # Fallback cleaning
        import re
        return re.sub(r'[^a-zA-Z0-9._/-]', '_', path)

def get_property_allowance(property_name: str) -> float:
    """Get the allowance for a property."""
    try:
        client = get_supabase_client()
        result = client.rpc("get_property_allowance", {"property_name": property_name}).execute()
        return float(result.data) if result.data else 50.0
    except Exception as e:
        print(f"❌ [SUPABASE] Error getting allowance for {property_name}: {e}")
        return 50.0
