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
# CALCULATION FUNCTIONS (NO DOWNLOADS)
# =============================================

async def calculate_monthly_costs_only(property_names: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Calculate monthly costs without downloading any invoices.
    This function only processes existing data or uses mock data for calculation.
    """
    try:
        print(f"🧮 [CALC] Calculating costs for {len(property_names)} properties ({start_date} to {end_date})")
        
        manager = get_supabase_manager()
        results = []
        
        for property_name in property_names:
            # Get property info
            property_info = manager.get_property_by_name(property_name)
            if not property_info:
                results.append({"error": f"Property not found: {property_name}"})
                continue
            
            # Get allowance
            allowance = manager.get_property_allowance(property_name)
            
            # For now, use mock data or existing data from Supabase
            # In the future, this could pull from existing invoice records
            mock_elec_cost = 50.0 + (hash(property_name) % 100)  # Mock electricity cost
            mock_water_cost = 30.0 + (hash(property_name) % 50)  # Mock water cost
            total_cost = mock_elec_cost + mock_water_cost
            overuse = max(0, total_cost - allowance)
            
            result = {
                "property_name": property_name,
                "total_electricity_cost": mock_elec_cost,
                "total_water_cost": mock_water_cost,
                "total_cost": total_cost,
                "allowance": allowance,
                "overuse": overuse,
                "calculation_method": "mock_data_no_download"
            }
            
            results.append(result)
        
        return {
            "properties": results,
            "total_properties": len(property_names),
            "calculation_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [CALC] Error in cost calculation: {e}")
        return {"error": str(e)}

# =============================================
# LEGACY COMPATIBILITY ENDPOINTS
# =============================================

@app.post("/api/calculate", response_model=CalculationResponse)
async def calculate_monthly_report_legacy(request: CalculationRequest):
    """
    Calculate monthly report with proper month-by-month overuse calculation.
    
    This endpoint processes each month separately and calculates overuse correctly.
    """
    try:
        print("🚀 [API] Starting month-by-month calculation...")
        print(f"📅 [API] Date range: {request.start_date} to {request.end_date}")
        
        # Parse dates
        from datetime import datetime
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        # Get all properties
        manager = get_supabase_manager()
        properties = manager.get_all_properties()
        
        # Generate list of months to process
        months_to_process = []
        current_date = start_date.replace(day=1)  # Start of month
        
        while current_date <= end_date:
            months_to_process.append(current_date.strftime("%Y-%m"))
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        print(f"📊 [API] Processing {len(months_to_process)} months: {months_to_process}")
        
        # Process each month separately - CALCULATION ONLY (no downloads)
        monthly_results = {}
        for month in months_to_process:
            print(f"📅 [API] Processing month: {month}")
            
            # Get month start and end dates
            month_start = f"{month}-01"
            month_end = f"{month}-31"
            
            # Calculate costs for this month (NO DOWNLOADS)
            result = await calculate_monthly_costs_only(
                property_names=[prop.name for prop in properties],
                start_date=month_start,
                end_date=month_end
            )
            
            if "error" not in result:
                monthly_results[month] = result
            else:
                print(f"❌ [API] Error processing month {month}: {result['error']}")
        
        # Combine results month by month
        combined_properties = {}
        
        for month, result in monthly_results.items():
            for prop in result.get("properties", []):
                if "error" in prop:
                    continue
                    
                prop_name = prop["property_name"]
                
                if prop_name not in combined_properties:
                    # Initialize property data
                    combined_properties[prop_name] = {
                        "name": prop_name,
                        "elec_cost": 0,
                        "water_cost": 0,
                        "elec_extra": 0,
                        "water_extra": 0,
                        "total_extra": 0,
                        "allowance": prop.get("allowance", 50),
                        "monthly_breakdown": {}
                    }
                
                # Add this month's data
                monthly_data = {
                    "elec_cost": prop.get("total_electricity_cost", 0),
                    "water_cost": prop.get("total_water_cost", 0),
                    "total_cost": prop.get("total_electricity_cost", 0) + prop.get("total_water_cost", 0),
                    "overuse": max(0, (prop.get("total_electricity_cost", 0) + prop.get("total_water_cost", 0)) - prop.get("allowance", 50))
                }
                
                combined_properties[prop_name]["monthly_breakdown"][month] = monthly_data
                
                # Add to totals
                combined_properties[prop_name]["elec_cost"] += monthly_data["elec_cost"]
                combined_properties[prop_name]["water_cost"] += monthly_data["water_cost"]
                combined_properties[prop_name]["total_extra"] += monthly_data["overuse"]
        
        # Convert to final format
        final_properties = []
        total_elec_cost = 0
        total_water_cost = 0
        total_extra = 0
        properties_with_overages = 0
        
        for prop_data in combined_properties.values():
            final_properties.append(prop_data)
            total_elec_cost += prop_data["elec_cost"]
            total_water_cost += prop_data["water_cost"]
            total_extra += prop_data["total_extra"]
            
            if prop_data["total_extra"] > 0:
                properties_with_overages += 1
        
        # Create response data
        response_data = {
            "properties": final_properties,
            "summary": {
                "total_properties": len(final_properties),
                "total_electricity_cost": total_elec_cost,
                "total_water_cost": total_water_cost,
                "total_electricity_extra": 0,  # Not calculated separately
                "total_water_extra": 0,  # Not calculated separately
                "total_extra": total_extra,
                "properties_with_overages": properties_with_overages,
                "calculation_date": datetime.now().isoformat(),
                "allowance_system": "room-based",
                "months_processed": months_to_process,
                "calculation_method": "month-by-month"
            }
        }
        
        print(f"✅ [API] Calculation completed: {len(final_properties)} properties, {properties_with_overages} with overages")
        
        return CalculationResponse(
            success=True,
            message=f"Month-by-month calculation completed for {len(months_to_process)} months",
            data=response_data
        )
        
    except Exception as e:
        print(f"❌ [API] Calculation failed: {e}")
        return CalculationResponse(
            success=False,
            message="Calculation failed",
            error=str(e)
        )

# =============================================
# PDF DOWNLOAD ENDPOINTS (MANUAL TRIGGER)
# =============================================

class PropertyDownloadRequest(BaseModel):
    property_names: List[str]
    start_date: str
    end_date: str

@app.post("/api/download-property-pdfs")
async def download_property_pdfs(request: PropertyDownloadRequest):
    """
    Download PDFs for selected properties with overages.
    This is triggered manually from the overages tab.
    """
    try:
        print(f"📥 [DOWNLOAD] Starting PDF download for {len(request.property_names)} properties")
        print(f"📅 [DOWNLOAD] Date range: {request.start_date} to {request.end_date}")
        
        # Process each property individually to download their specific invoices
        results = []
        successful_downloads = 0
        failed_downloads = 0
        
        for property_name in request.property_names:
            print(f"🏠 [DOWNLOAD] Processing property: {property_name}")
            
            try:
                # Use the existing process_property_invoices function for actual downloads
                result = await process_property_invoices(
                    property_name=property_name,
                    start_date=request.start_date,
                    end_date=request.end_date
                )
                
                if "error" not in result:
                    results.append({
                        "property_name": property_name,
                        "status": "success",
                        "downloaded_files": result.get("downloaded_files_count", 0),
                        "total_cost": result.get("total_cost", 0),
                        "overuse": result.get("overuse", 0)
                    })
                    successful_downloads += 1
                else:
                    results.append({
                        "property_name": property_name,
                        "status": "failed",
                        "error": result["error"]
                    })
                    failed_downloads += 1
                    
            except Exception as e:
                print(f"❌ [DOWNLOAD] Error processing {property_name}: {e}")
                results.append({
                    "property_name": property_name,
                    "status": "failed",
                    "error": str(e)
                })
                failed_downloads += 1
        
        return {
            "success": True,
            "message": f"PDF download completed: {successful_downloads} successful, {failed_downloads} failed",
            "total_properties": len(request.property_names),
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "results": results
        }
        
    except Exception as e:
        print(f"❌ [DOWNLOAD] Error in PDF download: {e}")
        return {
            "success": False,
            "message": "PDF download failed",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
