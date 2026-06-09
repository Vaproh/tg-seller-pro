import html
import config

MAX_MSG_LEN = 4000


def esc(text):
    if text is None:
        return "—"
    return html.escape(str(text))


def code(text):
    if text is None:
        return "—"
    return f"<code>{html.escape(str(text))}</code>"


def spoiler(text):
    if text is None:
        return "—"
    return f"<tg-spoiler>{html.escape(str(text))}</tg-spoiler>"


def code_id(value):
    return code(value)


def code_username(value):
    return code(value)


def code_email(value):
    return code(value)


def _truncate(text, limit=MAX_MSG_LEN):
    if len(text) <= limit:
        return text
    return text[:limit - 20] + "\n\n... (truncated)"


def reddit_url(username):
    return f"https://reddit.com/user/{username}"


def _d(row):
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    return dict(row)


def fmt_account_block(account):
    a = _d(account)
    status = a.get("status", "available")
    status_emoji = {"available": "🟢", "sold": "🔴", "pending_payment": "🟡"}.get(status, "⚪")
    lines = [
        f"╭─ Account #{code_id(a.get('id', ''))} ────────────────",
        f"│ 👤 Username: {code_username(a.get('username'))}",
        f"│ 🔑 Password: {spoiler(a.get('password'))}",
    ]
    if a.get("email"):
        lines.append(f"│ 📧 Email: {code(a['email'])}")
    if a.get("email_password"):
        lines.append(f"│ 🔑 Email Pass: {spoiler(a['email_password'])}")
    lines.append(f"│ 🔐 2FA: {'Yes' if a.get('has_2fa') else 'No'}")
    lines.append(f"│ ✅ Verified: {'Yes' if a.get('is_verified') else 'No'}")
    lines.append(f"│ 🔗 Profile: {code(reddit_url(a.get('username', '')))}")
    lines.append(f"│ 📂 Category: {esc(a.get('category_name', '—'))}")
    lines.append(f"│ 📦 Status: {status_emoji} {esc(status)}")
    lines.append(f"│ 📝 Notes: {esc(a.get('notes'))}")
    lines.append("╰──────────────────────────")
    return "\n".join(lines)


def fmt_sale_block(sale):
    s = _d(sale)
    ps = s.get("payment_status", "pending")
    ps_emoji = "✅" if ps == "paid" else "🟡" if ps == "pending" else "⚪"
    sale_code = s.get("sale_code", f"#{s.get('id', '')}")
    username = s.get("username", "")
    email = s.get("email")
    lines = [
        f"╭─ {code(sale_code)} ────────────────",
        f"│ 👤 Username: {code(username)}",
        f"│ 💰 Price: {config.CURRENCY}{s.get('price', 0):.0f}",
        f"│ 💳 Payment: {ps_emoji} {esc(ps)}",
        f"│ 📅 Sold: {esc(str(s.get('sold_at', ''))[:16])}",
        f"│ 👨‍💼 Seller: {esc(s.get('seller_name', '—'))}",
        f"│ 🔗 Profile: {code(reddit_url(username))}",
        f"│ 📂 Category: {esc(s.get('category_name', '—'))}",
    ]
    if email:
        lines.append(f"│ 📧 Email: {code(email)}")
    if s.get("notes"):
        lines.append(f"│ 📝 Notes: {esc(s['notes'])}")
    lines.append("╰──────────────────────────")
    return "\n".join(lines)


def fmt_receipt(sale):
    s = _d(sale)
    username = str(s.get("username", ""))
    password = str(s.get("password", ""))
    price = s.get("price", 0)
    sale_code = s.get("sale_code", f"#{s.get('id', '')}")
    sold_at = str(s.get("sold_at", ""))[:10]
    ps = s.get("payment_status", "pending")
    ps_label = "Pending Payment" if ps == "pending" else "Paid"
    return (
        "╔══════════════════════════════════╗\n"
        "║     🧾 Reddit Account Receipt    ║\n"
        "╠══════════════════════════════════╣\n"
        f"║ Account: {code(username)}\n"
        f"║ Password: {spoiler(password)}\n"
        f"║ Profile: {code(reddit_url(username))}\n"
        "║──────────────────────────────────║\n"
        f"║ Price: {config.CURRENCY}{price:.0f}\n"
        f"║ Status: {ps_label}\n"
        f"║ {code(sale_code)}\n"
        f"║ Date: {sold_at}\n"
        "╚══════════════════════════════════╝"
    )
