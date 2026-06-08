HELP_MAIN_ADMIN = """<b>📖 Help — Admin</b>

<b>➕ Account Management</b>
/add — Add single account (wizard)
/bulkadd — Bulk import accounts
/extractcsv — Import from CSV file
/delete — Delete account (with filters)
/bulkdelete — Bulk delete accounts

<b>📋 Browsing</b>
/list — Browse accounts with filters
/search — Search with multi-filters
/getid — View account by ID

<b>💰 Selling</b>
/sell — Sell an account (available only)
/bulksell — Bulk sell (select or by number)
/sales — View all sales
/sale — Sale detail by ID
/markpaid — Toggle payment status
/voidsale — Void a sale (returns to stock)
/marksold — Mark account 🔴 sold
/markunsold — Mark account 🟢 available
/markpendingpayment — Mark account 🟡 pending

<b>📂 Preview</b>
/preview — Pull accounts for buyer

<b>📂 Categories</b>
/categories — List categories
/addcategory — Create category
/deletecategory — Delete category

<b>📦 Inventory</b>
/inventory — Stock overview with filters

<b>👥 Buyers</b>
/buyers — List all buyers
/buyer — Buyer purchase history

<b>📊 Reports</b>
/report — Revenue reports

<b>👤 Seller Management</b>
/addseller — Register seller
/removeseller — Remove seller
/listsellers — List all sellers

<b>⚙️ Utilities</b>
/export — Export accounts CSV
/backup — Download DB backup
/ping — Health check
/help — Show this help"""

HELP_MAIN_SELLER = """<b>📖 Help — Seller</b>

<b>📋 Browsing</b>
/list — Browse accounts with filters
/search — Search with multi-filters
/getid — View account by ID

<b>💰 Selling</b>
/sell — Sell an account (available only)
/bulksell — Bulk sell (select or by number)
/sales — View your sales
/sale — Sale detail by ID
/markpaid — Toggle payment status
/marksold — Mark account 🔴 sold
/markunsold — Mark account 🟢 available
/markpendingpayment — Mark account 🟡 pending

<b>📂 Preview</b>
/preview — Pull accounts for buyer

<b>📂 Categories</b>
/categories — List categories

<b>📦 Inventory</b>
/inventory — Stock overview with filters

<b>👥 Buyers</b>
/buyers — List buyers
/buyer — Buyer purchase history

<b>⚙️ Utilities</b>
/ping — Health check
/help — Show this help"""

HELP_TOPICS = {
    "sell": """<b>💰 Help — Selling Accounts</b>

<b>/sell</b> — Sell a single account
1. Bot shows 🟢 available accounts with filters
2. Filter by status, category, or ID
3. Tap an account to select
4. Pick buyer from previous buyers or type new
5. Enter price (required)
6. Choose 🟢 Sold or 🟡 Pending Payment
7. Confirm — receipt sent

<b>/bulksell</b> — Sell multiple accounts
Choose mode:
• <b>Select:</b> tap accounts to toggle, then Done
• <b>Number:</b> enter how many, auto-picks available

Then: pick buyer → enter price → choose status → confirm

<b>/markpaid</b> — Toggle payment status
Shows pending sales — select one to mark as paid.

<b>/voidsale</b> — (Admin) Cancel a sale
Account returns to available stock.

<b>/marksold &lt;id&gt;</b> — Mark account 🔴 sold
<b>/markunsold &lt;id&gt;</b> — Mark account 🟢 available
<b>/markpendingpayment &lt;id&gt;</b> — Mark 🟡 pending""",

    "preview": """<b>📂 Help — Preview Accounts</b>

<b>/preview</b> — Pull accounts for buyer preview
1. Select a category (or All)
2. Enter how many accounts to pull
3. Bot shows accounts with Reddit profile links
4. Each has a "Sell" button for quick selling""",

    "accounts": """<b>➕ Help — Account Management</b>

<b>/add</b> — Add single account (wizard)
Username → Password → Email → Email Pass → 2FA → Verified → Notes → Category → Confirm

<b>/bulkadd</b> — Bulk import
Select category → paste lines (user:pass) → /done

<b>/extractcsv</b> — CSV import
Select category → upload CSV → map columns → preview → import
For 2FA/Verified: choose Yes/No or select from CSV column

<b>/delete</b> — Delete account
Pass ID directly: /delete 123
Or use filters: browse → tap account → confirm

<b>/bulkdelete</b> — Bulk delete
Enter IDs (comma-separated) or category name → confirm""",

    "search": """<b>🔎 Help — Search</b>

<b>/search</b> — Search with multi-filters
1. Tap a search type button (with emojis)
2. Enter the search value
3. Results shown in compact format

<b>Search types:</b>
👤 Username — partial match
🔑 Password — partial match
📂 Category — exact name (tap from list)
📊 Status — 🟢 available / 🔴 sold / 🟡 pending (tap from list)
👤 Buyer — buyer name
🏷️ Tag — sale tag
📝 Notes — notes content
🔍 General — searches username, password, and notes
🔢 By ID — enter ID(s), comma-separated

<b>Multi-filter:</b> Category shows all accounts, then filter further by status or ID.""",

    "categories": """<b>📂 Help — Categories</b>

<b>/categories</b> — List all with account counts and default price

<b>/addcategory</b> — Create new category
Usage: /addcategory Finance

<b>/deletecategory</b> — Delete category
Accounts move to 'uncategorized'.""",

    "sales": """<b>📈 Help — Sales</b>

<b>/sales</b> — View sales list
Admin sees all, seller sees own.
Filter: 🟡 Pending / ✅ Paid / 📋 All

<b>/sale &lt;id&gt;</b> — Sale detail
Shows full receipt with actions:
• ✅ Mark Paid
• 🟡 Mark Pending
• 🔴 Mark Unsold (voids sale)
• ♻️ Void""",

    "buyers": """<b>👥 Help — Buyers</b>

<b>/buyers</b> — List all buyers
Shows total spent and purchase count.
Admin sees all, seller sees own.

<b>/buyer &lt;name&gt;</b> — Buyer history
Usage: /buyer john_doe""",

    "inventory": """<b>📦 Help — Inventory</b>

<b>/inventory</b> — Stock overview
Shows per-category breakdown:
🟢 Available / 🔴 Sold / 🟡 Pending Payment
Total revenue and pending amount

Filter by status or category from the inventory view.""",

    "reports": """<b>📊 Help — Reports</b>

<b>/report</b> — Revenue reports (Admin only)
Shows by period: Today / This Week / This Month / All Time
Includes:
💰 Total revenue
📈 Sales count
💳 Pending payments
📦 Inventory: available / sold / pending
Per-seller and per-category breakdown""",

    "sellers": """<b>👤 Help — Seller Management</b>

<b>/addseller</b> — Register a seller
Usage: /addseller 123456789 Alice

<b>/removeseller</b> — Soft-delete
Usage: /removeseller 123456789

<b>/listsellers</b> — List all with sales + earnings""",

    "statuses": """<b>📊 Help — Account Statuses</b>

🟢 <b>available</b> — Ready to sell
🔴 <b>sold</b> — Sold to buyer
🟡 <b>pending_payment</b> — Sold, awaiting payment

Use /marksold, /markunsold, /markpendingpayment to change status.

Only 🟢 available accounts appear in sell flows.""",

    "settings": """<b>⚙️ Help — Settings</b>

Bot configuration via .env:
 BOT_TOKEN — Telegram bot token
 ADMIN_USER_ID — Admin Telegram ID
 DAILY_REPORT_HOUR — Report hour (0-23)
 WEEKLY_REPORT_DAY — Report day
 TIMEZONE — Timezone (default: Asia/Kolkata)

Automatic notifications:
📊 Daily report at configured hour
📊 Weekly report on configured day
🟡 Pending payment reminder every 4 hours""",
}
