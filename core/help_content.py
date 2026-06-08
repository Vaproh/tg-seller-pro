HELP_MAIN_ADMIN = """<b>📖 Help — Admin</b>

<b>Account Management</b>
/add — Add single account (wizard)
/bulkadd — Bulk import accounts
/extractcsv — Import from CSV file
/delete — Delete account
/bulkdelete — Bulk delete accounts

<b>Browsing</b>
/list — Browse accounts
/search — Search accounts
/getid — View account by ID

<b>Selling</b>
/sell — Sell an account
/bulksell — Bulk sell to one buyer
/sales — View sales
/sale — Sale detail
/markpaid — Mark payment received
/voidsale — Void a sale

<b>Preview</b>
/preview — Pull accounts for buyer

<b>Categories</b>
/categories — List categories
/addcategory — Create category
/deletecategory — Delete category

<b>Inventory</b>
/inventory — Stock overview by status

<b>Buyers</b>
/buyers — List all buyers
/buyer — Buyer purchase history

<b>Reports</b>
/report — Revenue reports

<b>Seller Management</b>
/addseller — Register seller
/removeseller — Remove seller
/listsellers — List all sellers

<b>Utilities</b>
/export — Export accounts CSV
/backup — Download DB backup
/ping — Health check
/help — Show this help"""

HELP_MAIN_SELLER = """<b>📖 Help — Seller</b>

<b>Browsing</b>
/list — Browse accounts
/search — Search accounts
/getid — View account by ID

<b>Selling</b>
/sell — Sell an account
/bulksell — Bulk sell to one buyer
/sales — View your sales
/sale — Sale detail
/markpaid — Mark payment received

<b>Preview</b>
/preview — Pull accounts for buyer

<b>Categories</b>
/categories — List categories

<b>Inventory</b>
/inventory — Stock overview by status

<b>Buyers</b>
/buyers — List buyers
/buyer — Buyer purchase history

<b>Utilities</b>
/ping — Health check
/help — Show this help"""

HELP_TOPICS = {
    "sell": """<b>📖 Help — Selling Accounts</b>

<b>/sell</b> — Sell a single account
1. Bot shows available accounts
2. Select one to sell
3. Enter buyer name
4. Enter price (auto-filled from category default)
5. Add optional tags
6. Confirm — receipt sent

<b>/bulksell</b> — Sell multiple accounts to one buyer
1. Enter buyer name
2. Enter price per account
3. Select accounts to sell
4. Confirm

<b>/markpaid</b> — Mark pending sale as paid
Shows list of pending sales — select one to toggle.

<b>/voidsale</b> — (Admin only) Cancel a sale
Account returns to active stock.""",

    "preview": """<b>📖 Help — Preview Accounts</b>

<b>/preview</b> — Pull accounts for buyer preview
1. Select a category
2. Enter how many accounts to pull
3. Bot shows accounts with Reddit profile links
4. Each account has a "Sell" button for quick selling""",

    "accounts": """<b>📖 Help — Account Management</b>

<b>/add</b> — Add single account (10-step wizard)
Username → Password → Email → Email Pass → 2FA → Verified → Notes → Category → Confirm

<b>/bulkadd</b> — Bulk import
Select category → paste lines (user:pass) → /done

<b>/extractcsv</b> — CSV import
Select category → upload CSV → map columns → preview → import

<b>/delete</b> — Delete account
Shows list → select → confirm

<b>/bulkdelete</b> — Bulk delete
Enter IDs or category name → confirm""",

    "search": """<b>📖 Help — Search</b>

<b>/search</b> — Search with filters
1. Tap a search type button
2. Enter the search value
3. Results shown

<b>Search types:</b>
• Username — partial match
• Password — partial match
• Category — exact name
• Status — active/sold/banned/locked/restricted
• Buyer — buyer name
• Tag — sale tag
• Notes — notes content
• General — searches username, password, and notes""",

    "categories": """<b>📖 Help — Categories</b>

<b>/categories</b> — List all with account counts

<b>/addcategory</b> — Create new category
Usage: /addcategory Finance

<b>/deletecategory</b> — Delete category
Moves accounts to 'uncategorized'.""",

    "sales": """<b>📖 Help — Sales</b>

<b>/sales</b> — View sales list
Admin sees all, seller sees own.
Filter: All / Pending / Paid

<b>/sale</b> — Sale detail
Enter sale ID for full info.""",

    "buyers": """<b>📖 Help — Buyers</b>

<b>/buyers</b> — List all buyers
Shows total spent and purchase count.
Admin sees all, seller sees own.

<b>/buyer</b> — Buyer history
Usage: /buyer john_doe""",

    "inventory": """<b>📖 Help — Inventory</b>

<b>/inventory</b> — Stock overview
Shows per-category breakdown:
• Active accounts
• Sold accounts
• Banned/Locked/Restricted
• Total value""",

    "reports": """<b>📖 Help — Reports</b>

<b>/report</b> — Revenue reports (Admin only)
Shows by period: Today / This Week / This Month / All Time
Includes:
• Total revenue
• Sales count
• Pending payments
• Per-seller breakdown
• Per-category breakdown""",

    "sellers": """<b>📖 Help — Seller Management</b>

<b>/addseller</b> — Register a seller
Usage: /addseller 123456789 Alice

<b>/removeseller</b> — Soft-delete
Usage: /removeseller 123456789

<b>/listsellers</b> — List all with sales + earnings""",

    "settings": """<b>📖 Help — Settings</b>

Bot configuration via .env:
• BOT_TOKEN — Telegram bot token
• ADMIN_USER_ID — Admin Telegram ID
• BOT_NAME — Bot display name
• SERVICE_NAME — Service name
• DAILY_REPORT_HOUR — Report hour (0-23)
• WEEKLY_REPORT_DAY — Report day
• TIMEZONE — Timezone (default: Asia/Kolkata)""",
}
