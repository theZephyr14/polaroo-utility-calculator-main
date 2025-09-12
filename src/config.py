import os
from dotenv import load_dotenv

# Load environment variables with fallbacks
try:
    load_dotenv('.env2')
except:
    # Set environment variables directly if .env2 fails
    os.environ.setdefault('STORAGE_BUCKET', 'polaroo_pdfs')
    os.environ.setdefault('SUPABASE_URL', 'https://dfryezdsbwwfwkdfzhao.supabase.co')
    os.environ.setdefault('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmcnllemRzYnd3ZndrZGZ6aGFvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYyMDEwNzEsImV4cCI6MjA3MTc3NzA3MX0.ZngI03QHOMQ0TFm49hCmbxDunA2vaQfaEzW44EVGKVk')
    os.environ.setdefault('POLAROO_EMAIL', 'francisco@node-living.com')
    os.environ.setdefault('POLAROO_PASSWORD', 'Aribau126!')

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

POLAROO_EMAIL = os.getenv("POLAROO_EMAIL")
POLAROO_PASSWORD = os.getenv("POLAROO_PASSWORD")

COHERE_API_KEY = os.getenv("COHERE_API_KEY", "9MdzGhunt8Nrc9cwFdBl3GvlRWRIkGLN4VPma3Yp")

STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "polaroo")
STORAGE_PREFIX = os.getenv("STORAGE_PREFIX", "raw")
STORAGE_STATE_PATH = os.getenv("STORAGE_STATE_PATH", "./.auth/polaroo-state.json")

REPORT_DATE = os.getenv("REPORT_DATE")  # YYYY-MM-DD or None
