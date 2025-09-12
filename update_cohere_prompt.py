
"""
Script to update the Cohere prompt with improved date overlap logic.
"""
import re

def update_cohere_prompt():
    """Update the Cohere prompt in polaroo_scrape.py with improved logic."""
    
    # Read the current file
    with open('src/polaroo_scrape.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the old prompt section
    old_prompt_start = 'invoice_text += "\\nIMPORTANT: Only select invoices that fall within the specified period {start_month} to {end_month}.\\n"'
    old_prompt_end = 'invoice_text += \'{"selected_electricity_rows": [row_numbers], "selected_water_rows": [row_numbers], "reasoning": "explanation", "missing_bills": "what is missing"}\''
    
    # Create the new improved prompt
    new_prompt = '''invoice_text += f"\\nOPERATIONAL LOGIC (for start of month calculations):\\n"
        invoice_text += f"\\nWATER: Find 1 bill that covers BOTH months of the period\\n"
        invoice_text += f"- If calculating for {start_month} to {end_month} period\\n"
        invoice_text += f"- Look for water bill that covers {start_month} AND {end_month} (any date range that includes both months)\\n"
        invoice_text += f"\\nELECTRICITY: Find 2 separate bills\\n"
        invoice_text += f"- 1 bill that covers the first month of the period ({start_month})\\n"
        invoice_text += f"- 1 bill that covers the second month of the period ({end_month})\\n"
        invoice_text += f"- Each bill can have any date range as long as it covers its respective month\\n"
        invoice_text += f"\\nFLEXIBLE DATE MATCHING EXAMPLES:\\n"
        invoice_text += f"- Water bill 15/06-15/08 covers July-August ✓\\n"
        invoice_text += f"- Water bill 01/07-31/08 covers July-August ✓\\n"
        invoice_text += f"- Water bill 20/07-20/09 covers July-August ✓\\n"
        invoice_text += f"- Electricity 15/07-14/08 covers July ✓\\n"
        invoice_text += f"- Electricity 01/08-31/08 covers August ✓\\n"
        invoice_text += f"- Electricity 20/08-19/09 covers August ✓\\n"
        invoice_text += f"\\nThe goal is to find bills that actually cover the months you're calculating for, regardless of the specific dates.\\n"
        invoice_text += f"\\nIMPORTANT RULES:\\n"
        invoice_text += f"- Only select bills that cover the months you're calculating for\\n"
        invoice_text += f"- Do NOT substitute with older bills if the required bills are not available\\n"
        invoice_text += f"- If bills are missing for the period, return empty arrays and explain what's missing\\n"
        invoice_text += f"- Return the row numbers of selected invoices\\n\\n"
        invoice_text += f"Format your response as JSON with this structure:\\n"
        invoice_text += f'{{"selected_electricity_rows": [row_numbers], "selected_water_rows": [row_numbers], "reasoning": "explanation", "missing_bills": "what is missing"}}' '''
    
    # Replace the old prompt with the new one
    pattern = r'invoice_text \+= "\\nIMPORTANT: Only select invoices that fall within the specified period \{start_month\} to \{end_month\}\\.\\n".*?invoice_text \+= \'\{.*?\}\''
    
    new_content = re.sub(pattern, new_prompt, content, flags=re.DOTALL)
    
    # Write the updated content back
    with open('src/polaroo_scrape.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ [UPDATE] Cohere prompt updated with improved date overlap logic!")
    print("📝 [CHANGES] Added flexible date matching for water and electricity bills")
    print("🎯 [LOGIC] Water: 1 bill covering both months, Electricity: 2 separate monthly bills")

if __name__ == "__main__":
    update_cohere_prompt()
