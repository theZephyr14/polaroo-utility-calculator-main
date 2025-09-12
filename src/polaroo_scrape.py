import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from src.config import (
    POLAROO_EMAIL,
    POLAROO_PASSWORD,
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    STORAGE_BUCKET,
)

LOGIN_URL = "https://app.polaroo.com/login"

# ---------- global waits ----------
WAIT_MS = 5_000          # minimum wait after each step
MAX_WAIT_LOOPS = 20       # 20 * 500ms = 30s for dashboard detection

# ---------- utils ----------
def _infer_content_type(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".csv"):
        return "text/csv"
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/octet-stream"

def _upload_to_supabase_bytes(filename: str, data: bytes) -> str:
    """
    Uploads `data` to Supabase Storage using REST.
    Returns the path key stored in the bucket.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY or not STORAGE_BUCKET:
        raise RuntimeError("Supabase env config missing: SUPABASE_URL / SUPABASE_SERVICE_KEY / STORAGE_BUCKET")

    # Upload to raw folder with flat name subfolder
    object_key = f"raw/{filename}"

    url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{quote(STORAGE_BUCKET)}/{quote(object_key)}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": _infer_content_type(filename),
        "x-upsert": "true",
    }
    resp = requests.post(url, headers=headers, data=data, timeout=60)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Supabase upload failed [{resp.status_code}]: {resp.text}")

    return object_key

async def _wait(page, label: str):
    print(f"⏳ [WAIT] {label} … {WAIT_MS}ms")
    await page.wait_for_timeout(WAIT_MS)

# ---------- helpers ----------
async def _wait_for_dashboard(page) -> None:
    """Wait until we are on any /dashboard page and the sidebar/nav is present."""
    print("🔍 [DASHBOARD] Waiting for dashboard page to load...")
    for i in range(MAX_WAIT_LOOPS):  # up to ~30s
        url = page.url
        has_sidebar = await page.locator("nav, [role='navigation']").count() > 0
        print(f"🔍 [DASHBOARD] Attempt {i+1}/{MAX_WAIT_LOOPS}: URL={url}, Has sidebar={has_sidebar}")
        if "/dashboard" in url and has_sidebar:
            print("✅ [DASHBOARD] Dashboard detected! Waiting for network idle...")
            await page.wait_for_load_state("networkidle")
            print("✅ [DASHBOARD] Dashboard fully loaded!")
            return
        await page.wait_for_timeout(500)
    raise PWTimeout("Did not reach a dashboard page with sidebar after sign-in.")

async def _ensure_logged_in(page) -> None:
    """Start at /login. If already authenticated, Polaroo will redirect to dashboard. If not, login and let it redirect."""
    print("🚀 [LOGIN] Starting login process...")
    
    # Add a small delay to make it look more human-like
    await page.wait_for_timeout(2000)
    
    await page.goto(LOGIN_URL)
    print(f"🌐 [LOGIN] Navigated to: {page.url}")
    await page.wait_for_load_state("domcontentloaded")
    await _wait(page, "after goto /login")

    if "login" in page.url.lower():
        print("🔐 [LOGIN] Login page detected, proceeding with authentication...")
        try:
            print("🔍 [LOGIN] Waiting for 'Sign in' heading...")
            await page.get_by_role("heading", name="Sign in").wait_for(timeout=30_000)  # Reduced from 60s to 30s
            print("✅ [LOGIN] 'Sign in' heading found!")
            
            print("📧 [LOGIN] Filling email...")
            await page.get_by_placeholder("Email").fill(POLAROO_EMAIL or "")
            print("🔑 [LOGIN] Filling password...")
            await page.get_by_placeholder("Password").fill(POLAROO_PASSWORD or "")
            await _wait(page, "after filling credentials")
            
            print("🖱️ [LOGIN] Clicking Sign in button...")
            await page.get_by_role("button", name="Sign in").click()
            await page.wait_for_load_state("domcontentloaded")
            print("✅ [LOGIN] Sign in button clicked, waiting for redirect...")
        except PWTimeout as e:
            print(f"❌ [LOGIN] Timeout waiting for login elements: {e}")
            # Take a screenshot for debugging
            await page.screenshot(path="_debug/login_timeout.png")
            print("📸 [LOGIN] Screenshot saved to _debug/login_timeout.png")
            raise
    else:
        print("✅ [LOGIN] Already logged in, redirected to dashboard")

    # Wait 5 seconds after login, then navigate to accounting dashboard
    print("⏳ [WAIT] Waiting 5 seconds after login...")
    await page.wait_for_timeout(5_000)
    
    # Navigate directly to accounting dashboard
    accounting_url = "https://app.polaroo.com/dashboard/accounting"
    print(f"🌐 [NAVIGATE] Going to accounting dashboard: {accounting_url}")
    await page.goto(accounting_url)
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_load_state("networkidle")
    print("✅ [NAVIGATE] Successfully reached accounting dashboard")
    
    # Wait 10 seconds after reaching accounting dashboard
    print("⏳ [WAIT] Waiting 10 seconds after reaching accounting dashboard...")
    await page.wait_for_timeout(10_000)

async def _open_report_from_sidebar(page) -> None:
    """Click the 'Report' item in the left sidebar to open the Report page."""
    print("📊 [REPORT] Looking for Report link in sidebar...")
    candidates = [
        page.get_by_role("link", name="Report"),
        page.get_by_role("link", name=re.compile(r"\bReport\b", re.I)),
        page.locator('a:has-text("Report")'),
        page.locator('[role="navigation"] >> text=Report'),
        page.locator('nav >> text=Report'),
    ]
    for i, loc in enumerate(candidates):
        count = await loc.count()
        print(f"🔍 [REPORT] Candidate {i+1}: Found {count} elements")
        if count:
            btn = loc.first
            if await btn.is_visible():
                print("✅ [REPORT] Found visible Report link, clicking...")
                await btn.scroll_into_view_if_needed()
                await _wait(page, "before clicking sidebar → Report")
                await btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
                await _wait(page, "after landing on Report")
                print(f"✅ [REPORT] Successfully navigated to Report page: {page.url}")
                return
    raise PWTimeout("Could not click 'Report' in the sidebar.")

async def _set_date_range_last_month(page) -> None:
    """Open the date-range picker and select 'Last month' (robust for ng-select)."""
    print("📅 [DATE] Looking for date range selector...")
    container = page.locator(".ng-select .ng-select-container").filter(
        has_text=re.compile(r"last\s+\d+\s*month(s)?|last\s+month", re.I)
    ).first

    if await container.count() == 0:
        print("🔍 [DATE] Trying alternative selector...")
        chip = page.get_by_text(re.compile(r"^last\s+\d+\s*month(s)?$|^last\s+month$", re.I)).first
        if await chip.count():
            container = chip.locator(
                'xpath=ancestor-or-self::*[contains(@class,"ng-select")][1]//div[contains(@class,"ng-select-container")]'
            ).first

    if await container.count() == 0:
        raise PWTimeout("Date-range selector not found (no ng-select container with 'Last … month').")

    print("✅ [DATE] Found date range selector, opening dropdown...")
    await container.scroll_into_view_if_needed()
    await _wait(page, "before opening date-range menu")

    def listbox_open():
        return page.locator('[role="listbox"], .ng-dropdown-panel').first

    opened = False
    try:
        await container.click()
        await page.wait_for_timeout(600)
        opened = await listbox_open().count() > 0
        print(f"🔍 [DATE] Click attempt 1: Dropdown opened = {opened}")
    except Exception as e:
        print(f"⚠️ [DATE] Click attempt 1 failed: {e}")
        opened = False

    if not opened:
        arrow = container.locator(".ng-arrow-wrapper, .ng-arrow").first
        if await arrow.count():
            await arrow.click()
            await page.wait_for_timeout(600)
            opened = await listbox_open().count() > 0
            print(f"🔍 [DATE] Click attempt 2 (arrow): Dropdown opened = {opened}")

    if not opened:
        await container.focus()
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(600)
        opened = await listbox_open().count() > 0
        print(f"🔍 [DATE] Click attempt 3 (Enter): Dropdown opened = {opened}")

    if not opened:
        box = await container.bounding_box()
        if box:
            await page.mouse.click(box["x"] + box["width"] - 8, box["y"] + box["height"] / 2)
            await page.wait_for_timeout(600)
            opened = await listbox_open().count() > 0
            print(f"🔍 [DATE] Click attempt 4 (mouse): Dropdown opened = {opened}")

    if not opened:
        raise PWTimeout("Could not open the date-range dropdown.")

    print("✅ [DATE] Date range dropdown opened successfully!")
    await _wait(page, "after opening date-range menu")

    print("🔍 [DATE] Looking for 'Last month' option...")
    option = page.locator(
        '.ng-dropdown-panel .ng-option',
        has_text=re.compile(r"^\s*last\s+month(s)?\s*$", re.I),
    ).first
    if not await option.count():
        option = page.get_by_text(re.compile(r"^\s*last\s+month(s)?\s*$", re.I)).first

    await option.wait_for(timeout=30_000)  # Reduced from 60s to 30s
    await _wait(page, "before selecting 'Last month'")
    await option.click()
    await page.wait_for_load_state("networkidle")
    await _wait(page, "after selecting 'Last month'")
    print("✅ [DATE] Successfully selected 'Last month'!")

async def _open_download_menu(page) -> None:
    """Click the visible 'Download' control."""
    print("📥 [DOWNLOAD] Looking for Download button...")
    await page.evaluate("window.scrollTo(0, 0)")
    btns = page.get_by_text("Download", exact=True)
    if not await btns.count():
        print("🔍 [DOWNLOAD] Trying case-insensitive search...")
        btns = page.locator(r'text=/\bdownload\b/i')
    cnt = await btns.count()
    print(f"🔍 [DOWNLOAD] Found {cnt} Download elements")
    if cnt == 0:
        raise PWTimeout("No element with visible text matching 'Download' found.")
    for i in range(cnt):
        el = btns.nth(i)
        if await el.is_visible():
            print(f"✅ [DOWNLOAD] Found visible Download button #{i+1}, clicking...")
            await el.scroll_into_view_if_needed()
            await _wait(page, "before opening Download menu")
            await el.click()
            await page.wait_for_timeout(500)
            await _wait(page, "after opening Download menu")
            print("✅ [DOWNLOAD] Download menu opened successfully!")
            return
    raise PWTimeout("Found 'Download' elements, but none were visible/clickable.")

async def _pick_download_excel(page):
    """Return a locator for 'Download Excel'; fallback to 'Download CSV'."""
    print("📊 [FORMAT] Looking for download format options...")
    await page.wait_for_timeout(200)
    # Prioritize Excel format
    excel = page.get_by_text("Download Excel", exact=True)
    if await excel.count():
        print("✅ [FORMAT] Found 'Download Excel' option!")
        return excel.first
    
    # Try other Excel variations
    excel_labels = ["Download XLSX", "Download XLS", "Descargar Excel", "Descargar XLSX"]
    for label in excel_labels:
        loc = page.get_by_text(label, exact=True)
        if await loc.count():
            print(f"✅ [FORMAT] Found '{label}' option!")
            return loc.first
    
    print("⚠️ [FORMAT] Excel format not found, trying CSV...")
    # Fallback to CSV if Excel not available
    csv = page.get_by_text("Download CSV", exact=True)
    if await csv.count():
        print("✅ [FORMAT] Found 'Download CSV' option!")
        return csv.first
    
    csv_labels = ["Descargar CSV"]
    for label in csv_labels:
        loc = page.get_by_text(label, exact=True)
        if await loc.count():
            print(f"✅ [FORMAT] Found '{label}' option!")
            return loc.first
    
    raise PWTimeout("Dropdown did not contain 'Download Excel' or 'Download CSV'.")

# ---------- invoice-focused functions ----------
async def _open_invoices_from_sidebar(page) -> None:
    """Click the 'Invoices' item in the left sidebar to open the Invoices page."""
    print("📋 [INVOICES] Looking for Invoices link in sidebar...")
    candidates = [
        page.get_by_role("link", name="Invoices"),
        page.get_by_role("link", name=re.compile(r"\bInvoices\b", re.I)),
        page.locator('a:has-text("Invoices")'),
        page.locator('[role="navigation"] >> text=Invoices'),
        page.locator('nav >> text=Invoices'),
    ]
    for i, loc in enumerate(candidates):
        count = await loc.count()
        print(f"🔍 [INVOICES] Candidate {i+1}: Found {count} elements")
        if count:
            btn = loc.first
            if await btn.is_visible():
                print("✅ [INVOICES] Found visible Invoices link, clicking...")
                await btn.scroll_into_view_if_needed()
                await _wait(page, "before clicking sidebar → Invoices")
                await btn.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
                await _wait(page, "after landing on Invoices")
                print(f"✅ [INVOICES] Successfully navigated to Invoices page: {page.url}")
                return
    raise PWTimeout("Could not click 'Invoices' in the sidebar.")

async def _search_for_property(page, property_name: str) -> None:
    """Search for a specific property in the search bar."""
    print(f"🔍 [SEARCH] Searching for property: {property_name}")
    
    # Find the search input field
    search_input = page.locator('input[type="text"], input[placeholder*="search" i], input[placeholder*="Search" i]').first
    if await search_input.count() == 0:
        # Try alternative selectors
        search_input = page.locator('input').filter(has_text=re.compile(r"search", re.I)).first
    
    if await search_input.count() == 0:
        raise PWTimeout("Search input field not found")
    
    # Clear and fill the search field
    await search_input.click()
    await search_input.fill("")  # Clear existing text
    await search_input.fill(property_name)
    
    # Wait exactly 5 seconds after searching as requested
    print("⏳ [SEARCH] Waiting 5 seconds for search results to load...")
    await page.wait_for_timeout(5000)
    print(f"✅ [SEARCH] Successfully searched for: {property_name}")

async def _get_invoice_table_data(page) -> list[dict]:
    """Extract invoice table data for the current property."""
    print("📊 [TABLE] Extracting invoice table data...")
    
    # Wait for table to load
    await page.wait_for_timeout(2000)
    
    # Find the table rows (skip header)
    rows = await page.locator('table tbody tr, .table tbody tr, [role="row"]').all()
    
    invoices = []
    for i, row in enumerate(rows):
        try:
            # Extract data from each column
            cells = await row.locator('td, th').all()
            if len(cells) < 10:  # Skip if not enough columns
                continue
                
            invoice_data = {
                'row_index': i,
                'asset': await cells[1].text_content() if len(cells) > 1 else "",
                'upload_date': await cells[2].text_content() if len(cells) > 2 else "",
                'modified_date': await cells[3].text_content() if len(cells) > 3 else "",
                'issue_date': await cells[4].text_content() if len(cells) > 4 else "",
                'payment_date': await cells[5].text_content() if len(cells) > 5 else "",
                'account': await cells[6].text_content() if len(cells) > 6 else "",
                'invoice_reference': await cells[7].text_content() if len(cells) > 7 else "",
                'provider': await cells[8].text_content() if len(cells) > 8 else "",
                'company': await cells[9].text_content() if len(cells) > 9 else "",
                'service': await cells[11].text_content() if len(cells) > 11 else "",  # Service column
                'initial_date': await cells[12].text_content() if len(cells) > 12 else "",  # Initial date
                'final_date': await cells[13].text_content() if len(cells) > 13 else "",  # Final date
                'subtotal': await cells[14].text_content() if len(cells) > 14 else "",  # Subtotal
                'taxes': await cells[15].text_content() if len(cells) > 15 else "",  # Taxes
                'total': await cells[16].text_content() if len(cells) > 16 else "",  # Total
                'download_button': cells[0] if len(cells) > 0 else None,  # Download button (first column)
            }
            invoices.append(invoice_data)
        except Exception as e:
            print(f"⚠️ [TABLE] Error extracting row {i}: {e}")
            continue
    
    print(f"✅ [TABLE] Extracted {len(invoices)} invoice records")
    return invoices

async def _download_invoice_files(page, selected_invoices: list[dict], property_name: str) -> list[str]:
    """Download the selected invoice files and upload to Supabase."""
    print(f"📥 [DOWNLOAD] Downloading {len(selected_invoices)} invoices for {property_name}")
    
    downloaded_files = []
    context = page.context
    
    for i, invoice in enumerate(selected_invoices):
        try:
            if invoice['download_button']:
                print(f"📥 [DOWNLOAD] Downloading invoice {i+1}: {invoice['invoice_reference']}")
                
                # Correct approach: wait for new tab, switch to it, click download
                try:
                    # Get initial page count
                    initial_pages = len(context.pages)
                    print(f"📊 [PAGES] Initial page count: {initial_pages}")
                    
                    # Click the download button (this opens PDF in new tab)
                    await invoice['download_button'].click()
                    print("🖱️ [DOWNLOAD] Clicked download button, waiting for PDF tab...")
                    
                    # Wait for new page to appear (check every 500ms for 10 seconds)
                    new_page = None
                    for attempt in range(20):  # 20 attempts * 500ms = 10 seconds
                        await page.wait_for_timeout(500)
                        current_pages = len(context.pages)
                        print(f"📊 [PAGES] Attempt {attempt + 1}: {current_pages} pages")
                        
                        if current_pages > initial_pages:
                            new_page = context.pages[-1]  # Get the newest page
                            print(f"✅ [NEW PAGE] New tab detected: {new_page.url}")
                            break
                    
                    if not new_page:
                        print("❌ [ERROR] No new tab opened within 10 seconds")
                        continue
                    
                    # Wait for the new page to load
                    await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
                    
                    print(f"📄 [DOWNLOAD] PDF tab opened: {new_page.url}")
                    
                    # Wait for PDF to load (10 seconds)
                    print("⏳ [PDF] Waiting for PDF to load...")
                    await new_page.wait_for_timeout(10000)
                    
                    # Direct PDF download from URL (much more reliable)
                    print(f"📄 [PDF] PDF URL: {new_page.url}")
                    
                    try:
                        # Get PDF content directly from URL
                        response = await new_page.goto(new_page.url)
                        pdf_content = await response.body()
                        print(f"✅ [PDF] Downloaded PDF content: {len(pdf_content)} bytes")
                        
                        # Generate filename
                        suggested = f"invoice_{property_name}_{i+1}.pdf"
                        stem = Path(suggested).stem or f"invoice_{property_name}_{i+1}"
                        ext = Path(suggested).suffix or ".pdf"
                        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        filename = f"{stem}_{ts}{ext}"
                        
                        # Save locally first
                        local_path = Path("_debug/downloads") / filename
                        with open(local_path, 'wb') as f:
                            f.write(pdf_content)
                        size = local_path.stat().st_size if local_path.exists() else 0
                        print(f"💾 [DOWNLOAD] Saved locally: {local_path} ({size} bytes)")
                        
                        # Upload to Supabase
                        try:
                            # Clean filename for S3 compatibility and include flat name
                            clean_property_name = property_name.replace("º", "o").replace(" ", "_").replace("/", "_")
                            supabase_filename = f"{clean_property_name}/{filename}"
                            print(f"☁️ [UPLOAD] Uploading to Supabase: {supabase_filename}")
                            
                            # Upload to Supabase Storage
                            key = _upload_to_supabase_bytes(supabase_filename, pdf_content)
                            downloaded_files.append(key)
                            print(f"✅ [UPLOAD] Successfully uploaded to Supabase: {key}")
                            
                        except Exception as upload_error:
                            print(f"❌ [UPLOAD] Failed to upload to Supabase: {upload_error}")
                            downloaded_files.append(f"FAILED: {supabase_filename}")
                        
                        print(f"✅ [DOWNLOAD] Successfully processed invoice {i+1}")
                        
                    except Exception as pdf_error:
                        print(f"❌ [PDF] Failed to download PDF directly: {pdf_error}")
                        await new_page.screenshot(path=f"_debug/pdf_download_error_{i+1}.png")
                        print(f"📸 [DEBUG] PDF download error screenshot saved to _debug/pdf_download_error_{i+1}.png")
                        await new_page.close()
                        continue
                
                    
                    # Close the PDF tab and return to main tab
                    try:
                        await new_page.close()
                        print("🔄 [TAB] Closed PDF tab, returning to main tab")
                        await page.bring_to_front()
                        await page.wait_for_timeout(1000)
                    except Exception as close_error:
                        print(f"⚠️ [TAB] Error closing PDF tab: {close_error}")
                        # Continue anyway
                    
                except Exception as download_error:
                    print(f"❌ [DOWNLOAD] Download failed for invoice {i+1}: {download_error}")
                    # Take screenshot for debugging
                    try:
                        await page.screenshot(path=f"_debug/download_error_{i+1}.png")
                        print(f"📸 [DEBUG] Download error screenshot saved to _debug/download_error_{i+1}.png")
                    except:
                        print("📸 [DEBUG] Could not take screenshot (page closed)")
                    continue
                
        except Exception as e:
            print(f"❌ [DOWNLOAD] Error downloading invoice {i+1}: {e}")
            continue
    
    return downloaded_files

# ---------- Month selection ----------
def get_user_month_selection() -> tuple[str, str]:
    """
    Ask user to select 2 months for calculation.
    Returns tuple of (start_month, end_month) in YYYY-MM format.
    """
    print("📅 [MONTH SELECTION] Please select 2 months for calculation:")
    print("Available months (last 12 months):")
    
    from datetime import datetime, timedelta
    current_date = datetime.now()
    months = []
    
    for i in range(12):
        month_date = current_date - timedelta(days=30*i)
        month_str = month_date.strftime("%Y-%m")
        month_display = month_date.strftime("%B %Y")
        months.append((month_str, month_display))
        print(f"{i+1}. {month_display} ({month_str})")
    
    while True:
        try:
            choice1 = int(input("Enter first month number (1-12): ")) - 1
            if 0 <= choice1 < len(months):
                start_month = months[choice1][0]
                break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    while True:
        try:
            choice2 = int(input("Enter second month number (1-12): ")) - 1
            if 0 <= choice2 < len(months):
                end_month = months[choice2][0]
                break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    print(f"✅ [MONTH SELECTION] Selected months: {months[choice1][1]} to {months[choice2][1]}")
    return start_month, end_month

def get_user_month_selection_auto() -> tuple[str, str]:
    """
    Auto-select the last 2 months for testing purposes.
    Returns tuple of (start_month, end_month) in YYYY-MM format.
    """
    from datetime import datetime, timedelta
    current_date = datetime.now()
    
    # Get last 2 months
    last_month = current_date - timedelta(days=30)
    two_months_ago = current_date - timedelta(days=60)
    
    start_month = two_months_ago.strftime("%Y-%m")
    end_month = last_month.strftime("%Y-%m")
    
    print(f"📅 [AUTO SELECTION] Using last 2 months: {start_month} to {end_month}")
    return start_month, end_month

def filter_invoices_by_date_range(invoices: list[dict], start_month: str, end_month: str) -> list[dict]:
    """
    Filter invoices to only include those within the specified date range.
    Looks at both initial_date and final_date columns.
    """
    print(f"🔍 [FILTER] Filtering invoices for date range: {start_month} to {end_month}")
    
    filtered_invoices = []
    for invoice in invoices:
        initial_date = invoice.get('initial_date', '')
        final_date = invoice.get('final_date', '')
        
        # Try to parse dates and check if they fall within range
        try:
            from datetime import datetime
            
            # Parse initial date
            if initial_date:
                initial_parsed = datetime.strptime(initial_date.split()[0], '%Y-%m-%d')
                initial_month = initial_parsed.strftime('%Y-%m')
            else:
                initial_month = None
            
            # Parse final date
            if final_date:
                final_parsed = datetime.strptime(final_date.split()[0], '%Y-%m-%d')
                final_month = final_parsed.strftime('%Y-%m')
            else:
                final_month = None
            
            # Check if either date falls within our range
            if (initial_month and start_month <= initial_month <= end_month) or \
               (final_month and start_month <= final_month <= end_month):
                filtered_invoices.append(invoice)
                print(f"✅ [FILTER] Included invoice: {invoice.get('service', 'Unknown')} - {initial_date} to {final_date}")
            else:
                print(f"❌ [FILTER] Excluded invoice: {invoice.get('service', 'Unknown')} - {initial_date} to {final_date}")
                
        except Exception as e:
            print(f"⚠️ [FILTER] Error parsing dates for invoice: {e}")
            # If we can't parse dates, include it to be safe
            filtered_invoices.append(invoice)
    
    print(f"✅ [FILTER] Filtered to {len(filtered_invoices)} invoices from {len(invoices)} total")
    return filtered_invoices

# ---------- Cohere LLM integration ----------
def analyze_invoices_with_cohere(invoices: list[dict], start_month: str, end_month: str) -> dict:
    """
    Use Cohere LLM to analyze invoices and select the right ones.
    Returns selected invoices and calculation data.
    """
    print("🤖 [COHERE] Analyzing invoices with LLM...")
    print(f"🤖 [COHERE] Date range: {start_month} to {end_month}")
    
    try:
        import cohere
        from src.config import COHERE_API_KEY
        
        # Initialize Cohere client
        co = cohere.Client(COHERE_API_KEY)
        
        # Prepare invoice data for LLM analysis
        invoice_text = "Invoice Analysis Request:\n\n"
        invoice_text += f"I need to select the right invoices for utility bill calculation for the period {start_month} to {end_month}.\n"
        invoice_text += f"IMPORTANT: The period is {start_month} to {end_month} (e.g., 2025-05 to 2025-06 means May 2025 to June 2025).\n"
        invoice_text += "I need 2 electricity bills (monthly) and 1 water bill (every 2 months) from this period.\n\n"
        invoice_text += f"Available invoices (filtered by date range) - Total: {len(invoices)}:\n"
        
        for i, inv in enumerate(invoices):
            invoice_text += f"Row {i+1}:\n"
            invoice_text += f"  Service: {inv.get('service', 'N/A')}\n"
            invoice_text += f"  Issue Date: {inv.get('issue_date', 'N/A')}\n"
            invoice_text += f"  Initial Date: {inv.get('initial_date', 'N/A')}\n"
            invoice_text += f"  Final Date: {inv.get('final_date', 'N/A')}\n"
            invoice_text += f"  Total: {inv.get('total', 'N/A')}\n"
            invoice_text += f"  Provider: {inv.get('provider', 'N/A')}\n"
            invoice_text += f"  Company: {inv.get('company', 'N/A')}\n\n"
        
        invoice_text += f"\nOPERATIONAL LOGIC (for start of month calculations):\n"
        invoice_text += f"\nWATER: Find 1 bill that covers BOTH months of the period\n"
        invoice_text += f"- If calculating for {start_month} to {end_month} period\n"
        invoice_text += f"- Look for water bill that covers {start_month} AND {end_month} (any date range that includes both months)\n"
        invoice_text += f"\nELECTRICITY: Find 2 separate bills\n"
        invoice_text += f"- 1 bill that covers the first month of the period ({start_month})\n"
        invoice_text += f"- 1 bill that covers the second month of the period ({end_month})\n"
        invoice_text += f"- Each bill can have any date range as long as it covers its respective month\n"
        invoice_text += f"\nFLEXIBLE DATE MATCHING EXAMPLES:\n"
        invoice_text += f"- Water bill 15/06-15/08 covers July-August ✓\n"
        invoice_text += f"- Water bill 01/07-31/08 covers July-August ✓\n"
        invoice_text += f"- Water bill 20/07-20/09 covers July-August ✓\n"
        invoice_text += f"- Electricity 15/07-14/08 covers July ✓\n"
        invoice_text += f"- Electricity 01/08-31/08 covers August ✓\n"
        invoice_text += f"- Electricity 20/08-19/09 covers August ✓\n"
        invoice_text += f"\nThe goal is to find bills that actually cover the months you're calculating for, regardless of the specific dates.\n"
        invoice_text += f"\nIMPORTANT RULES:\n"
        invoice_text += f"- Only select bills that cover the months you're calculating for\n"
        invoice_text += f"- Do NOT substitute with older bills if the required bills are not available\n"
        invoice_text += f"- If bills are missing for the period, return empty arrays and explain what's missing\n"
        invoice_text += f"- Return the row numbers of selected invoices\n\n"
        invoice_text += f"Format your response as JSON with this structure:\n"
        invoice_text += f'{{"selected_electricity_rows": [row_numbers], "selected_water_rows": [row_numbers], "reasoning": "explanation", "missing_bills": "what is missing"}}'
        
        # Call Cohere API
        response = co.generate(
            model='command',
            prompt=invoice_text,
            max_tokens=800,
            temperature=0.1
        )
        
        # Parse LLM response
        llm_response = response.generations[0].text.strip()
        print(f"🤖 [COHERE] LLM Response: {llm_response}")
        
        # Try to parse JSON response
        import json
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Clean control characters that break JSON parsing
                json_str = json_str.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                # Remove multiple spaces
                json_str = re.sub(r'\s+', ' ', json_str)
                analysis = json.loads(json_str)
            else:
                # Try parsing the whole response
                llm_response_clean = llm_response.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                llm_response_clean = re.sub(r'\s+', ' ', llm_response_clean)
                analysis = json.loads(llm_response_clean)
            
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
            missing_bills = "Could not parse LLM response"
    
    except Exception as e:
        print(f"⚠️ [COHERE] Error with Cohere API: {e}, using fallback logic")
        selected_electricity_rows = []
        selected_water_rows = []
        reasoning = f"Cohere API error: {e}"
    
    # Fallback logic if LLM fails
    if not selected_electricity_rows and not selected_water_rows:
        print("🔄 [COHERE] Using fallback logic...")
        
        # Filter invoices by service type and date range
        from datetime import datetime
        
        # Parse the date range
        start_year, start_month_num = map(int, start_month.split('-'))
        end_year, end_month_num = map(int, end_month.split('-'))
        
        def is_in_date_range(invoice):
            try:
                # Try to parse initial_date or final_date
                date_str = invoice.get('initial_date', '') or invoice.get('final_date', '')
                if not date_str:
                    return False
                
                # Parse date (assuming DD/MM/YYYY format)
                if '/' in date_str:
                    day, month, year = map(int, date_str.split('/'))
                    invoice_date = datetime(year, month, 1)
                    
                    # Check if invoice date falls within the range
                    start_date = datetime(start_year, start_month_num, 1)
                    end_date = datetime(end_year, end_month_num, 1)
                    
                    return start_date <= invoice_date <= end_date
                return False
            except:
                return False
        
        # Filter by service type AND date range
        electricity_invoices = [inv for inv in invoices 
                              if inv.get('service', '').lower() in ['electricity', 'electric'] 
                              and is_in_date_range(inv)]
        water_invoices = [inv for inv in invoices 
                         if inv.get('service', '').lower() in ['water', 'agua'] 
                         and is_in_date_range(inv)]
        
        # Sort by final date (most recent first)
        electricity_invoices.sort(key=lambda x: x.get('final_date', ''), reverse=True)
        water_invoices.sort(key=lambda x: x.get('final_date', ''), reverse=True)
        
        # Select invoices and inform user about availability
        selected_electricity = electricity_invoices[:2]
        selected_water = water_invoices[:1]
        
        # Inform user about missing bills - be strict about not substituting
        missing_bills = []
        if not electricity_invoices:
            missing_bills.append("No electricity bills found in the specified period")
        elif len(electricity_invoices) < 2:
            missing_bills.append(f"Only {len(electricity_invoices)} electricity bill(s) found (expected 2)")
        
        if not water_invoices:
            missing_bills.append("No water bills found in the specified period")
        
        if missing_bills:
            print("⚠️ [WARNING] Missing bills:")
            for missing in missing_bills:
                print(f"  - {missing}")
            print("❌ [ERROR] Cannot proceed with calculation - required bills are missing!")
            print("ℹ️ [INFO] Please check if the correct months were selected or if bills are available")
        
        selected_invoices = selected_electricity + selected_water
        reasoning = f"Strict fallback: found {len(selected_electricity)} electricity and {len(selected_water)} water bills in date range. Missing: {', '.join(missing_bills) if missing_bills else 'None'}"
    
    else:
        # Use LLM selections
        selected_invoices = []
        
        # Get electricity invoices by row numbers
        for row_num in selected_electricity_rows:
            if 0 <= row_num-1 < len(invoices):
                selected_invoices.append(invoices[row_num-1])
        
        # Get water invoices by row numbers
        for row_num in selected_water_rows:
            if 0 <= row_num-1 < len(invoices):
                selected_invoices.append(invoices[row_num-1])
    
    # Calculate totals with better error handling
    total_electricity = 0.0
    total_water = 0.0
    
    for inv in selected_invoices:
        try:
            total_str = inv.get('total', '0')
            if total_str and total_str != 'N/A':
                # Clean the total string
                total_clean = total_str.replace('€', '').replace(',', '.').replace(' ', '').strip()
                if total_clean:
                    total_value = float(total_clean)
                    
                    service = inv.get('service', '').strip().lower()
                    print(f"🔍 [DEBUG] Service field: '{inv.get('service', '')}' -> cleaned: '{service}'")
                    
                    if service in ['electricity', 'electric']:
                        total_electricity += total_value
                        print(f"💰 [CALC] {service}: {total_str} -> {total_value}")
                    elif service in ['water', 'agua']:
                        total_water += total_value
                        print(f"💰 [CALC] {service}: {total_str} -> {total_value}")
                    elif service in ['gas', 'gas natural']:
                        print(f"💰 [CALC] {service}: {total_str} -> {total_value} (EXCLUDED from calculation)")
                    else:
                        print(f"💰 [CALC] {service}: {total_str} -> {total_value} (UNKNOWN service - excluded)")
        except (ValueError, TypeError) as e:
            print(f"⚠️ [CALC] Error parsing total '{inv.get('total', '')}': {e}")
            continue
    
    print(f"🤖 [COHERE] Analysis complete: €{total_electricity:.2f} electricity, €{total_water:.2f} water")
    print(f"🤖 [COHERE] Reasoning: {reasoning}")
    
    return {
        'selected_invoices': selected_invoices,
        'total_electricity': total_electricity,
        'total_water': total_water,
        'total_all': total_electricity + total_water,
        'reasoning': reasoning
    }

# ---------- main invoice flow ----------
async def process_property_invoices(property_name: str, start_month: str, end_month: str) -> dict:
    """
    Process invoices for a single property:
    1. Search for property
    2. Extract table data
    3. Filter by date range
    4. Use LLM to select invoices
    5. Download selected invoices
    6. Calculate overuse
    """
    print(f"🏠 [PROPERTY] Processing invoices for: {property_name}")
    print(f"📅 [PROPERTY] Date range: {start_month} to {end_month}")
    
    user_data = str(Path("./.chrome-profile").resolve())
    Path(user_data).mkdir(exist_ok=True)
    Path("_debug").mkdir(exist_ok=True)
    Path("_debug/downloads").mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("🌐 [BROWSER] Launching browser...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=True,
            slow_mo=0,
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
                "--disable-images",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
            accept_downloads=True,
            ignore_https_errors=True,
        )
        context.set_default_timeout(120_000)
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # 1) Login
            await _ensure_logged_in(page)
            
            # 2) We're already on the accounting dashboard - ready to search for invoices
            print("✅ [ACCOUNTING] Ready to search for invoices on accounting dashboard")
            
            # 3) Search for property
            await _search_for_property(page, property_name)
            
            # 4) Extract table data
            invoices = await _get_invoice_table_data(page)
            
            if not invoices:
                print("❌ [ERROR] No invoice data found")
                return {
                    'property_name': property_name,
                    'date_range': f"{start_month} to {end_month}",
                    'room_count': 0,
                    'allowance': 0.0,
                    'total_electricity': 0.0,
                    'total_water': 0.0,
                    'total_cost': 0.0,
                    'overuse': 0.0,
                    'selected_invoices': [],
                    'downloaded_files': [],
                    'llm_reasoning': "No invoice data found"
                }
            
            print(f"📊 [INVOICES] Found {len(invoices)} total invoices")
            
            # 5) Use LLM to analyze ALL invoices and select the right ones
            print("🤖 [LLM] Analyzing all invoices with Cohere...")
            analysis = analyze_invoices_with_cohere(invoices, start_month, end_month)
            
            # 7) Download selected invoices
            downloaded_files = await _download_invoice_files(page, analysis['selected_invoices'], property_name)
            
            # 8) Calculate overuse (using existing logic)
            from src.polaroo_process import ADDRESS_ROOM_MAPPING, ROOM_LIMITS, SPECIAL_LIMITS
            
            room_count = ADDRESS_ROOM_MAPPING.get(property_name, 1)
            allowance = SPECIAL_LIMITS.get(property_name, ROOM_LIMITS.get(room_count, 50))
            
            # Double allowances for 2-month period
            allowance *= 2
            
            total_cost = analysis['total_all']
            overuse = max(0, total_cost - allowance)
            
            result = {
                'property_name': property_name,
                'date_range': f"{start_month} to {end_month}",
                'room_count': room_count,
                'allowance': allowance,
                'total_electricity': analysis['total_electricity'],
                'total_water': analysis['total_water'],
                'total_cost': total_cost,
                'overuse': overuse,
                'selected_invoices': analysis['selected_invoices'],
                'downloaded_files': downloaded_files,
                'llm_reasoning': analysis.get('reasoning', 'No reasoning provided')
            }
            
            print(f"✅ [PROPERTY] Completed processing for {property_name}: €{total_cost:.2f} total, €{overuse:.2f} overuse")
            return result
            
        except Exception as e:
            print(f"❌ [ERROR] Failed to process {property_name}: {e}")
            raise
        finally:
            await context.close()

async def process_first_10_properties() -> list[dict]:
    """Process invoices for the first 10 properties in Book 1."""
    from src.polaroo_process import USER_ADDRESSES
    
    # Get month selection from user
    start_month, end_month = get_user_month_selection()
    
    first_10 = USER_ADDRESSES[:10]
    results = []
    
    for property_name in first_10:
        try:
            result = await process_property_invoices(property_name, start_month, end_month)
            results.append(result)
        except Exception as e:
            print(f"❌ [ERROR] Failed to process {property_name}: {e}")
            results.append({
                'property_name': property_name,
                'date_range': f"{start_month} to {end_month}",
                'error': str(e),
                'total_cost': 0,
                'overuse': 0
            })
    
    return results

async def process_first_10_properties_auto() -> list[dict]:
    """Process invoices for the first 10 properties in Book 1 with auto month selection."""
    from src.polaroo_process import USER_ADDRESSES
    
    # Auto-select last 2 months
    start_month, end_month = get_user_month_selection_auto()
    
    first_10 = USER_ADDRESSES[:10]
    results = []
    
    for property_name in first_10:
        try:
            result = await process_property_invoices(property_name, start_month, end_month)
            results.append(result)
        except Exception as e:
            print(f"❌ [ERROR] Failed to process {property_name}: {e}")
            results.append({
                'property_name': property_name,
                'date_range': f"{start_month} to {end_month}",
                'error': str(e),
                'total_cost': 0,
                'overuse': 0
            })
    
    return results

# ---------- main flow ----------
async def download_report_bytes() -> tuple[bytes, str]:
    """
    Headful + persistent Chrome profile with deliberate waits:
      /login → dashboard → sidebar 'Report' → set 'Last month' → Download → Excel
      → save locally (timestamped) → upload to Supabase Storage.
    """
    print("🚀 [START] Starting Polaroo report download process...")
    Path("_debug").mkdir(exist_ok=True)
    Path("_debug/downloads").mkdir(parents=True, exist_ok=True)
    user_data = str(Path("./.chrome-profile").resolve())
    Path(user_data).mkdir(exist_ok=True)

    async with async_playwright() as p:
        print("🌐 [BROWSER] Launching browser...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=True,  # headless for production
            slow_mo=0,       # no manual Resume needed
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
                "--disable-images",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--disable-blink-features=AutomationControlled",
                "--exclude-switches=enable-automation",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ],
            accept_downloads=True,
            ignore_https_errors=True,
        )
        context.set_default_timeout(120_000)
        page = context.pages[0] if context.pages else await context.new_page()

        # Add stealth measures to bypass Cloudflare
        print("🥷 [STEALTH] Adding anti-detection measures...")
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        # Safe debug listeners
        page.on("console",       lambda m: print("🌐 [BROWSER]", m.type, m.text))
        page.on("requestfailed", lambda r: print("❌ [BROWSER] REQ-FAILED:", r.url, r.failure or ""))
        page.on("response",      lambda r: print("📡 [BROWSER] HTTP", r.status, r.url) if r.status >= 400 else None)

        try:
            # 1) Login / dashboard
            print("🔐 [STEP 1/4] Starting login process...")
            try:
                await _ensure_logged_in(page)
            except Exception as e:
                if "403" in str(e) or "401" in str(e) or "cloudflare" in str(e).lower():
                    print("🛡️ [CLOUDFLARE] Detected Cloudflare protection, trying alternative approach...")
                    # Try with different user agent and settings
                    await page.set_extra_http_headers({
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    })
                    await page.wait_for_timeout(5000)  # Wait longer
                    await _ensure_logged_in(page)
                else:
                    raise

            # 2) Open Report
            print("📊 [STEP 2/4] Opening Report page...")
            await _open_report_from_sidebar(page)

            # 3) Set Last month
            print("📅 [STEP 3/4] Setting date range to Last month...")
            await _set_date_range_last_month(page)

            # 4) Download → Excel (preferred) or CSV
            print("📥 [STEP 4/4] Starting download process...")
            await _open_download_menu(page)
            item = await _pick_download_excel(page)

            print("💾 [DOWNLOAD] Initiating file download...")
            await _wait(page, "before clicking Download item")
            async with page.expect_download() as dl_info:
                await item.click()
            dl = await dl_info.value

            # --- timestamped filename (UTC) ---
            suggested = dl.suggested_filename or "polaroo_report.xlsx"
            stem = Path(suggested).stem or "polaroo_report"
            ext = Path(suggested).suffix or ".xlsx"
            ts  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            filename = f"{stem}_{ts}{ext}"

            # Save locally for debugging/inspection
            local_path = Path("_debug/downloads") / filename
            await dl.save_as(str(local_path))
            size = local_path.stat().st_size if local_path.exists() else 0
            print(f"💾 [SAVED] {local_path} ({size} bytes)")

            # Read bytes for upload
            data = local_path.read_bytes()

            # Upload to Supabase Storage (same timestamped name)
            print("☁️ [UPLOAD] Uploading to Supabase...")
            key = _upload_to_supabase_bytes(filename, data)
            print(f"☁️ [UPLOAD] Successfully uploaded to: {STORAGE_BUCKET}/{key}")

            await _wait(page, "after download+upload")
            print("✅ [SUCCESS] Report download and upload completed successfully!")
            
        except Exception as e:
            print(f"❌ [ERROR] Scraping failed: {e}")
            # Take a screenshot for debugging
            await page.screenshot(path="_debug/error_screenshot.png")
            print("📸 [DEBUG] Error screenshot saved to _debug/error_screenshot.png")
            raise
        finally:
            await context.close()
            print("🔚 [CLEANUP] Browser closed")
            
        return data, filename


def download_report_sync() -> tuple[bytes, str]:
    """Synchronous wrapper for download_report_bytes that works with FastAPI."""
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in a running loop, we need to run in a thread with a new event loop
            import concurrent.futures
            import threading
            
            def run_in_thread():
                # Create a new event loop in this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(download_report_bytes())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        else:
            # No running loop, safe to use asyncio.run
            return asyncio.run(download_report_bytes())
    except RuntimeError:
        # Fallback to asyncio.run
        return asyncio.run(download_report_bytes())
