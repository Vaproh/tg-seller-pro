HELP_MAIN_ADMIN = """<b>📖 Help — Admin</b>

<b>➕ Add Accounts</b>
/add — Add one account
/bulkadd — Add many at once
/extractcsv — Import from Excel file
/delete — Delete account
/bulkdelete — Delete many

<b>📋 Find Accounts</b>
/list — See all accounts
/search — Find specific ones
/getid — See one account

<b>💰 Sell</b>
/sell — Sell one account
/bulksell — Sell many at once
/sales — See all sales
/sale — See one sale
/markpaid — Mark as paid
/voidsale — Cancel a sale
/marksold — Mark 🔴 sold
/markunsold — Mark 🟢 available
/markpendingpayment — Mark 🟡 waiting for money
/editsale — Edit sale details

<b>📂 Other</b>
/preview — Show accounts to buyer
/categories — See all categories
/addcategory — Make new category
/deletecategory — Remove category
/inventory — What's in stock
/buyers — See all buyers
/buyer — See one buyer's orders
/report — Money report

<b>👤 Team</b>
/addseller — Add team member
/removeseller — Remove team member
/listsellers — See team

<b>⚙️ Tools</b>
/export — Download Excel file
/backup — Download database
/ping — Check if bot works
/help — This menu

Type <b>/help command</b> for details on any command.
Example: <b>/help sell</b>"""

HELP_MAIN_SELLER = """<b>📖 Help — Seller</b>

<b>📋 Find Accounts</b>
/list — See all accounts
/search — Find specific ones
/getid — See one account

<b>💰 Sell</b>
/sell — Sell one account
/bulksell — Sell many at once
/sales — See your sales
/sale — See one sale
/markpaid — Mark as paid
/marksold — Mark 🔴 sold
/markunsold — Mark 🟢 available
/markpendingpayment — Mark 🟡 waiting for money
/editsale — Edit sale details

<b>📂 Other</b>
/preview — Show accounts to buyer
/categories — See all categories
/inventory — What's in stock
/buyers — See all buyers
/buyer — See one buyer's orders

<b>⚙️ Tools</b>
/ping — Check if bot works
/help — This menu

Type <b>/help command</b> for details on any command.
Example: <b>/help sell</b>"""

HELP_TOPICS = {
    "sell": """<b>💰 /sell — Sell an Account</b>

<b>What it does:</b>
Lets you sell an account to a buyer.

<b>How to use:</b>
1. Type /sell
2. Pick mode:
   • <b>Pick account:</b> tap to select one
   • <b>Pick any:</b> auto-picks one available account
3. Pick a buyer or type their name
4. Type the price
5. Pick: 🟢 Sold or 🟡 Waiting for money
6. Confirm

<b>Notes:</b>
- Only 🟢 available accounts show up
- Price must be typed (no skipping)
- Buyer names are saved for next time""",

    "bulksell": """<b>💰 /bulksell — Sell Many Accounts</b>

<b>What it does:</b>
Sell multiple accounts to one buyer at once.

<b>How to use:</b>
1. Type /bulksell
2. Pick mode:
   • <b>Select:</b> tap accounts to pick them
   • <b>Number:</b> type how many (auto-picks available accounts)
3. Pick buyer
4. Type price per account
5. Pick status: 🟢 or 🟡
6. Confirm

<b>Notes:</b>
- Tap accounts to toggle selection
- Use ⬅️ ➡️ to go between pages
- Same flow as /sell but for multiple accounts""",

    "sales": """<b>📈 /sales — View Sales</b>

<b>What it does:</b>
Shows all your sales in a list.

<b>How to use:</b>
Type /sales

<b>Filter by:</b>
🟡 Pending — waiting for money
✅ Paid — money received
📋 All — everything

Use ⬅️ ➡️ to go between pages.""",

    "sale": """<b>🧾 /sale — View One Sale</b>

<b>What it does:</b>
Shows full details of one sale.

<b>How to use:</b>
Type /sale 123
(replace 123 with the sale number)

<b>You can:</b>
✅ Mark as paid
🟡 Mark as pending
🔴 Mark as unsold (cancel)
♻️ Void (delete sale)""",

    "markpaid": """<b>💳 /markpaid — Mark Payment</b>

<b>What it does:</b>
Shows pending sales, lets you mark one as paid.

<b>How to use:</b>
Type /markpaid
Tap the sale you got paid for""",

    "marksold": """<b>🔴 /marksold — Mark Sold</b>

<b>What it does:</b>
Marks an account as 🔴 sold.

<b>How to use:</b>
Type /marksold 123
(or multiple: /marksold 1,2,3)""",

    "markunsold": """<b>🟢 /markunsold — Mark Available</b>

<b>What it does:</b>
Makes an account available to sell again.

<b>How to use:</b>
Type /markunsold 123
(or multiple: /markunsold 1,2,3)""",

    "markpendingpayment": """<b>🟡 /markpendingpayment — Mark Pending</b>

<b>What it does:</b>
Marks account as waiting for payment.

<b>How to use:</b>
Type /markpendingpayment 123
(or multiple: /markpendingpayment 1,2,3)""",

    "voidsale": """<b>♻️ /voidsale — Cancel Sale</b>

<b>What it does:</b>
Deletes a sale. Account goes back to available.

<b>How to use:</b>
Type /voidsale 123
(or multiple: /voidsale 1,2,3)
(replace 123 with sale number)""",

    "editsale": """<b>✏️ /editsale — Edit Sale Details</b>

<b>What it does:</b>
Lets you change buyer, price, payment status, or notes on existing sales.

<b>How to use:</b>
1. Type /editsale
2. Pick: 🏷️ Sale ID or 📦 Account ID
3. Enter ID(s), comma-separated
4. Tap a field to change:
   • 👤 Buyer — type new name
   • 💰 Price — type new price
   • 📦 Status — pick paid/pending
   • 📝 Notes — type new notes
5. Tap ✅ Done when finished

<b>Sale IDs</b> look like: SALE-X7K9M2P4
<b>Account IDs</b> are plain numbers: 1, 2, 3

<b>Works with incomplete sales:</b>
If an account was marked as sold directly (via /marksold) without buyer/price info, /editsale will create a draft sale record so you can fill in the details.

<b>Notes:</b>
- Accepts multiple IDs: /editsale → Account ID → 1,2,3
- Changes apply to all IDs at once
- Status change auto-updates account status
- Pending changes shown before applying""",

    "list": """<b>📋 /list — Browse Accounts</b>

<b>What it does:</b>
Shows all accounts in a list, 5 per page.

<b>How to use:</b>
Type /list

<b>Filter by:</b>
🟢 Available — only unsold
🔴 Sold — only sold
🟡 Pending — only waiting for money
📂 Category — pick a category
🔢 By ID — type account numbers""",

    "search": """<b>🔎 /search — Find Accounts</b>

<b>What it does:</b>
Search for accounts by different things.

<b>How to use:</b>
Type /search
Tap what to search by
Type your search

<b>Options:</b>
👤 Username — find by name
🔑 Password — find by password
📂 Category — pick a category
📊 Status — pick 🟢/🔴/🟡
👤 Buyer — find by buyer name
📝 Notes — find in notes
🔍 General — searches everything
🔢 By ID — type account numbers""",

    "getid": """<b>🔍 /getid — View Account</b>

<b>What it does:</b>
Shows full details of one account.

<b>How to use:</b>
Type /getid 123
(replace 123 with account number)""",

    "add": """<b>➕ /add — Add One Account</b>

<b>What it does:</b>
Adds one account step by step.

<b>How to use:</b>
Type /add
Then follow the steps:
1. Type username
2. Type password
3. Type email (or skip)
4. Type email password (or skip)
5. Pick 2FA: Yes/No
6. Pick verified: Yes/No
7. Type notes (or skip)
8. Pick category
9. Confirm""",

    "bulkadd": """<b>📥 /bulkadd — Add Many Accounts</b>

<b>What it does:</b>
Add lots of accounts at once.

<b>How to use:</b>
1. Type /bulkadd
2. Pick a category
3. Paste accounts like:
   user1:pass1
   user2:pass2
4. Type /done when finished""",

    "extractcsv": """<b>📄 /extractcsv — Import from Excel</b>

<b>What it does:</b>
Import accounts from a CSV/Excel file.

<b>How to use:</b>
1. Type /extractcsv
2. Pick category
3. Upload your CSV file
4. Map the columns:
   • Tap which column is username
   • Tap which column is password
   • Skip or pick email, 2FA, etc.
5. Preview and confirm""",

    "delete": """<b>🗑️ /delete — Delete Account</b>

<b>What it does:</b>
Permanently deletes an account.

<b>How to use:</b>
Option 1: Type /delete 123
Option 2: Type /delete → pick from list

<b>Bulk delete:</b>
Type /bulkdelete → type IDs: 1,2,3
Or type a category name to delete all in it""",

    "bulkdelete": """<b>🗑️ /bulkdelete — Delete Many</b>

<b>What it does:</b>
Delete multiple accounts at once.

<b>How to use:</b>
Type /bulkdelete
Then type:
• Account numbers: 1,2,3
• Or a category name (deletes all in it)""",

    "preview": """<b>📂 /preview — Show to Buyer</b>

<b>What it does:</b>
Pulls accounts to show a buyer.

<b>How to use:</b>
1. Type /preview
2. Pick category (or All)
3. Type how many
4. Shows accounts with Reddit links
5. Tap "Sell" to sell one right away""",

    "categories": """<b>📂 /categories — List Categories</b>

<b>What it does:</b>
Shows all categories with account counts.

<b>How to use:</b>
Type /categories""",

    "addcategory": """<b>➕ /addcategory — New Category</b>

<b>What it does:</b>
Creates a new category.

<b>How to use:</b>
Type /addcategory Food
(replace Food with your category name)""",

    "deletecategory": """<b>🗑️ /deletecategory — Remove Category</b>

<b>What it does:</b>
Deletes a category. Accounts in it move to "uncategorized".

<b>How to use:</b>
Type /deletecategory Food
(replace Food with the category name)""",

    "inventory": """<b>📦 /inventory — Stock Overview</b>

<b>What it does:</b>
Shows how many accounts you have.

<b>How to use:</b>
Type /inventory

Shows:
🟢 Available count
🔴 Sold count
🟡 Waiting for money count
Per category and total""",

    "buyers": """<b>👥 /buyers — List Buyers</b>

<b>What it does:</b>
Shows all buyers and how much they spent.

<b>How to use:</b>
Type /buyers""",

    "buyer": """<b>👤 /buyer — Buyer History</b>

<b>What it does:</b>
Shows one buyer's purchase history.

<b>How to use:</b>
Type /buyer John
(replace John with buyer name)""",

    "report": """<b>📊 /report — Money Report</b>

<b>What it does:</b>
Shows money made in a time range.

<b>How to use:</b>
Type /report
Pick: Today / This Week / This Month / All Time""",

    "addseller": """<b>👤 /addseller — Add Team Member</b>

<b>What it does:</b>
Lets someone else sell accounts.

<b>How to use:</b>
Type /addseller 123456 Alice
(numbers = their Telegram ID, name = their name)""",

    "removeseller": """<b>🚫 /removeseller — Remove Team Member</b>

<b>What it does:</b>
Stops someone from selling.

<b>How to use:</b>
Type /removeseller 123456
(numbers = their Telegram ID)""",

    "listsellers": """<b>👥 /listsellers — See Team</b>

<b>What it does:</b>
Shows all sellers and their stats.

<b>How to use:</b>
Type /listsellers""",

    "export": """<b>📤 /export — Download Excel</b>

<b>What it does:</b>
Downloads all accounts as a CSV file.

<b>How to use:</b>
Type /export""",

    "backup": """<b>💾 /backup — Download Database</b>

<b>What it does:</b>
Downloads the entire database as a file.

<b>How to use:</b>
Type /backup""",

    "ping": """<b>🏓 /ping — Check Bot</b>

<b>What it does:</b>
Checks if the bot is running.

<b>How to use:</b>
Type /ping""",

    "status": """<b>📊 Account Status</b>

🟢 <b>available</b> — ready to sell
🔴 <b>sold</b> — already sold
🟡 <b>pending</b> — sold but no money yet

/marksold 123 — make it 🔴
/markunsold 123 — make it 🟢
/markpendingpayment 123 — make it 🟡

Only 🟢 accounts show when selling.
You get a reminder every 4 hours if someone hasn't paid.""",

    "filter": """<b>🔍 How Filtering Works</b>

When you see a list, tap a button to filter:

📋 All — show everything
🟢 Available — only unsold
🔴 Sold — only sold
🟡 Pending — only waiting for money
📂 Category — pick a category
🔢 By ID — type account numbers

Use ⬅️ ➡️ to move between pages.
5 accounts per page.""",

    "settings": """<b>⚙️ Settings</b>

Bot needs a .env file with:
BOT_TOKEN — bot token from @BotFather
ADMIN_USER_ID — your Telegram ID

Auto messages:
📊 Daily report
📊 Weekly report
🟡 Payment reminder every 4 hours""",
}
