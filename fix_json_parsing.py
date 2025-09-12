"""
Fix the JSON parsing in the Cohere response handling.
"""
import re

def fix_json_parsing():
    """Fix the JSON parsing logic in polaroo_scrape.py."""
    
    # Read the current file
    with open('src/polaroo_scrape.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the JSON parsing section
    old_parsing = '''        # Try to parse JSON response
        import json
        try:
            analysis = json.loads(llm_response)
            selected_electricity_rows = analysis.get('selected_electricity_rows', [])
            selected_water_rows = analysis.get('selected_water_rows', [])
            reasoning = analysis.get('reasoning', 'No reasoning provided')
            
            print(f"🤖 [COHERE] Selected electricity rows: {selected_electricity_rows}")
            print(f"🤖 [COHERE] Selected water rows: {selected_water_rows}")
            print(f"🤖 [COHERE] Reasoning: {reasoning}")
            
        except json.JSONDecodeError:
            print("⚠️ [COHERE] Failed to parse JSON response, using fallback logic")
            # Fallback to basic logic
            selected_electricity_rows = []
            selected_water_rows = []
            reasoning = "JSON parsing failed, using fallback logic"'''
    
    # Create improved JSON parsing
    new_parsing = '''        # Try to parse JSON response
        import json
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\\{.*\\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                analysis = json.loads(json_str)
            else:
                # Try parsing the whole response
                analysis = json.loads(llm_response)
            
            selected_electricity_rows = analysis.get('selected_electricity_rows', [])
            selected_water_rows = analysis.get('selected_water_rows', [])
            reasoning = analysis.get('reasoning', 'No reasoning provided')
            missing_bills = analysis.get('missing_bills', 'None')
            
            print(f"✅ [COHERE] Parsed: {len(selected_electricity_rows)} electricity, {len(selected_water_rows)} water bills")
            print(f"🤖 [COHERE] Selected electricity rows: {selected_electricity_rows}")
            print(f"🤖 [COHERE] Selected water rows: {selected_water_rows}")
            print(f"🤖 [COHERE] Reasoning: {reasoning}")
            if missing_bills and missing_bills != 'None':
                print(f"⚠️ [COHERE] Missing: {missing_bills}")
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️ [COHERE] Failed to parse JSON response: {e}")
            print(f"🔍 [COHERE] Raw response: {llm_response[:200]}...")
            print("🔄 [COHERE] Using fallback logic...")
            # Fallback to basic logic
            selected_electricity_rows = []
            selected_water_rows = []
            reasoning = f"JSON parsing failed: {e}"
            missing_bills = "Could not parse LLM response"'''
    
    # Replace the old parsing with the new one
    content = content.replace(old_parsing, new_parsing)
    
    # Write the updated content back
    with open('src/polaroo_scrape.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ [FIX] JSON parsing improved!")
    print("🔧 [CHANGES] Added regex extraction and better error handling")
    print("📝 [IMPROVEMENT] Now handles LLM responses with extra text")

if __name__ == "__main__":
    fix_json_parsing()
