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
/help — This menu"""

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

<b>📂 Other</b>
/preview — Show accounts to buyer
/categories — See all categories
/inventory — What's in stock
/buyers — See all buyers
/buyer — See one buyer's orders

<b>⚙️ Tools</b>
/ping — Check if bot works
/help — This menu"""

HELP_TOPICS = {
    "sell": """<b>💰 How to Sell</b>

<b>/sell</b> — sell one account
1. Pick an available account
2. Pick buyer (or type name)
3. Type the price
4. Pick: 🟢 Sold or 🟡 Waiting for money
5. Done! Receipt sent

<b>/bulksell</b> — sell many accounts
Pick accounts → same steps as above

<b>/markpaid</b> — buyer paid? Mark it done
<b>/voidsale</b> — cancel a sale""",

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

    "search": """<b>🔎 How to Search</b>

<b>/search</b> — tap what to search by:

👤 Username — type part of name
🔑 Password — type part of password
📂 Category — tap a category
📊 Status — tap 🟢 or 🔴 or 🟡
👤 Buyer — type buyer name
🏷️ Tag — type a tag
📝 Notes — type what's in notes
🔍 General — searches everything
🔢 By ID — type account numbers""",

    "add": """<b>➕ How to Add Accounts</b>

<b>/add</b> — add one:
Type username → password → email (or skip) → done

<b>/bulkadd</b> — add many:
Pick category → paste lines like:
user1:pass1
user2:pass2
Then type /done

<b>/extractcsv</b> — import from Excel:
Pick category → upload file → map columns → done""",

    "delete": """<b>🗑️ How to Delete</b>

<b>/delete</b> — delete one:
Type /delete 123 (use account number)
Or just /delete → pick from list

<b>/bulkdelete</b> — delete many:
Type account numbers: 1,2,3
Or type a category name to delete all in it""",

    "preview": """<b>📂 How to Preview</b>

<b>/preview</b> — show accounts to buyer:
1. Pick category
2. Type how many
3. Shows accounts with links
4. Tap "Sell" to sell right away""",

    "categories": """<b>📂 Categories</b>

<b>/categories</b> — see all categories
<b>/addcategory Food</b> — make new one
<b>/deletecategory Food</b> — delete one""",

    "sales": """<b>📈 Sales</b>

<b>/sales</b> — see all sales
Filter by: 🟡 Pending / ✅ Paid / 📋 All

<b>/sale 123</b> — see one sale
Can mark paid, cancel, or change status""",

    "inventory": """<b>📦 Inventory</b>

<b>/inventory</b> — see what you have:
🟢 how many available
🔴 how many sold
🟡 how many waiting for money
Per category and total""",

    "buyers": """<b>👥 Buyers</b>

<b>/buyers</b> — see all buyers
<b>/buyer John</b> — see John's orders""",

    "reports": """<b>📊 Money Reports</b>

<b>/report</b> — pick time range:
Today / This Week / This Month / All Time

Shows: how much money, how many sales, who sold what""",

    "sellers": """<b>👤 Team Members</b>

<b>/addseller 123456 Alice</b> — add member
<b>/removeseller 123456</b> — remove member
<b>/listsellers</b> — see everyone""",

    "settings": """<b>⚙️ Settings</b>

Bot needs a .env file with:
BOT_TOKEN — bot token from @BotFather
ADMIN_USER_ID — your Telegram ID

Auto messages:
📊 Daily report
📊 Weekly report
🟡 Payment reminder every 4 hours""",
}
