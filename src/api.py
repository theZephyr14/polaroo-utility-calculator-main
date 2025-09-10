"""
FastAPI backend for Polaroo utility bill processing.

This API provides endpoints for:
1. Running monthly utility calculations
2. Retrieving historical data
3. Managing configuration settings
4. Exporting reports

Designed for production deployment on platforms like:
- Railway
- Renderm keepts. howto change it right?
- Heroku
- DigitalOcean App Platform
- AWS Elastic Beanstalk
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

from src.polaroo_scrape import download_report_sync, download_report_bytes
from src.polaroo_process import process_usage, USER_ADDRESSES
from src.load_supabase import upload_raw, upsert_monthly

# Initialize FastAPI app
app = FastAPI(
    title="Utility Bill Calculator API",
    description="API for processing Polaroo utility reports and calculating excess charges",
    version="1.0.0"
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

class CalculationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ConfigurationRequest(BaseModel):
    electricity_allowance: float
    water_allowance: float

# Global state for storing calculation results
calculation_results = {}

@app.get("/")
async def root():
    """Serve the main application."""
    return FileResponse("src/static/index.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Utility Bill Calculator API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",  # Add actual DB check
        "polaroo": "configured",  # Add actual Polaroo check
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/calculate", response_model=CalculationResponse)
async def calculate_monthly_report(request: CalculationRequest):
    """
    Run the monthly utility calculation workflow.
    
    This endpoint:
    1. Downloads the latest report from Polaroo
    2. Processes the data and calculates excess charges
    3. Optionally saves results to database
    4. Returns processed data for frontend display
    """
    try:
        print("🚀 [API] Starting monthly calculation request...")
        
        # Step 1: Download report from Polaroo
        print("📥 [API] Step 1/3: Downloading report from Polaroo...")
        file_bytes, filename = await download_report_bytes()
        print(f"✅ [API] Report downloaded: {filename} ({len(file_bytes)} bytes)")
        
        # Step 2: Archive to Supabase (if requested)
        if request.auto_save:
            print("☁️ [API] Step 2/3: Archiving report to Supabase...")
            try:
                # Ensure we have bytes, not BytesIO
                if hasattr(file_bytes, 'read'):
                    file_bytes = file_bytes.read()
                upload_raw(date.today(), file_bytes, filename)
                print("✅ [API] Report archived successfully")
            except Exception as e:
                print(f"⚠️ [API] Warning: Failed to archive report: {e}")
        
        # Step 3: Process data and calculate excess charges
        print("🧮 [API] Step 3/3: Processing data and calculating excess charges...")
        
        # Create temporary file for processing
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx" if filename.endswith('.xlsx') else ".csv") as tmp:
            # Ensure we write bytes
            if hasattr(file_bytes, 'read'):
                file_bytes.seek(0)
                tmp.write(file_bytes.read())
            else:
                tmp.write(file_bytes)
            tmp_path = tmp.name
        
        try:
            print(f"📊 [API] Processing file: {tmp_path}")
            if filename.endswith('.xlsx'):
                df_raw = pd.read_excel(tmp_path, engine='openpyxl')
                print(f"🔍 [API] Excel columns found: {list(df_raw.columns)}")
                print(f"🔍 [API] First few rows:")
                print(df_raw.head().to_string())
            
            df = process_usage(tmp_path, allowances=None, delimiter=';', decimal=',')
            print(f"✅ [API] Data processed: {len(df)} properties found")
            print(f"🔍 [API] Processed DataFrame columns: {list(df.columns)}")
            
            properties = []
            book1_properties = []  # Properties in USER_ADDRESSES (book1)
            
            for _, row in df.iterrows():
                try:
                    property_data = {
                        "name": str(row.get('Property', 'Unknown')),
                        "elec_cost": float(row.get('Electricity Cost', 0)),
                        "water_cost": float(row.get('Water Cost', 0)),
                        "elec_extra": float(row.get('elec_extra', 0)),
                        "water_extra": float(row.get('water_extra', 0)),
                        "total_extra": float(row.get('Total Extra', 0)),
                        "allowance": float(row.get('Allowance', 0))
                    }
                    
                    # Add to all properties list
                    properties.append(property_data)
                    
                    # Check if this property is in book1 (USER_ADDRESSES)
                    if property_data["name"] in USER_ADDRESSES:
                        book1_properties.append(property_data)
                        
                except Exception as e:
                    print(f"⚠️ [API] Error processing row: {e}")
                    print(f"🔍 [API] Row data: {dict(row)}")
            
            print(f"📊 [API] Total properties processed: {len(properties)}")
            print(f"📊 [API] Book1 properties found: {len(book1_properties)}")
            print(f"📊 [API] Book1 property names: {[p['name'] for p in book1_properties[:5]]}...")
            
            # Use book1_properties for the response (filtered results)
            filtered_properties = book1_properties
            
            results_data = {
                "properties": filtered_properties,  # Only book1 properties
                "summary": {
                    "total_properties": len(filtered_properties),
                    "total_electricity_cost": sum(p["elec_cost"] for p in filtered_properties),
                    "total_water_cost": sum(p["water_cost"] for p in filtered_properties),
                    "total_electricity_extra": 0.0,  # No individual elec extra
                    "total_water_extra": 0.0,  # No individual water extra
                    "total_extra": sum(p["total_extra"] for p in filtered_properties),  # Total overages
                    "properties_with_overages": len([p for p in filtered_properties if p["total_extra"] > 0]),
                    "calculation_date": datetime.now().isoformat(),
                    "allowance_system": "room-based",
                    "filter_applied": "book1_only",  # Indicate filtering was applied
                    "total_properties_processed": len(properties)  # Show total processed vs filtered
                }
            }
            
            # Store results globally (in production, use Redis or database)
            calculation_results["latest"] = results_data
            
            print(f"✅ [API] Calculation completed successfully! Processed {len(properties)} properties")
            print(f"📊 [API] Summary: {len([p for p in filtered_properties if p['total_extra'] > 0])} book1 properties with total overages")
            print(f"📊 [API] Filtering: Showing {len(filtered_properties)} book1 properties out of {len(properties)} total")
            
            # Debug: Show what we're sending to frontend
            print(f"🔍 [API] First 3 book1 properties being sent to frontend:")
            for i, prop in enumerate(filtered_properties[:3]):
                print(f"  {i+1}. {prop}")
                print(f"    - elec_cost: {prop['elec_cost']}, water_cost: {prop['water_cost']}")
                print(f"    - elec_extra: {prop['elec_extra']}, water_extra: {prop['water_extra']}")
                print(f"    - allowance: {prop['allowance']}")
            
        except Exception as e:
            print(f"❌ [API] Calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return CalculationResponse(
                success=False,
                message="Calculation failed",
                error=str(e)
            )
        finally:
            # Clean up temporary file
            import os
            try:
                os.unlink(tmp_path)
                print("🧹 [API] Temporary file cleaned up")
            except:
                pass
        
        return CalculationResponse(
            success=True,
            message=f"Monthly calculation completed successfully using room-based allowances",
            data=results_data
        )
        
    except Exception as e:
        return CalculationResponse(
            success=False,
            message="Calculation failed",
            error=str(e)
        )

@app.get("/api/results/latest")
async def get_latest_results():
    """Get the most recent calculation results."""
    if "latest" not in calculation_results:
        raise HTTPException(status_code=404, detail="No calculation results available")
    
    return calculation_results["latest"]

@app.get("/api/export/csv")
async def export_csv():
    """Export the latest results as CSV."""
    if "latest" not in calculation_results:
        raise HTTPException(status_code=404, detail="No calculation results available")
    
    df = pd.DataFrame(calculation_results["latest"]["properties"])
    
    # Create CSV in memory
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    return JSONResponse(
        content={"csv_data": csv_buffer.getvalue()},
        headers={"Content-Disposition": f"attachment; filename=utility_report_{date.today().strftime('%Y%m%d')}.csv"}
    )

@app.get("/api/export/excel")
async def export_excel():
    """Export the latest results as Excel."""
    if "latest" not in calculation_results:
        raise HTTPException(status_code=404, detail="No calculation results available")
    
    df = pd.DataFrame(calculation_results["latest"]["properties"])
    
    # Create Excel in memory
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Utility Report', index=False)
        
        # Create summary sheet
        summary_data = {
            'Metric': ['Total Properties', 'Properties with Elec Overages', 'Properties with Water Overages',
                      'Total Electricity Cost', 'Total Water Cost', 'Total Electricity Extra', 'Total Water Extra'],
            'Value': [
                calculation_results["latest"]["summary"]["total_properties"],
                calculation_results["latest"]["summary"]["properties_with_elec_overages"],
                calculation_results["latest"]["summary"]["properties_with_water_overages"],
                calculation_results["latest"]["summary"]["total_electricity_cost"],
                calculation_results["latest"]["summary"]["total_water_cost"],
                calculation_results["latest"]["summary"]["total_electricity_extra"],
                calculation_results["latest"]["summary"]["total_water_extra"]
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
    
    excel_buffer.seek(0)
    
    return JSONResponse(
        content={"excel_data": excel_buffer.getvalue().hex()},  # Convert bytes to hex for JSON
        headers={"Content-Disposition": f"attachment; filename=utility_report_{date.today().strftime('%Y%m%d')}.xlsx"}
    )

@app.get("/api/configuration")
async def get_configuration():
    """Get current configuration settings."""
    from polaroo_process import ROOM_LIMITS, SPECIAL_LIMITS, ADDRESS_ROOM_MAPPING
    return {
        "allowance_system": "room-based",
        "room_limits": ROOM_LIMITS,
        "special_limits": SPECIAL_LIMITS,
        "address_room_mapping": ADDRESS_ROOM_MAPPING,
        "properties": USER_ADDRESSES
    }

# ---------- New Invoice Processing Endpoints ----------
@app.post("/api/process-invoices", response_model=CalculationResponse)
async def process_invoices_for_property(request: dict):
    """
    Process invoices for a single property using the new invoice-focused workflow.
    
    Expected request body:
    {
        "property_name": "Aribau 1º 1ª"
    }
    """
    try:
        property_name = request.get("property_name")
        if not property_name:
            raise HTTPException(status_code=400, detail="property_name is required")
        
        print(f"🚀 [API] Starting invoice processing for: {property_name}")
        
        # Import the new invoice processing function
        from src.polaroo_scrape import process_property_invoices
        
        # Process the property
        result = await process_property_invoices(property_name)
        
        return CalculationResponse(
            success=True,
            message=f"Invoice processing completed for {property_name}",
            data=result
        )
        
    except Exception as e:
        print(f"❌ [API] Invoice processing failed: {e}")
        return CalculationResponse(
            success=False,
            message="Invoice processing failed",
            error=str(e)
        )

@app.post("/api/process-first-10", response_model=CalculationResponse)
async def process_first_10_properties_endpoint():
    """
    Process invoices for the first 10 properties in Book 1.
    This is the main endpoint for testing the new workflow.
    """
    try:
        print("🚀 [API] Starting invoice processing for first 10 properties...")
        
        # Import the new invoice processing function
        from src.polaroo_scrape import process_first_10_properties
        
        # Process all properties
        results = await process_first_10_properties()
        
        # Calculate summary
        total_properties = len(results)
        successful_properties = len([r for r in results if 'error' not in r])
        total_cost = sum(r.get('total_cost', 0) for r in results)
        total_overuse = sum(r.get('overuse', 0) for r in results)
        
        summary = {
            "total_properties": total_properties,
            "successful_properties": successful_properties,
            "failed_properties": total_properties - successful_properties,
            "total_cost": total_cost,
            "total_overuse": total_overuse,
            "properties": results
        }
        
        return CalculationResponse(
            success=True,
            message=f"Processed {successful_properties}/{total_properties} properties successfully",
            data=summary
        )
        
    except Exception as e:
        print(f"❌ [API] First 10 properties processing failed: {e}")
        return CalculationResponse(
            success=False,
            message="First 10 properties processing failed",
            error=str(e)
        )

@app.post("/api/process-property", response_model=CalculationResponse)
async def process_single_property_endpoint(request: dict):
    """
    Process invoices for a single property and return results immediately.
    This allows for real-time display of results.
    """
    try:
        property_name = request.get("property_name")
        if not property_name:
            raise HTTPException(status_code=400, detail="property_name is required")
        
        print(f"🚀 [API] Starting invoice processing for: {property_name}")
        
        # Import the new invoice processing function
        from src.polaroo_scrape import process_property_invoices
        
        # Process the single property
        result = await process_property_invoices(property_name)
        
        return CalculationResponse(
            success=True,
            message=f"Invoice processing completed for {property_name}",
            data=result
        )
        
    except Exception as e:
        print(f"❌ [API] Single property processing failed: {e}")
        return CalculationResponse(
            success=False,
            message="Single property processing failed",
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
