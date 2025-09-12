"""
Debug script to see what's on the login page and fix the selectors.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from src.config import POLAROO_EMAIL, POLAROO_PASSWORD

async def debug_login_page():
    """Debug the login page to see what selectors we need."""
    print("🔍 [DEBUG] Opening login page to inspect elements...")
    
    user_data = str(Path("./.chrome-profile").resolve())
    Path(user_data).mkdir(exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=False,  # VISIBLE BROWSER
            slow_mo=2000,    # Very slow so you can see everything
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
            print("🌐 [DEBUG] Going to login page...")
            await page.goto("https://app.polaroo.com/login")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)
            
            print("📸 [DEBUG] Taking screenshot...")
            await page.screenshot(path="_debug/login_page.png")
            print("✅ [DEBUG] Screenshot saved to _debug/login_page.png")
            
            print("🔍 [DEBUG] Looking for all input fields...")
            inputs = await page.locator('input').all()
            print(f"Found {len(inputs)} input fields:")
            
            for i, input_elem in enumerate(inputs):
                try:
                    input_type = await input_elem.get_attribute('type')
                    placeholder = await input_elem.get_attribute('placeholder')
                    name = await input_elem.get_attribute('name')
                    id_attr = await input_elem.get_attribute('id')
                    class_attr = await input_elem.get_attribute('class')
                    
                    print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}', name='{name}', id='{id_attr}', class='{class_attr}'")
                except Exception as e:
                    print(f"  Input {i}: Error reading attributes: {e}")
            
            print("\n🔍 [DEBUG] Looking for all buttons...")
            buttons = await page.locator('button').all()
            print(f"Found {len(buttons)} buttons:")
            
            for i, button in enumerate(buttons):
                try:
                    text = await button.text_content()
                    type_attr = await button.get_attribute('type')
                    class_attr = await button.get_attribute('class')
                    
                    print(f"  Button {i}: text='{text}', type='{type_attr}', class='{class_attr}'")
                except Exception as e:
                    print(f"  Button {i}: Error reading attributes: {e}")
            
            print("\n🔍 [DEBUG] Looking for forms...")
            forms = await page.locator('form').all()
            print(f"Found {len(forms)} forms:")
            
            for i, form in enumerate(forms):
                try:
                    action = await form.get_attribute('action')
                    method = await form.get_attribute('method')
                    class_attr = await form.get_attribute('class')
                    
                    print(f"  Form {i}: action='{action}', method='{method}', class='{class_attr}'")
                except Exception as e:
                    print(f"  Form {i}: Error reading attributes: {e}")
            
            print("\n🎯 [DEBUG] Browser will stay open for 60 seconds so you can inspect the page...")
            print("Look at the page and tell me what you see!")
            await page.wait_for_timeout(60000)  # Keep open for 60 seconds
            
        except Exception as e:
            print(f"❌ [ERROR] Debug failed: {e}")
            await page.screenshot(path="_debug/error_debug.png")
            print("📸 [DEBUG] Error screenshot saved to _debug/error_debug.png")
        finally:
            await context.close()

if __name__ == "__main__":
    print("🚀 [START] Debugging login page...")
    print("This will open a browser and show you all the elements on the login page.")
    
    asyncio.run(debug_login_page())
