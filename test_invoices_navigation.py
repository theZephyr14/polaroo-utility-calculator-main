"""
Test script to check if we can navigate to the invoices page.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from src.config import POLAROO_EMAIL, POLAROO_PASSWORD

async def test_invoices_navigation():
    """Test navigation to invoices page."""
    print("🔍 [TEST] Testing invoices page navigation...")
    
    user_data = str(Path("./.chrome-profile").resolve())
    Path(user_data).mkdir(exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=False,  # VISIBLE BROWSER
            slow_mo=1000,    # Slow down actions
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
            ],
            ignore_https_errors=True,
        )
        context.set_default_timeout(30_000)
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # 1) Login first
            print("🔐 [LOGIN] Logging in...")
            await page.goto("https://app.polaroo.com/login")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            
            if "login" in page.url.lower():
                print("🔐 [LOGIN] Filling credentials...")
                await page.locator('#email').fill(POLAROO_EMAIL or "")
                await page.locator('#password').fill(POLAROO_PASSWORD or "")
                await page.get_by_role("button", name="Sign in").click()
                await page.wait_for_load_state("domcontentloaded")
                print("✅ [LOGIN] Login completed")
            
            # 2) Wait and go to accounting dashboard
            print("⏳ [WAIT] Waiting 5 seconds...")
            await page.wait_for_timeout(5000)
            
            print("🌐 [NAVIGATE] Going to accounting dashboard...")
            await page.goto("https://app.polaroo.com/dashboard/accounting")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("networkidle")
            print(f"✅ [ACCOUNTING] Current URL: {page.url}")
            
            # 3) Try to navigate to invoices
            print("📋 [INVOICES] Trying to navigate to invoices page...")
            invoices_url = "https://app.polaroo.com/dashboard/accounting/invoices"
            print(f"🌐 [INVOICES] Going to: {invoices_url}")
            await page.goto(invoices_url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("networkidle")
            
            print(f"✅ [INVOICES] Final URL: {page.url}")
            
            # Check if we're actually on the invoices page
            page_text = await page.text_content('body')
            if 'invoices' in page_text.lower() or 'bills' in page_text.lower():
                print("✅ [INVOICES] Successfully reached invoices page!")
            else:
                print("❌ [INVOICES] Not on invoices page - checking what's there...")
                print(f"🔍 [DEBUG] Page contains: {page_text[:500]}...")
            
            # Take screenshot
            await page.screenshot(path="_debug/invoices_navigation.png")
            print("📸 [DEBUG] Screenshot saved to _debug/invoices_navigation.png")
            
            # 4) Try alternative navigation methods
            print("\n🔍 [ALTERNATIVE] Trying to find invoices link in sidebar...")
            
            # Look for sidebar navigation
            sidebar_links = await page.locator('nav a, [role="navigation"] a, .sidebar a').all()
            print(f"🔍 [SIDEBAR] Found {len(sidebar_links)} sidebar links")
            
            for i, link in enumerate(sidebar_links[:10]):  # Check first 10 links
                try:
                    text = await link.text_content()
                    href = await link.get_attribute('href')
                    print(f"  Link {i}: '{text}' -> {href}")
                except:
                    pass
            
            # Look for invoices-related text
            print("\n🔍 [SEARCH] Looking for invoices-related elements...")
            invoices_elements = await page.locator('text=/invoice|bill/i').all()
            print(f"🔍 [SEARCH] Found {len(invoices_elements)} elements with 'invoice' or 'bill'")
            
            for i, elem in enumerate(invoices_elements[:5]):  # Check first 5
                try:
                    text = await elem.text_content()
                    print(f"  Element {i}: '{text[:100]}...'")
                except:
                    pass
            
            print("\n🎯 [TEST] Browser will stay open for 30 seconds...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"❌ [ERROR] Test failed: {e}")
            try:
                await page.screenshot(path="_debug/invoices_error.png")
                print("📸 [DEBUG] Error screenshot saved to _debug/invoices_error.png")
            except:
                pass
        finally:
            await context.close()

if __name__ == "__main__":
    print("🚀 [START] Testing invoices navigation...")
    asyncio.run(test_invoices_navigation())
