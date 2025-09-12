"""
Fix the Adobe Web Viewer download button detection with more comprehensive selectors.
"""
import re

def fix_adobe_download():
    """Improve Adobe Web Viewer download button detection."""
    
    # Read the current file
    with open('src/polaroo_scrape.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the Adobe download selectors section
    old_selectors = '''                download_selectors = [
                    'button[title*="Download"]',
                    'button[aria-label*="Download"]',
                    'button:has-text("Download")',
                    'a[title*="Download"]',
                    'a[aria-label*="Download"]',
                    'a:has-text("Download")',
                    '[data-testid*="download"]',
                    '.download-button',
                    'button[class*="download"]'
                ]'''
    
    # Create more comprehensive selectors for Adobe Web Viewer
    new_selectors = '''                # Comprehensive selectors for Adobe Web Viewer
                download_selectors = [
                    # Common download button patterns
                    'button[title*="Download" i]',
                    'button[aria-label*="Download" i]',
                    'button:has-text("Download")',
                    'a[title*="Download" i]',
                    'a[aria-label*="Download" i]',
                    'a:has-text("Download")',
                    '[data-testid*="download" i]',
                    '.download-button',
                    'button[class*="download" i]',
                    
                    # Adobe-specific patterns
                    'button[title*="Save" i]',
                    'button[aria-label*="Save" i]',
                    'button:has-text("Save")',
                    'a[title*="Save" i]',
                    'a[href*="download" i]',
                    'a[href*=".pdf" i]',
                    
                    # Icon-based patterns
                    'button svg[class*="download"]',
                    'button svg[class*="save"]',
                    'a svg[class*="download"]',
                    'a svg[class*="save"]',
                    
                    # Generic button patterns
                    'button[type="button"]',
                    'button[class*="btn"]',
                    'button[class*="button"]',
                    'a[class*="btn"]',
                    'a[class*="button"]',
                    
                    # Top-right area patterns (common for download buttons)
                    'header button',
                    '.header button',
                    '.toolbar button',
                    '.controls button',
                    '.actions button',
                    '[class*="header"] button',
                    '[class*="toolbar"] button',
                    '[class*="control"] button',
                    '[class*="action"] button',
                    
                    # Right-click context menu patterns
                    '[role="menuitem"]:has-text("Download")',
                    '[role="menuitem"]:has-text("Save")',
                    
                    # Fallback - any clickable element
                    'button',
                    'a[href]'
                ]'''
    
    # Replace the old selectors
    content = content.replace(old_selectors, new_selectors)
    
    # Also add better debugging and fallback logic
    old_button_logic = '''                download_button = None
                for selector in download_selectors:
                    try:
                        download_button = new_page.locator(selector).first
                        if await download_button.count() > 0 and await download_button.is_visible():
                            print(f"✅ [DOWNLOAD] Found download button with selector: {selector}")
                            break
                    except:
                        continue'''
    
    new_button_logic = '''                download_button = None
                
                # First, take a screenshot for debugging
                await new_page.screenshot(path=f"_debug/adobe_page_{i+1}.png")
                print(f"📸 [DEBUG] Adobe page screenshot saved to _debug/adobe_page_{i+1}.png")
                
                # Get page content for debugging
                page_text = await new_page.text_content('body')
                print(f"🔍 [DEBUG] Adobe page contains 'download': {'download' in page_text.lower()}")
                print(f"🔍 [DEBUG] Adobe page contains 'save': {'save' in page_text.lower()}")
                
                # Try all selectors
                for j, selector in enumerate(download_selectors):
                    try:
                        elements = await new_page.locator(selector).all()
                        if elements:
                            print(f"🔍 [DEBUG] Selector {j+1} '{selector}': Found {len(elements)} elements")
                            for k, elem in enumerate(elements):
                                try:
                                    if await elem.is_visible():
                                        text = await elem.text_content()
                                        print(f"  Element {k+1}: '{text[:50]}...' (visible)")
                                        download_button = elem
                                        print(f"✅ [DOWNLOAD] Found download button with selector: {selector}")
                                        break
                                except:
                                    continue
                            if download_button:
                                break
                    except Exception as e:
                        print(f"⚠️ [DEBUG] Selector {j+1} '{selector}' failed: {e}")
                        continue
                
                # If still no button found, try to find any clickable element
                if not download_button:
                    print("🔍 [DEBUG] Trying to find any clickable element...")
                    try:
                        all_buttons = await new_page.locator('button, a').all()
                        print(f"🔍 [DEBUG] Found {len(all_buttons)} total buttons/links")
                        for btn in all_buttons[:5]:  # Check first 5
                            try:
                                if await btn.is_visible():
                                    text = await btn.text_content()
                                    print(f"  Button: '{text[:30]}...'")
                            except:
                                pass
                    except:
                        pass'''
    
    # Replace the old button logic
    content = content.replace(old_button_logic, new_button_logic)
    
    # Write the updated content back
    with open('src/polaroo_scrape.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ [FIX] Adobe Web Viewer download button detection improved!")
    print("🔧 [CHANGES] Added comprehensive selectors for Adobe Web Viewer")
    print("📸 [DEBUG] Added screenshot and text debugging")
    print("🎯 [IMPROVEMENT] Now tries 30+ different selectors and provides detailed debugging")

if __name__ == "__main__":
    fix_adobe_download()
