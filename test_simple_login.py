"""
Simple test to just try logging in and see what happens.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from src.config import POLAROO_EMAIL, POLAROO_PASSWORD

async def test_simple_login():
    """Just try to login and see what happens."""
    print("🔐 [SIMPLE] Testing simple login...")
    
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
            print("🌐 [SIMPLE] Going to login page...")
            await page.goto("https://app.polaroo.com/login")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)
            
            print("📸 [SIMPLE] Taking screenshot...")
            await page.screenshot(path="_debug/simple_login.png")
            print("✅ [SIMPLE] Screenshot saved to _debug/simple_login.png")
            
            print("🔍 [SIMPLE] Looking for email field...")
            email_field = page.locator('#email').first
            if await email_field.count() > 0:
                print("✅ [SIMPLE] Found email field by ID")
            else:
                email_field = page.get_by_placeholder("Email").first
                if await email_field.count() > 0:
                    print("✅ [SIMPLE] Found email field by placeholder")
                else:
                    print("❌ [SIMPLE] No email field found!")
                    return
            
            print("📧 [SIMPLE] Filling email...")
            await email_field.click()
            await email_field.fill("")  # Clear first
            await email_field.fill(POLAROO_EMAIL or "")
            print(f"✅ [SIMPLE] Email filled: {POLAROO_EMAIL}")
            
            print("🔍 [SIMPLE] Looking for password field...")
            password_field = page.locator('#password').first
            if await password_field.count() > 0:
                print("✅ [SIMPLE] Found password field by ID")
            else:
                password_field = page.get_by_placeholder("Password").first
                if await password_field.count() > 0:
                    print("✅ [SIMPLE] Found password field by placeholder")
                else:
                    print("❌ [SIMPLE] No password field found!")
                    return
            
            print("🔑 [SIMPLE] Filling password...")
            await password_field.click()
            await password_field.fill("")  # Clear first
            await password_field.fill(POLAROO_PASSWORD or "")
            print("✅ [SIMPLE] Password filled")
            
            print("🔍 [SIMPLE] Looking for sign in button...")
            signin_button = page.get_by_role("button", name="Sign in").first
            if await signin_button.count() > 0:
                print("✅ [SIMPLE] Found sign in button by role")
            else:
                signin_button = page.locator('button:has-text("Sign in")').first
                if await signin_button.count() > 0:
                    print("✅ [SIMPLE] Found sign in button by text")
                else:
                    print("❌ [SIMPLE] No sign in button found!")
                    return
            
            print("🖱️ [SIMPLE] Clicking sign in button...")
            await signin_button.click()
            print("✅ [SIMPLE] Sign in button clicked!")
            
            print("⏳ [SIMPLE] Waiting for redirect...")
            await page.wait_for_timeout(5000)
            
            print(f"🌐 [SIMPLE] Current URL: {page.url}")
            
            if "login" not in page.url.lower():
                print("✅ [SIMPLE] Successfully logged in! Redirected away from login page.")
            else:
                print("❌ [SIMPLE] Still on login page, login might have failed.")
            
            print("📸 [SIMPLE] Taking final screenshot...")
            await page.screenshot(path="_debug/simple_login_final.png")
            print("✅ [SIMPLE] Final screenshot saved to _debug/simple_login_final.png")
            
            print("\n🎯 [SIMPLE] Browser will stay open for 30 seconds...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"❌ [SIMPLE] Error: {e}")
            try:
                await page.screenshot(path="_debug/simple_login_error.png")
                print("📸 [SIMPLE] Error screenshot saved to _debug/simple_login_error.png")
            except:
                pass
        finally:
            await context.close()

if __name__ == "__main__":
    print("🚀 [START] Testing simple login...")
    asyncio.run(test_simple_login())
