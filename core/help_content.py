HELP_MAIN_ADMIN = """<b>📖 Help — Admin</b>

<b>➕ Accounts</b>
/add — Add single account
/bulkadd — Bulk import (user:pass)
/extractcsv — Import from CSV
/delete — Delete (filter or ID)
/bulkdelete — Bulk delete

<b>📋 Browse</b>
/list — Browse with filters
/search — Search with filters
/getid — View by ID

<b>💰 Sell</b>
/sell — Sell available account
/bulksell — Bulk sell
/sales — View all sales
/sale — Sale detail
/markpaid — Mark paid
/voidsale — Void sale

<b>📊 Status</b>
/marksold — 🔴 Mark sold
/markunsold — 🟢 Mark available
/markpendingpayment — 🟡 Mark pending

<b>📂 Other</b>
/preview — Preview for buyer
/categories — List categories
/addcategory — Create category
/deletecategory — Delete category
/inventory — Stock overview
/buyers — List buyers
/buyer — Buyer history
/report — Revenue reports

<b>👤 Sellers</b>
/addseller — Register seller
/removeseller — Remove seller
/listsellers — List sellers

<b>⚙️ Utils</b>
/export — Export CSV
/backup — DB backup
/ping — Health check
/help — This help"""

HELP_MAIN_SELLER = """<b>📖 Help — Seller</b>

<b>📋 Browse</b>
/list — Browse with filters
/search — Search with filters
/getid — View by ID

<b>💰 Sell</b>
/sell — Sell available account
/bulksell — Bulk sell
/sales — View your sales
/sale — Sale detail
/markpaid — Mark paid

<b>📊 Status</b>
/marksold — 🔴 Mark sold
/markunsold — 🟢 Mark available
/markpendingpayment — 🟡 Mark pending

<b>📂 Other</b>
/preview — Preview for buyer
/categories — List categories
/inventory — Stock overview
/buyers — List buyers
/buyer — Buyer history

<b>⚙️ Utils</b>
/ping — Health check
/help — This help"""

HELP_TOPICS = {
    "sell": """<b>💰 Selling Accounts</b>

<b>/sell</b>
1. Shows 🟢 available accounts
2. Filter: status, category, or ID
3. Tap account to select
4. Pick buyer (from list or type new)
5. Enter price
6. Pick status: 🟢 Sold or 🟡 Pending
7. Confirm

<b>/bulksell</b>
• <b>Select:</b> tap accounts → Done
• <b>Number:</b> enter count → auto-pick
Then same flow: buyer → price → status

<b>/markpaid</b> — Pick pending sale → mark paid
<b>/voidsale</b> — Cancel sale → account back to stock""",

    "status": """<b>📊 Account Status</b>

🟢 <b>available</b> — Can be sold
🔴 <b>sold</b> — Already sold
🟡 <b>pending_payment</b> — Sold, waiting for payment

Commands:
/marksold 123 — set 🔴
/markunsold 123 — set 🟢
/markpendingpayment 123 — set 🟡

Only 🟢 accounts show in /sell and /bulksell.
Pending payment reminder sent every 4 hours.""",

    "filter": """<b>🔍 Filtering System</b>

Used in /list, /sell, /bulksell, /delete, /inventory

Buttons:
📋 All — show everything
🟢 Available — only unsold
🔴 Sold — only sold
🟡 Pending — only pending payment
📂 Category — pick category
🔢 By ID — enter ID(s)

For /sell and /bulksell: only 🟢 available shown by default.
Pagination: 5 results per page, use ⬅️ ➡️.""",

    "search": """<b>🔎 Searching</b>

<b>/search</b> — tap type → enter value → results

Types:
👤 Username — partial match
🔑 Password — partial match
📂 Category — tap from list
📊 Status — tap 🟢/🔴/🟡
👤 Buyer — buyer name
🏷️ Tag — sale tag
📝 Notes — notes content
🔍 General — username+password+notes
🔢 By ID — comma-separated IDs

Status search shows 2 results + count.""",

    "add": """<b>➕ Adding Accounts</b>

<b>/add</b> — 10-step wizard:
Username → Password → Email → Email Pass → 2FA → Verified → Notes → Category → Confirm

<b>/bulkadd</b> — Paste lines:
Select category → send lines (user:pass) → /done

<b>/extractcsv</b> — CSV import:
Select category → upload file → map columns → preview → import
For 2FA/Verified: Yes/No buttons or select CSV column""",

    "delete": """<b>🗑️ Deleting Accounts</b>

<b>/delete</b> — Two ways:
• Pass ID: /delete 123
• No args: shows filter menu → tap account → confirm

<b>/bulkdelete</b> — Enter:
• Comma-separated IDs: 1,2,3
• Category name: deletes all in that category""",

    "preview": """<b>📂 Preview for Buyer</b>

<b>/preview</b>
1. Pick category (or All)
2. Enter count
3. Shows accounts with Reddit links
4. Tap "Sell" button to quick-sell""",

    "categories": """<b>📂 Categories</b>

<b>/categories</b> — List all with counts
<b>/addcategory Finance</b> — Create new
<b>/deletecategory Finance</b> — Delete (accounts move to uncategorized)""",

    "sales": """<b>📈 Sales</b>

<b>/sales</b> — List with filters
🟡 Pending / ✅ Paid / 📋 All
Admin sees all, seller sees own.

<b>/sale 123</b> — Full detail with actions:
✅ Mark Paid / 🟡 Mark Pending / 🔴 Mark Unsold / ♻️ Void""",

    "inventory": """<b>📦 Inventory</b>

<b>/inventory</b> — Overview:
🟢 Available / 🔴 Sold / 🟡 Pending per category
Total revenue and pending amount

Filter by status or category from the view.""",

    "buyers": """<b>👥 Buyers</b>

<b>/buyers</b> — List all with totals
<b>/buyer John</b> — Purchase history for buyer""",

    "reports": """<b>📊 Reports</b>

<b>/report</b> — Pick period:
Today / This Week / This Month / All Time

Shows: revenue, sales count, pending, per-seller, per-category""",

    "sellers": """<b>👤 Seller Management</b>

<b>/addseller 123 Alice</b> — Register
<b>/removeseller 123</b> — Remove
<b>/listsellers</b> — List all with stats""",

    "settings": """<b>⚙️ Settings</b>

Config via .env:
BOT_TOKEN, ADMIN_USER_ID, DAILY_REPORT_HOUR, WEEKLY_REPORT_DAY, TIMEZONE

Auto notifications:
📊 Daily report
📊 Weekly report
🟡 Pending payment reminder (every 4h)""",
}
