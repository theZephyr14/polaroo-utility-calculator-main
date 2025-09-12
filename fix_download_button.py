"""
Fix the download button detection to make it properly clickable.
"""
import re

def fix_download_button():
    """Fix the download button to be properly clickable."""
    
    # Read the current file
    with open('src/polaroo_scrape.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the download button assignment
    old_button = "                'download_button': cells[0] if len(cells) > 0 else None,  # Download button (first column)"
    
    # Create improved download button detection
    new_button = '''                'download_button': None,  # Will be set below
            }
            
            # Find the actual clickable download button in the first column
            if len(cells) > 0:
                # Look for clickable elements in the first cell
                download_selectors = [
                    'button',
                    'a',
                    '[role="button"]',
                    'svg',
                    '[class*="icon"]',
                    '[class*="download"]',
                    '[class*="cloud"]'
                ]
                
                for selector in download_selectors:
                    try:
                        download_elem = cells[0].locator(selector).first
                        if await download_elem.count() > 0 and await download_elem.is_visible():
                            invoice_data['download_button'] = download_elem
                            break
                    except:
                        continue
                
                # If no specific button found, try the cell itself
                if not invoice_data['download_button']:
                    try:
                        if await cells[0].is_visible():
                            invoice_data['download_button'] = cells[0]
                    except:
                        pass'''
    
    # Replace the old button assignment
    content = content.replace(old_button, new_button)
    
    # Write the updated content back
    with open('src/polaroo_scrape.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ [FIX] Download button detection improved!")
    print("🔧 [CHANGES] Added proper clickable element detection in first column")
    print("📝 [IMPROVEMENT] Now looks for buttons, links, and other clickable elements")

if __name__ == "__main__":
    fix_download_button()
