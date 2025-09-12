"""
FastAPI backend for Polaroo utility bill processing with full Supabase integration.

This API provides endpoints for:
1. Running monthly utility calculations
2. Retrieving historical data
3. Managing configuration settings
4. Exporting reports
5. Processing invoices with AI analysis

All data is stored in Supabase with proper relationships and file storage.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import tempfile
import json
import asyncio
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import io

from src.supabase_client import get_supabase_manager, ProcessingSession, PropertyResult
from src.polaroo_scrape_supabase import process_property_invoices, process_multiple_properties
from src.load_supabase import create_processing_session, update_processing_session

# Initialize FastAPI app
app = FastAPI(
    title="Utility Bill Calculator API (Supabase)",
    description="API for processing Polaroo utility reports with full Supabase integration",
    version="2.0.0"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Pydantic models for request/response
class CalculationRequest(BaseModel):
    auto_save: bool = True
    start_date: Optional[str] = None  # YYYY-MM format
    end_date: Optional[str] = None    # YYYY-MM format

class PropertyProcessingRequest(BaseModel):
    property_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class BatchProcessingRequest(BaseModel):
    property_names: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class CalculationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    status: str
    total_properties: int
    successful_properties: int
    failed_properties: int
    total_cost: float
    total_overuse: float
    created_at: datetime
    completed_at: Optional[datetime] = None

# =============================================
# BASIC ENDPOINTS
# =============================================

@app.get("/")
async def root():
    """Serve the main application."""
    return FileResponse("src/static/index.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        manager = get_supabase_manager()
        # Test database connection
        properties = manager.get_all_properties()
        
        return {
            "status": "healthy",
            "service": "Utility Bill Calculator API (Supabase)",
            "version": "2.0.0",
            "database": "connected",
            "properties_count": len(properties),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "Utility Bill Calculator API (Supabase)",
            "version": "2.0.0",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check."""
    try:
        manager = get_supabase_manager()
        
        # Check database tables
        properties = manager.get_all_properties()
        sessions = manager.client.table("processing_sessions").select("id").limit(1).execute()
        
        return {
            "status": "healthy",
            "database": "connected",
            "supabase": "configured",
            "properties_count": len(properties),
            "tables_accessible": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "supabase": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# =============================================
# PROPERTY MANAGEMENT ENDPOINTS
# =============================================

@app.get("/api/properties")
async def get_all_properties():
    """Get all properties."""
    try:
        manager = get_supabase_manager()
        properties = manager.get_all_properties()
        
        return {
            "success": True,
            "properties": [
                {
                    "id": prop.id,
                    "name": prop.name,
                    "room_count": prop.room_count,
                    "special_allowance": prop.special_allowance,
                    "allowance": manager.get_property_allowance(prop.name)
                }
                for prop in properties
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/properties/{property_name}/allowance")
async def get_property_allowance(property_name: str):
    """Get allowance for a specific property."""
    try:
        manager = get_supabase_manager()
        allowance = manager.get_property_allowance(property_name)
        
        return {
            "property_name": property_name,
            "allowance": allowance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# PROCESSING ENDPOINTS
# =============================================

@app.post("/api/process-property", response_model=CalculationResponse)
async def process_single_property(request: PropertyProcessingRequest):
    """Process invoices for a single property."""
    try:
        print(f"🚀 [API] Processing property: {request.property_name}")
        
        result = await process_property_invoices(
            property_name=request.property_name,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        if "error" in result:
            return CalculationResponse(
                success=False,
                message="Property processing failed",
                error=result["error"]
            )
        
        return CalculationResponse(
            success=True,
            message=f"Property processing completed for {request.property_name}",
            data=result
        )
        
    except Exception as e:
        print(f"❌ [API] Property processing failed: {e}")
        return CalculationResponse(
            success=False,
            message="Property processing failed",
            error=str(e)
        )

@app.post("/api/process-batch", response_model=CalculationResponse)
async def process_batch_properties(request: BatchProcessingRequest):
    """Process invoices for multiple properties."""
    try:
        print(f"🚀 [API] Processing batch: {len(request.property_names)} properties")
        
        result = await process_multiple_properties(
            property_names=request.property_names,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        if "error" in result:
            return CalculationResponse(
                success=False,
                message="Batch processing failed",
                error=result["error"]
            )
        
        return CalculationResponse(
            success=True,
            message=f"Batch processing completed: {result['successful_properties']}/{result['total_properties']} successful",
            data=result
        )
        
    except Exception as e:
        print(f"❌ [API] Batch processing failed: {e}")
        return CalculationResponse(
            success=False,
            message="Batch processing failed",
            error=str(e)
        )

@app.post("/api/process-first-10", response_model=CalculationResponse)
async def process_first_10_properties():
    """Process the first 10 properties."""
    try:
        print("🚀 [API] Processing first 10 properties...")
        
        manager = get_supabase_manager()
        properties = manager.get_all_properties()[:10]
        property_names = [prop.name for prop in properties]
        
        result = await process_multiple_properties(property_names)
        
        if "error" in result:
            return CalculationResponse(
                success=False,
                message="First 10 properties processing failed",
                error=result["error"]
            )
        
        return CalculationResponse(
            success=True,
            message=f"First 10 properties processed: {result['successful_properties']}/{result['total_properties']} successful",
            data=result
        )
        
    except Exception as e:
        print(f"❌ [API] First 10 properties processing failed: {e}")
        return CalculationResponse(
            success=False,
            message="First 10 properties processing failed",
            error=str(e)
        )

# =============================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================

@app.get("/api/sessions")
async def get_processing_sessions():
    """Get all processing sessions."""
    try:
        manager = get_supabase_manager()
        result = manager.client.table("processing_sessions").select("*").order("created_at", desc=True).execute()
        
        sessions = []
        for data in result.data:
            sessions.append({
                "id": data["id"],
                "session_name": data.get("session_name"),
                "start_date": data["start_date"],
                "end_date": data["end_date"],
                "status": data["status"],
                "total_properties": data["total_properties"],
                "successful_properties": data["successful_properties"],
                "failed_properties": data["failed_properties"],
                "total_cost": float(data["total_cost"]),
                "total_overuse": float(data["total_overuse"]),
                "created_at": data["created_at"],
                "completed_at": data.get("completed_at")
            })
        
        return {"sessions": sessions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_processing_session(session_id: str):
    """Get a specific processing session."""
    try:
        manager = get_supabase_manager()
        session = manager.get_processing_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(
            session_id=session.id,
            status=session.status,
            total_properties=session.total_properties,
            successful_properties=session.successful_properties,
            failed_properties=session.failed_properties,
            total_cost=session.total_cost,
            total_overuse=session.total_overuse,
            created_at=session.created_at,
            completed_at=session.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/results")
async def get_session_results(session_id: str):
    """Get property results for a session."""
    try:
        manager = get_supabase_manager()
        results = manager.get_property_results_by_session(session_id)
        
        return {
            "session_id": session_id,
            "results": [
                {
                    "id": result.id,
                    "property_name": result.property_name,
                    "room_count": result.room_count,
                    "allowance": result.allowance,
                    "total_electricity_cost": result.total_electricity_cost,
                    "total_water_cost": result.total_water_cost,
                    "total_cost": result.total_cost,
                    "overuse": result.overuse,
                    "selected_invoices_count": result.selected_invoices_count,
                    "downloaded_files_count": result.downloaded_files_count,
                    "processing_status": result.processing_status,
                    "error_message": result.error_message,
                    "created_at": result.created_at
                }
                for result in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# DATA EXPORT ENDPOINTS
# =============================================

@app.get("/api/export/session/{session_id}/csv")
async def export_session_csv(session_id: str):
    """Export session results as CSV."""
    try:
        manager = get_supabase_manager()
        results = manager.get_property_results_by_session(session_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found for this session")
        
        # Create DataFrame
        data = []
        for result in results:
            data.append({
                "Property": result.property_name,
                "Room Count": result.room_count,
                "Allowance": result.allowance,
                "Electricity Cost": result.total_electricity_cost,
                "Water Cost": result.total_water_cost,
                "Total Cost": result.total_cost,
                "Overuse": result.overuse,
                "Selected Invoices": result.selected_invoices_count,
                "Downloaded Files": result.downloaded_files_count,
                "Status": result.processing_status
            })
        
        df = pd.DataFrame(data)
        
        # Create CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        return JSONResponse(
            content={"csv_data": csv_buffer.getvalue()},
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}_results.csv"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/session/{session_id}/excel")
async def export_session_excel(session_id: str):
    """Export session results as Excel."""
    try:
        manager = get_supabase_manager()
        results = manager.get_property_results_by_session(session_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found for this session")
        
        # Create DataFrame
        data = []
        for result in results:
            data.append({
                "Property": result.property_name,
                "Room Count": result.room_count,
                "Allowance": result.allowance,
                "Electricity Cost": result.total_electricity_cost,
                "Water Cost": result.total_water_cost,
                "Total Cost": result.total_cost,
                "Overuse": result.overuse,
                "Selected Invoices": result.selected_invoices_count,
                "Downloaded Files": result.downloaded_files_count,
                "Status": result.processing_status
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Session Results', index=False)
            
            # Create summary sheet
            summary_data = {
                'Metric': ['Total Properties', 'Successful Properties', 'Failed Properties',
                          'Total Cost', 'Total Overuse', 'Average Cost per Property'],
                'Value': [
                    len(results),
                    len([r for r in results if r.processing_status == 'completed']),
                    len([r for r in results if r.processing_status == 'failed']),
                    sum(r.total_cost for r in results),
                    sum(r.overuse for r in results),
                    sum(r.total_cost for r in results) / len(results) if results else 0
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        excel_buffer.seek(0)
        
        return JSONResponse(
            content={"excel_data": excel_buffer.getvalue().hex()},
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}_results.xlsx"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# CONFIGURATION ENDPOINTS
# =============================================

@app.get("/api/configuration")
async def get_configuration():
    """Get current configuration settings."""
    try:
        manager = get_supabase_manager()
        
        # Get room limits
        room_limits_result = manager.client.table("room_limits").select("*").execute()
        room_limits = {limit["room_count"]: limit["allowance"] for limit in room_limits_result.data}
        
        # Get properties
        properties = manager.get_all_properties()
        
        return {
            "allowance_system": "room-based",
            "room_limits": room_limits,
            "properties": [
                {
                    "name": prop.name,
                    "room_count": prop.room_count,
                    "special_allowance": prop.special_allowance,
                    "allowance": manager.get_property_allowance(prop.name)
                }
                for prop in properties
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system-settings")
async def get_system_settings():
    """Get system settings."""
    try:
        manager = get_supabase_manager()
        result = manager.client.table("system_settings").select("*").execute()
        
        settings = {}
        for setting in result.data:
            settings[setting["setting_key"]] = {
                "value": setting["setting_value"],
                "description": setting.get("description")
            }
        
        return {"settings": settings}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# LEGACY COMPATIBILITY ENDPOINTS
# =============================================

@app.post("/api/calculate", response_model=CalculationResponse)
async def calculate_monthly_report_legacy(request: CalculationRequest):
    """
    Legacy endpoint for monthly calculation.
    
    This endpoint maintains backward compatibility while using the new Supabase system.
    """
    try:
        print("🚀 [API] Legacy monthly calculation request...")
        
        # Get all properties
        manager = get_supabase_manager()
        properties = manager.get_all_properties()
        
        # Process first 10 properties as a sample
        property_names = [prop.name for prop in properties[:10]]
        
        result = await process_multiple_properties(
            property_names=property_names,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        if "error" in result:
            return CalculationResponse(
                success=False,
                message="Legacy calculation failed",
                error=result["error"]
            )
        
        # Convert to legacy format
        legacy_data = {
            "properties": [
                {
                    "name": prop["property_name"],
                    "elec_cost": prop.get("total_electricity_cost", 0),
                    "water_cost": prop.get("total_water_cost", 0),
                    "elec_extra": 0,  # No individual elec extra in new system
                    "water_extra": 0,  # No individual water extra in new system
                    "total_extra": prop.get("overuse", 0),
                    "allowance": prop.get("allowance", 50)
                }
                for prop in result.get("properties", [])
                if "error" not in prop
            ],
            "summary": {
                "total_properties": result.get("total_properties", 0),
                "total_electricity_cost": sum(p.get("total_electricity_cost", 0) for p in result.get("properties", []) if "error" not in p),
                "total_water_cost": sum(p.get("total_water_cost", 0) for p in result.get("properties", []) if "error" not in p),
                "total_electricity_extra": 0,
                "total_water_extra": 0,
                "total_extra": result.get("total_overuse", 0),
                "properties_with_overages": len([p for p in result.get("properties", []) if p.get("overuse", 0) > 0 and "error" not in p]),
                "calculation_date": datetime.now().isoformat(),
                "allowance_system": "room-based",
                "filter_applied": "first_10_properties"
            }
        }
        
        return CalculationResponse(
            success=True,
            message="Legacy calculation completed successfully using Supabase",
            data=legacy_data
        )
        
    except Exception as e:
        print(f"❌ [API] Legacy calculation failed: {e}")
        return CalculationResponse(
            success=False,
            message="Legacy calculation failed",
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
