"""
Fix Adobe Web Viewer loading and button detection with better waiting.
"""
import re

def fix_adobe_wait():
    """Improve Adobe Web Viewer loading and button detection."""
    
    # Read the current file
    with open('src/polaroo_scrape.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the Adobe loading section
    old_wait = '''                # Wait for Adobe Acrobat to load
                await new_page.wait_for_timeout(3000)'''
    
    # Replace with better waiting logic
    new_wait = '''                # Wait for Adobe Web Viewer to fully load
                print("⏳ [ADOBE] Waiting for Adobe Web Viewer to load...")
                await new_page.wait_for_timeout(8000)  # Wait 8 seconds for full load
                
                # Try to wait for the page to be ready
                try:
                    await new_page.wait_for_load_state("networkidle", timeout=10000)
                    print("✅ [ADOBE] Adobe page loaded (networkidle)")
                except:
                    print("⚠️ [ADOBE] Adobe page loaded (timeout)")'''
    
    # Replace the old wait logic
    content = content.replace(old_wait, new_wait)
    
    # Also improve the button finding logic
    old_button_logic = '''                # Wait longer for Adobe Web Viewer to fully load
                print("⏳ [ADOBE] Waiting for Adobe Web Viewer to load...")
                await new_page.wait_for_timeout(5000)  # Wait 5 seconds for full load
                
                download_button = None
                for selector in download_selectors:
                    try:
                        download_button = new_page.locator(selector).first
                        if await download_button.count() > 0 and await download_button.is_visible():
                            print(f"✅ [DOWNLOAD] Found download button with selector: {selector}")
                            break
                    except:
                        continue
                
                # Take screenshot for debugging if no button found
                if not download_button:
                    await new_page.screenshot(path=f"_debug/adobe_no_button_{i+1}.png")
                    print(f"📸 [DEBUG] No button found, screenshot saved to _debug/adobe_no_button_{i+1}.png")'''
    
    # Replace with more patient button finding
    new_button_logic = '''                download_button = None
                
                # Try multiple times to find the download button
                for attempt in range(3):
                    print(f"🔍 [ADOBE] Attempt {attempt + 1}/3 to find download button...")
                    
                    for selector in download_selectors:
                        try:
                            download_button = new_page.locator(selector).first
                            if await download_button.count() > 0 and await download_button.is_visible():
                                print(f"✅ [DOWNLOAD] Found download button with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if download_button:
                        break
                    
                    # Wait a bit more and try again
                    if attempt < 2:
                        print("⏳ [ADOBE] Waiting 2 more seconds and trying again...")
                        await new_page.wait_for_timeout(2000)
                
                # Take screenshot for debugging if no button found
                if not download_button:
                    await new_page.screenshot(path=f"_debug/adobe_no_button_{i+1}.png")
                    print(f"📸 [DEBUG] No button found after 3 attempts, screenshot saved to _debug/adobe_no_button_{i+1}.png")
                    
                    # Get page text for debugging
                    try:
                        page_text = await new_page.text_content('body')
                        print(f"🔍 [DEBUG] Adobe page text (first 200 chars): {page_text[:200]}")
                    except:
                        print("🔍 [DEBUG] Could not get Adobe page text")'''
    
    # Replace the old button logic
    content = content.replace(old_button_logic, new_button_logic)
    
    # Write the updated content back
    with open('src/polaroo_scrape.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ [FIX] Adobe Web Viewer loading improved!")
    print("⏳ [CHANGES] Increased wait time to 8 seconds + networkidle")
    print("🔄 [IMPROVEMENT] Added 3 attempts to find download button")
    print("📸 [DEBUG] Added better debugging with screenshots and page text")

if __name__ == "__main__":
    fix_adobe_wait()
