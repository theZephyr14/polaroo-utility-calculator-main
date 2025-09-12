#!/usr/bin/env python3
"""
Test script to run actual invoice processing with a single property.
This will test the full workflow including browser automation.
"""

import asyncio
from src.polaroo_scrape import process_property_invoices, get_user_month_selection_auto
from playwright.async_api import async_playwright

async def test_single_property_visible():
    """Test invoice processing with visible browser window."""
    print("🧪 [TEST] Testing invoice processing with visible browser...")
    
    # Test with a simple property
    property_name = "Aribau 1º 1ª"  # 1 room property
    
    # Auto-select last 2 months for testing
    start_month, end_month = get_user_month_selection_auto()
    
    print(f"Testing property: {property_name}")
    print(f"Date range: {start_month} to {end_month}")
    print("This will open a VISIBLE browser window so you can see what's happening...")
    
    # Import the necessary modules
    from pathlib import Path
    from src.config import POLAROO_EMAIL, POLAROO_PASSWORD
    
    user_data = str(Path("./.chrome-profile").resolve())
    Path(user_data).mkdir(exist_ok=True)
    Path("_debug").mkdir(exist_ok=True)
    Path("_debug/downloads").mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("🌐 [BROWSER] Launching VISIBLE browser...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=False,  # VISIBLE BROWSER
            slow_mo=1000,    # Slow down actions so you can see them
            viewport={"width": 1366, "height": 900},
            args=[
                "--disable-gpu",
                "--no-sandbox", 
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-plugins",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
            accept_downloads=True,
            ignore_https_errors=True,
        )
        context.set_default_timeout(120_000)
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # 1) Login
            print("🔐 [LOGIN] Starting login process...")
            await page.goto("https://app.polaroo.com/login")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            
            if "login" in page.url.lower():
                print("🔐 [LOGIN] Login page detected, proceeding with authentication...")
                await page.get_by_role("heading", name="Sign in").wait_for(timeout=30_000)
                
                print("📧 [LOGIN] Filling email...")
                await page.get_by_placeholder("Email").fill(POLAROO_EMAIL or "")
                print("🔑 [LOGIN] Filling password...")
                await page.get_by_placeholder("Password").fill(POLAROO_PASSWORD or "")
                await page.wait_for_timeout(2000)
                
                print("🖱️ [LOGIN] Clicking Sign in button...")
                await page.get_by_role("button", name="Sign in").click()
                await page.wait_for_load_state("domcontentloaded")
                print("✅ [LOGIN] Sign in button clicked, waiting for redirect...")
            
            # Wait 5 seconds after login, then navigate to accounting dashboard
            print("⏳ [WAIT] Waiting 5 seconds after login...")
            await page.wait_for_timeout(5_000)
            
            # Navigate directly to accounting dashboard
            accounting_url = "https://app.polaroo.com/dashboard/accounting"
            print(f"🌐 [NAVIGATE] Going to accounting dashboard: {accounting_url}")
            await page.goto(accounting_url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("networkidle")
            print("✅ [NAVIGATE] Successfully reached accounting dashboard")
            
            # Wait 10 seconds after reaching accounting dashboard
            print("⏳ [WAIT] Waiting 10 seconds after reaching accounting dashboard...")
            await page.wait_for_timeout(10_000)
            print("✅ [ACCOUNTING] Ready to search for invoices on accounting dashboard")
            
            # Search for property
            print(f"🔍 [SEARCH] Searching for property: {property_name}")
            search_input = page.locator('input[type="text"], input[placeholder*="search" i], input[placeholder*="Search" i]').first
            if await search_input.count() == 0:
                search_input = page.locator('input').first
            
            await search_input.click()
            await search_input.fill("")  # Clear existing text
            await search_input.fill(property_name)
            
            # Wait exactly 5 seconds after searching as requested
            print("⏳ [SEARCH] Waiting 5 seconds for search results to load...")
            await page.wait_for_timeout(5000)
            
            print(f"✅ [SEARCH] Successfully searched for: {property_name}")
            
            # Extract table data
            print("📊 [TABLE] Extracting invoice table data...")
            await page.wait_for_timeout(2000)
            
            # Find the table rows
            rows = await page.locator('table tbody tr, .table tbody tr, [role="row"]').all()
            print(f"🔍 [TABLE] Found {len(rows)} table rows")
            
            if rows:
                print("✅ [TABLE] Table data found! Let's examine the first few rows...")
                for i, row in enumerate(rows[:3]):  # Show first 3 rows
                    try:
                        cells = await row.locator('td, th').all()
                        if cells:
                            cell_texts = []
                            for cell in cells:
                                text = await cell.text_content()
                                cell_texts.append(text.strip() if text else "")
                            print(f"Row {i}: {cell_texts[:5]}...")  # Show first 5 columns
                    except Exception as e:
                        print(f"Error reading row {i}: {e}")
            else:
                print("❌ [TABLE] No table rows found")
                # Take a screenshot to see what's on the page
                await page.screenshot(path="_debug/visible_test.png")
                print("📸 [DEBUG] Screenshot saved to _debug/visible_test.png")
            
            print("\n🎯 [TEST] Browser will stay open for 30 seconds so you can see the page...")
            await page.wait_for_timeout(30000)  # Keep browser open for 30 seconds
            
            return {"status": "completed", "rows_found": len(rows)}
            
        except Exception as e:
            print(f"❌ [ERROR] Test failed: {e}")
            await page.screenshot(path="_debug/error_visible.png")
            print("📸 [DEBUG] Error screenshot saved to _debug/error_visible.png")
            return None
        finally:
            await context.close()

async def test_single_property():
    """Test invoice processing for a single property."""
    print("🧪 [TEST] Testing invoice processing for a single property...")
    
    # Test with a simple property
    property_name = "Aribau 1º 1ª"  # 1 room property
    
    # Auto-select last 2 months for testing
    start_month, end_month = get_user_month_selection_auto()
    
    print(f"Testing property: {property_name}")
    print(f"Date range: {start_month} to {end_month}")
    print("This will open a browser and attempt to process invoices...")
    
    try:
        result = await process_property_invoices(property_name, start_month, end_month)
        
        print("\n✅ [SUCCESS] Invoice processing completed!")
        print(f"Property: {result['property_name']}")
        print(f"Date range: {result['date_range']}")
        print(f"Room count: {result['room_count']}")
        print(f"Allowance: €{result['allowance']:.2f}")
        print(f"Total electricity: €{result['total_electricity']:.2f}")
        print(f"Total water: €{result['total_water']:.2f}")
        print(f"Total cost: €{result['total_cost']:.2f}")
        print(f"Overuse: €{result['overuse']:.2f}")
        print(f"Selected invoices: {len(result['selected_invoices'])}")
        print(f"Downloaded files: {len(result['downloaded_files'])}")
        print(f"LLM reasoning: {result['llm_reasoning']}")
        
        return result
        
    except Exception as e:
        print(f"❌ [ERROR] Invoice processing failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 [START] Testing invoice processing with VISIBLE browser...")
    print("Note: This will open a VISIBLE browser window so you can see what's happening.")
    print("The browser will stay open for 30 seconds after the test completes.")
    
    # Run the visible test
    result = asyncio.run(test_single_property_visible())
    
    if result:
        print(f"\n✅ [COMPLETE] Test completed successfully!")
        print(f"Status: {result['status']}")
        print(f"Table rows found: {result['rows_found']}")
    else:
        print("\n❌ [COMPLETE] Test failed!")
