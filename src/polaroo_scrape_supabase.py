"""
Polaroo scraping with full Supabase integration.

This module provides the complete invoice processing workflow using
the new Supabase database system for all data storage and management.
"""

import asyncio
import re
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import quote
from typing import List, Dict, Any, Optional, Tuple

import requests
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from src.config import (
    POLAROO_EMAIL,
    POLAROO_PASSWORD,
    COHERE_API_KEY,
)
from src.supabase_client import (
    get_supabase_manager, 
    ProcessingSession, 
    PropertyResult, 
    Invoice,
    Property
)

LOGIN_URL = "https://app.polaroo.com/login"

# ---------- global waits ----------
WAIT_MS = 5_000          # minimum wait after each step
MAX_WAIT_LOOPS = 20       # 20 * 500ms = 30s for dashboard detection

# ---------- utils ----------
def _infer_content_type(filename: str) -> str:
    """Infer content type from filename."""
    name = filename.lower()
    if name.endswith(".csv"):
        return "text/csv"
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/octet-stream"

def _clean_property_name(property_name: str) -> str:
    """Clean property name for file storage."""
    # Replace special characters that cause issues
    cleaned = re.sub(r'[ºª]', '', property_name)
    cleaned = re.sub(r'[^a-zA-Z0-9._/-]', '_', cleaned)
    cleaned = re.sub(r'_+', '_', cleaned)
    return cleaned

async def _ensure_logged_in(page) -> bool:
    """Ensure user is logged in to Polaroo."""
    try:
        print("🚀 [LOGIN] Starting login process...")
        
        # Navigate to login page
        await page.goto(LOGIN_URL)
        await page.wait_for_timeout(WAIT_MS)
        
        # Check if already logged in (redirected to dashboard)
        current_url = page.url
        if "dashboard" in current_url:
            print("✅ [LOGIN] Already logged in, redirected to dashboard")
            return True
        
        # Fill login form
        print("📝 [LOGIN] Filling login form...")
        await page.fill('input[name="email"]', POLAROO_EMAIL)
        await page.fill('input[name="password"]', POLAROO_PASSWORD)
        
        # Submit form
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(WAIT_MS)
        
        # Wait for redirect to dashboard
        for _ in range(MAX_WAIT_LOOPS):
            current_url = page.url
            if "dashboard" in current_url:
                print("✅ [LOGIN] Successfully logged in")
                return True
            await page.wait_for_timeout(500)
        
        print("❌ [LOGIN] Login failed - no redirect to dashboard")
        return False
        
    except Exception as e:
        print(f"❌ [LOGIN] Login error: {e}")
        return False

async def _search_for_property(page, property_name: str) -> bool:
    """Search for a specific property in the accounting dashboard."""
    try:
        print(f"🔍 [SEARCH] Searching for property: {property_name}")
        
        # Navigate to accounting dashboard
        await page.goto("https://app.polaroo.com/dashboard/accounting")
        await page.wait_for_timeout(WAIT_MS)
        
        # Look for search input
        search_input = page.locator('input[placeholder*="search"], input[placeholder*="Search"]').first
        if await search_input.count() > 0:
            await search_input.fill(property_name)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(WAIT_MS)
        
        print(f"✅ [SEARCH] Successfully searched for: {property_name}")
        return True
        
    except Exception as e:
        print(f"❌ [SEARCH] Search error for {property_name}: {e}")
        return False

async def _get_invoice_table_data(page) -> List[Dict[str, Any]]:
    """Extract invoice table data from the current page."""
    try:
        print("📊 [TABLE] Extracting invoice table data...")
        
        # Wait for table to load
        await page.wait_for_selector('table, .table, [role="table"]', timeout=10000)
        
        # Extract table data
        table_data = await page.evaluate("""
            () => {
                const tables = document.querySelectorAll('table, .table, [role="table"]');
                const data = [];
                
                for (const table of tables) {
                    const rows = table.querySelectorAll('tr');
                    const headers = [];
                    
                    // Get headers from first row
                    if (rows.length > 0) {
                        const headerRow = rows[0];
                        const headerCells = headerRow.querySelectorAll('th, td');
                        for (const cell of headerCells) {
                            headers.push(cell.textContent.trim());
                        }
                    }
                    
                    // Extract data from remaining rows
                    for (let i = 1; i < rows.length; i++) {
                        const row = rows[i];
                        const cells = row.querySelectorAll('td, th');
                        const rowData = {};
                        
                        for (let j = 0; j < cells.length && j < headers.length; j++) {
                            const cellText = cells[j].textContent.trim();
                            rowData[headers[j]] = cellText;
                        }
                        
                        if (Object.keys(rowData).length > 0) {
                            data.push(rowData);
                        }
                    }
                }
                
                return data;
            }
        """)
        
        print(f"✅ [TABLE] Extracted {len(table_data)} invoice records")
        return table_data
        
    except Exception as e:
        print(f"❌ [TABLE] Error extracting table data: {e}")
        return []

async def analyze_invoices_with_cohere(invoices: List[Dict[str, Any]], 
                                     start_date: str, end_date: str) -> Dict[str, Any]:
    """Analyze invoices using Cohere AI."""
    try:
        print("🤖 [COHERE] Analyzing invoices with LLM...")
        
        # Prepare data for Cohere
        invoice_text = ""
        for i, invoice in enumerate(invoices, 1):
            invoice_text += f"Row {i}: {invoice}\n"
        
        prompt = f"""
        Analyze these utility invoices for the period {start_date} to {end_date}.
        
        IMPORTANT: This is a 2-MONTH period calculation. You need to find:
        - 2 ELECTRICITY bills (one for each month)
        - 1 WATER bill (covers both months, as water is billed every 2 months)
        
        For each invoice, determine:
        1. Service type (electricity, water, gas)
        2. Whether it should be included in the calculation
        3. The amount in euros
        4. The date range it covers
        
        SELECTION RULES:
        - ELECTRICITY: Select exactly 2 bills (one per month in the period)
        - WATER: Select exactly 1 bill that covers the entire 2-month period
        - GAS: Ignore gas bills for this calculation
        - Only select bills that fall within the date range {start_date} to {end_date}
        
        Return a JSON response with:
        {{
            "selected_electricity_rows": [list of row numbers for electricity bills],
            "selected_water_rows": [list of row numbers for water bills],
            "total_electricity_cost": sum of selected electricity bills,
            "total_water_cost": sum of selected water bills,
            "reasoning": "explanation of selections and date ranges",
            "missing_bills": "any missing bills for the period"
        }}
        
        Invoices:
        {invoice_text}
        """
        
        # Call Cohere API
        headers = {
            "Authorization": f"Bearer {COHERE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "command",
            "message": prompt,
            "max_tokens": 1000,
            "temperature": 0.1
        }
        
        response = requests.post(
            "https://api.cohere.ai/v1/chat",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            llm_response = result.get("text", "{}")
            
            # Parse JSON response
            import json
            try:
                parsed = json.loads(llm_response)
                print(f"✅ [COHERE] LLM Response: {parsed}")
                return parsed
            except json.JSONDecodeError:
                print(f"⚠️ [COHERE] Failed to parse JSON response: {llm_response}")
                return {
                    "selected_electricity_rows": [],
                    "selected_water_rows": [],
                    "reasoning": "Failed to parse LLM response",
                    "missing_bills": "Unknown"
                }
        else:
            print(f"❌ [COHERE] API error: {response.status_code} - {response.text}")
            return {
                "selected_electricity_rows": [],
                "selected_water_rows": [],
                "reasoning": "API error",
                "missing_bills": "Unknown"
            }
            
    except Exception as e:
        print(f"❌ [COHERE] Error analyzing invoices: {e}")
        return {
            "selected_electricity_rows": [],
            "selected_water_rows": [],
            "reasoning": f"Error: {str(e)}",
            "missing_bills": "Unknown"
        }

async def _download_invoice_files(page, invoices: List[Dict[str, Any]], 
                                 property_name: str, property_result_id: str) -> int:
    """Download invoice PDF files and store in Supabase."""
    try:
        print(f"📥 [DOWNLOAD] Downloading {len(invoices)} invoices for {property_name}")
        
        manager = get_supabase_manager()
        downloaded_count = 0
        
        for i, invoice in enumerate(invoices, 1):
            try:
                print(f"📥 [DOWNLOAD] Downloading invoice {i}: {invoice.get('Invoice Number', 'Unknown')}")
                
                # Look for download button
                download_buttons = page.locator('button:has-text("Download"), a:has-text("Download"), [title*="Download"]')
                if await download_buttons.count() > i:
                    # Click download button
                    await download_buttons.nth(i - 1).click()
                    await page.wait_for_timeout(2000)
                    
                    # Wait for new tab to open
                    pages = page.context.pages
                    if len(pages) > 1:
                        pdf_page = pages[-1]
                        await pdf_page.wait_for_load_state()
                        
                        # Get PDF content
                        pdf_content = await pdf_page.content()
                        pdf_bytes = pdf_content.encode('utf-8')
                        
                        # Generate filename
                        invoice_number = invoice.get('Invoice Number', f'invoice_{i}')
                        clean_property = _clean_property_name(property_name)
                        timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
                        filename = f"invoice_{clean_property}_{invoice_number}_{timestamp}.pdf"
                        
                        # Upload to Supabase Storage
                        file_path = manager.upload_file(
                            file_bytes=pdf_bytes,
                            property_name=property_name,
                            invoice_number=invoice_number,
                            file_name=filename
                        )
                        
                        if file_path:
                            # Create invoice record
                            invoice_record = Invoice(
                                property_result_id=property_result_id,
                                invoice_number=invoice_number,
                                service_type=invoice.get('Service', 'unknown'),
                                amount=float(invoice.get('Amount', 0).replace('€', '').replace(',', '.')),
                                is_downloaded=True,
                                file_path=file_path,
                                file_size=len(pdf_bytes)
                            )
                            
                            invoice_id = manager.create_invoice(invoice_record)
                            if invoice_id:
                                downloaded_count += 1
                                print(f"✅ [DOWNLOAD] Successfully processed invoice {i}")
                            else:
                                print(f"❌ [DOWNLOAD] Failed to create invoice record {i}")
                        else:
                            print(f"❌ [DOWNLOAD] Failed to upload invoice {i}")
                        
                        # Close PDF tab
                        await pdf_page.close()
                    else:
                        print(f"❌ [DOWNLOAD] No new tab opened for invoice {i}")
                else:
                    print(f"❌ [DOWNLOAD] No download button found for invoice {i}")
                    
            except Exception as e:
                print(f"❌ [DOWNLOAD] Error downloading invoice {i}: {e}")
                continue
        
        print(f"✅ [DOWNLOAD] Downloaded {downloaded_count}/{len(invoices)} invoices")
        return downloaded_count
        
    except Exception as e:
        print(f"❌ [DOWNLOAD] Error in download process: {e}")
        return 0

async def process_property_invoices(property_name: str, start_date: str = None, 
                                  end_date: str = None, session_id: str = None) -> Dict[str, Any]:
    """Process invoices for a single property using Supabase."""
    try:
        print(f"🏠 [PROPERTY] Processing: {property_name}")
        
        manager = get_supabase_manager()
        
        # Get property information
        property_info = manager.get_property_by_name(property_name)
        if not property_info:
            print(f"❌ [PROPERTY] Property not found: {property_name}")
            return {"error": f"Property not found: {property_name}"}
        
        # Create property result
        property_result = PropertyResult(
            session_id=session_id,
            property_id=property_info.id,
            property_name=property_name,
            room_count=property_info.room_count,
            allowance=manager.get_property_allowance(property_name),
            processing_status="processing"
        )
        
        property_result_id = manager.create_property_result(property_result)
        if not property_result_id:
            print(f"❌ [PROPERTY] Failed to create property result for {property_name}")
            return {"error": "Failed to create property result"}
        
        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Login
                if not await _ensure_logged_in(page):
                    raise Exception("Failed to login")
                
                # Search for property
                if not await _search_for_property(page, property_name):
                    raise Exception("Failed to search for property")
                
                # Get invoice data
                invoices = await _get_invoice_table_data(page)
                if not invoices:
                    raise Exception("No invoice data found")
                
                # Analyze with Cohere
                analysis = await analyze_invoices_with_cohere(invoices, start_date or "2025-01", end_date or "2025-12")
                
                # Calculate costs
                total_electricity = 0.0
                total_water = 0.0
                selected_invoices = []
                
                for i, invoice in enumerate(invoices, 1):
                    if i in analysis.get("selected_electricity_rows", []):
                        amount = float(invoice.get('Amount', '0').replace('€', '').replace(',', '.'))
                        total_electricity += amount
                        selected_invoices.append(invoice)
                    elif i in analysis.get("selected_water_rows", []):
                        amount = float(invoice.get('Amount', '0').replace('€', '').replace(',', '.'))
                        total_water += amount
                        selected_invoices.append(invoice)
                
                total_cost = total_electricity + total_water
                overuse = max(0.0, total_cost - property_result.allowance)
                
                # Update property result
                updates = {
                    "total_electricity_cost": total_electricity,
                    "total_water_cost": total_water,
                    "total_cost": total_cost,
                    "overuse": overuse,
                    "selected_invoices_count": len(selected_invoices),
                    "llm_reasoning": analysis.get("reasoning", ""),
                    "processing_status": "completed"
                }
                
                manager.update_property_result(property_result_id, updates)
                
                # Download selected invoices
                downloaded_count = await _download_invoice_files(page, selected_invoices, property_name, property_result_id)
                
                # Update download count
                manager.update_property_result(property_result_id, {"downloaded_files_count": downloaded_count})
                
                # Return results
                result = {
                    "property_name": property_name,
                    "room_count": property_info.room_count,
                    "allowance": property_result.allowance,
                    "total_electricity_cost": total_electricity,
                    "total_water_cost": total_water,
                    "total_cost": total_cost,
                    "overuse": overuse,
                    "selected_invoices_count": len(selected_invoices),
                    "downloaded_files_count": downloaded_count,
                    "llm_reasoning": analysis.get("reasoning", ""),
                    "missing_bills": analysis.get("missing_bills", "")
                }
                
                print(f"✅ [PROPERTY] Completed processing: {property_name}")
                return result
                
            finally:
                await browser.close()
                
    except Exception as e:
        print(f"❌ [PROPERTY] Error processing {property_name}: {e}")
        
        # Update property result with error
        if 'property_result_id' in locals():
            manager.update_property_result(property_result_id, {
                "processing_status": "failed",
                "error_message": str(e)
            })
        
        return {"error": str(e)}

async def process_multiple_properties(property_names: List[str], start_date: str = None, 
                                   end_date: str = None) -> Dict[str, Any]:
    """Process invoices for multiple properties."""
    try:
        print(f"🚀 [BATCH] Processing {len(property_names)} properties...")
        
        manager = get_supabase_manager()
        
        # Create processing session
        session = ProcessingSession(
            session_name=f"Batch processing {len(property_names)} properties",
            start_date=datetime.strptime(start_date, "%Y-%m") if start_date else date.today(),
            end_date=datetime.strptime(end_date, "%Y-%m") if end_date else date.today(),
            status="processing",
            total_properties=len(property_names)
        )
        
        session_id = manager.create_processing_session(session)
        if not session_id:
            return {"error": "Failed to create processing session"}
        
        # Process each property
        results = []
        successful_count = 0
        failed_count = 0
        total_cost = 0.0
        total_overuse = 0.0
        
        for property_name in property_names:
            result = await process_property_invoices(property_name, start_date, end_date, session_id)
            results.append(result)
            
            if "error" not in result:
                successful_count += 1
                total_cost += result.get("total_cost", 0)
                total_overuse += result.get("overuse", 0)
            else:
                failed_count += 1
        
        # Update session
        manager.update_processing_session(session_id, {
            "status": "completed",
            "successful_properties": successful_count,
            "failed_properties": failed_count,
            "total_cost": total_cost,
            "total_overuse": total_overuse,
            "completed_at": datetime.now()
        })
        
        return {
            "session_id": session_id,
            "total_properties": len(property_names),
            "successful_properties": successful_count,
            "failed_properties": failed_count,
            "total_cost": total_cost,
            "total_overuse": total_overuse,
            "properties": results
        }
        
    except Exception as e:
        print(f"❌ [BATCH] Error in batch processing: {e}")
        return {"error": str(e)}

# Legacy compatibility functions
async def get_user_month_selection() -> Tuple[str, str]:
    """Get user month selection (legacy compatibility)."""
    # This would normally prompt the user, but for now return defaults
    return "2025-05", "2025-06"

async def process_first_10_properties() -> List[Dict[str, Any]]:
    """Process the first 10 properties (legacy compatibility)."""
    manager = get_supabase_manager()
    properties = manager.get_all_properties()[:10]
    
    property_names = [prop.name for prop in properties]
    result = await process_multiple_properties(property_names)
    
    return result.get("properties", [])

# Main execution function
async def main():
    """Main execution function for testing."""
    # Test with a single property
    result = await process_property_invoices("Aribau 1º 1ª")
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
