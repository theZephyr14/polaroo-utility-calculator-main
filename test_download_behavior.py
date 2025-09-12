#!/usr/bin/env python3
"""
Test script to see what the download button actually does
"""
import asyncio
from playwright.async_api import async_playwright
from src.config import POLAROO_EMAIL, POLAROO_PASSWORD

async def test_download_behavior():
    """Test what happens when we click a download button"""
    async with async_playwright() as p:
        # Launch browser
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
                
                # Listen for different events
                print("👂 [LISTEN] Listening for events...")
                
                # Listen for new page
                new_page_promise = context.wait_for_event("page", timeout=5000)
                
                # Listen for download
                download_promise = page.expect_download(timeout=5000)
                
                # Click the button
                await download_buttons[0].click()
                print("✅ [CLICKED] Download button clicked")
                
                # Wait a bit to see what happens
                await page.wait_for_timeout(3000)
                
                # Check what events fired
                try:
                    new_page = await asyncio.wait_for(new_page_promise, timeout=1)
                    print(f"📄 [NEW PAGE] New page opened: {new_page.url}")
                except asyncio.TimeoutError:
                    print("❌ [NEW PAGE] No new page opened")
                
                try:
                    download = await asyncio.wait_for(download_promise, timeout=1)
                    print(f"📥 [DOWNLOAD] Download started: {download.suggested_filename}")
                except asyncio.TimeoutError:
                    print("❌ [DOWNLOAD] No download started")
                
                # Check current URL
                print(f"🌐 [URL] Current page URL: {page.url}")
                
                # Check if we're still on the same page
                await page.wait_for_timeout(2000)
                print(f"🌐 [URL] Final page URL: {page.url}")
                
            else:
                print("❌ [ERROR] No download buttons found")
                
        except Exception as e:
            print(f"❌ [ERROR] Test failed: {e}")
            await page.screenshot(path="_debug/download_test_error.png")
        
        finally:
            print("🔄 [CLEANUP] Closing browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_download_behavior())
