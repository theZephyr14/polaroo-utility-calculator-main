#!/usr/bin/env python3
"""
Simple test to verify the new download approach
"""
import asyncio
from playwright.async_api import async_playwright
from src.config import POLAROO_EMAIL, POLAROO_PASSWORD

async def test_simple_download():
    """Test the new download approach"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login
            print("🔐 [LOGIN] Logging in...")
            await page.goto("https://app.polaroo.com/login")
            await page.wait_for_timeout(2000)
            
            await page.fill('input[name="email"]', POLAROO_EMAIL)
            await page.fill('input[name="password"]', POLAROO_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            
            # Go to accounting
            print("📊 [NAVIGATE] Going to accounting...")
            await page.goto("https://app.polaroo.com/dashboard/accounting")
            await page.wait_for_timeout(10000)
            
            # Search for property
            print("🔍 [SEARCH] Searching for property...")
            await page.fill('input[placeholder*="Search"]', "Aribau 1º 1ª")
            await page.wait_for_timeout(5000)
            
            # Get first download button
            print("🔍 [FIND] Looking for download buttons...")
            download_buttons = await page.locator('button[title*="Download"], a[title*="Download"]').all()
            print(f"📊 [FOUND] Found {len(download_buttons)} download buttons")
            
            if download_buttons:
                print("🖱️ [CLICK] Clicking first download button...")
                
                # Get initial page count
                initial_pages = len(context.pages)
                print(f"📊 [PAGES] Initial page count: {initial_pages}")
                
                # Click the download button (this opens PDF in new tab)
                await download_buttons[0].click()
                print("🖱️ [DOWNLOAD] Clicked download button, waiting for PDF tab...")
                
                # Wait for new page to appear (check every 500ms for 10 seconds)
                new_page = None
                for attempt in range(20):  # 20 attempts * 500ms = 10 seconds
                    await page.wait_for_timeout(500)
                    current_pages = len(context.pages)
                    print(f"📊 [PAGES] Attempt {attempt + 1}: {current_pages} pages")
                    
                    if current_pages > initial_pages:
                        new_page = context.pages[-1]  # Get the newest page
                        print(f"✅ [NEW PAGE] New tab detected: {new_page.url}")
                        break
                
                if not new_page:
                    print("❌ [ERROR] No new tab opened within 10 seconds")
                else:
                    print("✅ [SUCCESS] New tab detected successfully!")
                    await new_page.close()
                
            else:
                print("❌ [ERROR] No download buttons found")
                
        except Exception as e:
            print(f"❌ [ERROR] Test failed: {e}")
            await page.screenshot(path="_debug/simple_download_test_error.png")
        
        finally:
            print("🔄 [CLEANUP] Closing browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_simple_download())
