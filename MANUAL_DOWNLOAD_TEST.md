# Manual Invoice Download Test Scripts

These scripts allow you to manually test the invoice download process before integrating it into the main system.

## Scripts Available

### 1. `test_manual_download.py`
**Basic test** - Downloads invoice data and uses LLM analysis without PDF downloads.

**Features:**
- Select property from database
- Choose date range (last 2 months or custom)
- Login to Polaroo
- Search for property
- Get invoice data
- Use LLM to analyze and select invoices
- Show costs and reasoning
- **No PDF downloads**

### 2. `test_manual_download_with_pdfs.py`
**Full test** - Downloads actual PDF files and uploads to Supabase.

**Features:**
- Everything from basic test PLUS:
- Download actual PDF invoices
- Upload PDFs to Supabase storage
- Show upload progress and file paths

## Setup

1. **Install requirements:**
   ```bash
   pip install -r test_requirements.txt
   playwright install chromium
   ```

2. **Make sure your environment is set up:**
   - `.env2` file with Supabase credentials
   - Supabase database with properties loaded

## Usage

### Basic Test (No PDFs)
```bash
python test_manual_download.py
```

### Full Test (With PDFs)
```bash
python test_manual_download_with_pdfs.py
```

## What You'll See

1. **Property Selection:** Choose from all properties in your database
2. **Date Range:** Select last 2 months or custom range
3. **Browser Window:** Opens visible browser so you can see what the bot is doing
4. **Progress Updates:** Real-time updates as the bot works
5. **LLM Analysis:** Shows which invoices were selected and why
6. **Results:** Final costs and file locations

## Expected Output

The bot should:
1. ✅ Login to Polaroo successfully
2. ✅ Find your selected property
3. ✅ Get all invoice data from the table
4. ✅ Use LLM to select the right invoices (2 electricity + 1 water for 2-month period)
5. ✅ Show reasoning for selections
6. ✅ Calculate total costs
7. ✅ (Full test) Download PDFs and upload to Supabase

## Troubleshooting

- **Login fails:** Check your credentials in `.env2`
- **Property not found:** Make sure the property exists in both your database and Polaroo
- **No invoices:** Check if the property has invoices in the selected date range
- **LLM errors:** Check your Cohere API key

## Next Steps

Once this works perfectly, we'll integrate the same logic into the main system's "Get Data" button in the overages tab.
