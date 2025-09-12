"""
Fix the tab navigation after downloading PDFs.
"""
import re

def fix_tab_navigation():
    """Add logic to go back to original tab after closing Adobe tab."""
    
    # Read the current file
    with open('src/polaroo_scrape.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the section where it closes the Adobe tab
    old_close_section = '''                print(f"✅ [DOWNLOAD] Downloaded and processed: {filename}")
                
                # Close the Adobe Acrobat tab
                await new_page.close()'''
    
    # Create the improved version that goes back to original tab
    new_close_section = '''                print(f"✅ [DOWNLOAD] Downloaded and processed: {filename}")
                
                # Close the Adobe Acrobat tab
                await new_page.close()
                
                # Switch back to the original tab (invoices page)
                print("🔄 [TAB] Switching back to original invoices tab...")
                await page.bring_to_front()
                await page.wait_for_timeout(1000)  # Wait for tab switch
                print("✅ [TAB] Back on original invoices tab")'''
    
    # Replace the old section with the new one
    content = content.replace(old_close_section, new_close_section)
    
    # Write the updated content back
    with open('src/polaroo_scrape.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ [FIX] Tab navigation improved!")
    print("🔄 [CHANGES] Added logic to switch back to original tab after closing Adobe tab")
    print("📝 [IMPROVEMENT] Bot will now return to invoices page after each PDF download")

if __name__ == "__main__":
    fix_tab_navigation()
