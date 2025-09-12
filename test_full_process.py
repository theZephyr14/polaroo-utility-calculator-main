"""
Test the full invoice processing with user input for 2 months - VISIBLE BROWSER.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from src.polaroo_scrape import get_user_month_selection, _ensure_logged_in, _search_for_property, _get_invoice_table_data, analyze_invoices_with_cohere, _download_invoice_files
from src.config import POLAROO_EMAIL, POLAROO_PASSWORD

async def test_full_process_visible():
    """Test the full invoice processing with VISIBLE browser."""
    print("🚀 [START] Testing full invoice processing with VISIBLE browser...")
    print("This will ask you for 2 months and process invoices for a single property.")
    
    # Get user input for 2 months
    print("\n📅 [INPUT] Please enter the 2 months you want to calculate for:")
    start_month, end_month = get_user_month_selection()
    
    print(f"\n📅 [SELECTED] Processing invoices for: {start_month} to {end_month}")
    
    # Test with a single property
    property_name = "Aribau 1º 1ª"
    
    print(f"\n🏠 [PROPERTY] Processing: {property_name}")
    print("This will open a VISIBLE browser window so you can see what's happening...")
    
    # Set up browser with visible window
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
            await _ensure_logged_in(page)
            
            # 2) We're already on the accounting dashboard - ready to search for invoices
            print("✅ [ACCOUNTING] Ready to search for invoices on accounting dashboard")
            
            # 3) Search for property
            await _search_for_property(page, property_name)
            
            # 4) Extract table data
            invoices = await _get_invoice_table_data(page)
            
            if not invoices:
                print("❌ [ERROR] No invoice data found")
                return None
            
            print(f"📊 [INVOICES] Found {len(invoices)} total invoices")
            
            # 5) Use LLM to analyze ALL invoices and select the right ones
            print("🤖 [LLM] Analyzing all invoices with Cohere...")
            analysis = analyze_invoices_with_cohere(invoices, start_month, end_month)
            
            # 6) Download selected invoices using column 1 (download button)
            downloaded_files = await _download_invoice_files(page, analysis['selected_invoices'], property_name)
            
            # 7) Calculate overuse (using existing logic)
            from src.polaroo_process import ADDRESS_ROOM_MAPPING, ROOM_LIMITS, SPECIAL_LIMITS
            
            room_count = ADDRESS_ROOM_MAPPING.get(property_name, 1)
            allowance = SPECIAL_LIMITS.get(property_name, ROOM_LIMITS.get(room_count, 50))
            
            # Double allowances for 2-month period
            allowance *= 2
            
            total_cost = analysis['total_all']
            overuse = max(0, total_cost - allowance)
            
            result = {
                'property_name': property_name,
                'date_range': f"{start_month} to {end_month}",
                'room_count': room_count,
                'allowance': allowance,
                'total_electricity': analysis['total_electricity'],
                'total_water': analysis['total_water'],
                'total_cost': total_cost,
                'overuse': overuse,
                'selected_invoices': analysis['selected_invoices'],
                'downloaded_files': downloaded_files,
                'llm_reasoning': analysis['reasoning']
            }
            
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
            
            print("\n🎯 [TEST] Browser will stay open for 30 seconds so you can see the results...")
            await page.wait_for_timeout(30000)
            
            return result
            
        except Exception as e:
            print(f"❌ [ERROR] Invoice processing failed: {e}")
            await page.screenshot(path="_debug/error_visible.png")
            print("📸 [DEBUG] Error screenshot saved to _debug/error_visible.png")
            return None
        finally:
            await context.close()

if __name__ == "__main__":
    print("🧪 [TEST] Full invoice processing test with VISIBLE browser...")
    print("This will ask you for 2 months and process invoices with a visible browser window.")
    
    result = asyncio.run(test_full_process_visible())
    
    if result:
        print("\n✅ [COMPLETE] Test completed successfully!")
    else:
        print("\n❌ [COMPLETE] Test failed!")
