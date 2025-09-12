"""
Simplify the Cohere prompt to be more direct and clear.
"""
import re

def simplify_cohere_prompt():
    """Simplify the Cohere prompt to be more direct."""
    
    # Read the current file
    with open('src/polaroo_scrape.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the complex prompt section and replace with simpler one
    old_prompt_pattern = r'invoice_text \+= f"\\nOPERATIONAL LOGIC.*?invoice_text \+= f\'\{.*?\}\''
    
    new_prompt = '''invoice_text += f"\\nTASK: Select utility bills for period {start_month} to {end_month}\\n"
        invoice_text += f"\\nREQUIREMENTS:\\n"
        invoice_text += f"- WATER: Find 1 bill that covers BOTH {start_month} AND {end_month}\\n"
        invoice_text += f"- ELECTRICITY: Find 2 bills - one for {start_month}, one for {end_month}\\n"
        invoice_text += f"\\nRULES:\\n"
        invoice_text += f"- Bills can start/end on any date as long as they cover the required months\\n"
        invoice_text += f"- Water bill must cover both months (e.g., 15/06-15/08 covers July-August)\\n"
        invoice_text += f"- Electricity bills must be separate (one per month)\\n"
        invoice_text += f"- If bills are missing, return empty arrays\\n"
        invoice_text += f"\\nReturn JSON: {{\\"selected_electricity_rows\\": [row_numbers], \\"selected_water_rows\\": [row_numbers], \\"reasoning\\": \\"explanation\\"}}" '''
    
    # Replace the complex prompt
    content = re.sub(old_prompt_pattern, new_prompt, content, flags=re.DOTALL)
    
    # Write the updated content back
    with open('src/polaroo_scrape.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ [SIMPLIFY] Cohere prompt simplified!")
    print("🎯 [CHANGES] Made prompt more direct and concise")
    print("📝 [IMPROVEMENT] Removed complex explanations, focused on core task")

if __name__ == "__main__":
    simplify_cohere_prompt()
