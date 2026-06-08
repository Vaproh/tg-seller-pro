import html
import config


def esc(text):
    if text is None:
        return "—"
    return html.escape(str(text))


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
        f"╭─ Account #{a.get('id', '')} ────────────────",
        f"│ 👤 Username: {esc(a.get('username'))}",
        f"│ 🔑 Password: <tg-spoiler>{esc(a.get('password'))}</tg-spoiler>",
    ]
    if a.get("email"):
        lines.append(f"│ 📧 Email: {esc(a['email'])}")
    if a.get("email_password"):
        lines.append(f"│ 🔑 Email Pass: <tg-spoiler>{esc(a['email_password'])}</tg-spoiler>")
    lines.append(f"│ 🔐 2FA: {'Yes' if a.get('has_2fa') else 'No'}")
    lines.append(f"│ ✅ Verified: {'Yes' if a.get('is_verified') else 'No'}")
    lines.append(f"│ 🔗 Profile: {reddit_url(a.get('username', ''))}")
    lines.append(f"│ 📂 Category: {esc(a.get('category_name', '—'))}")
    lines.append(f"│ 📦 Status: {status_emoji} {esc(status)}")
    lines.append(f"│ 📝 Notes: {esc(a.get('notes'))}")
    lines.append("╰──────────────────────────")
    return "\n".join(lines)


def fmt_sale_block(sale):
    s = _d(sale)
    ps = s.get("payment_status", "pending")
    ps_emoji = "✅" if ps == "paid" else "🟡" if ps == "pending" else "⚪"
    lines = [
        f"╭─ Sale #{s.get('id', '')} ────────────────",
        f"│ 👤 Buyer: {esc(s.get('buyer_name'))}",
        f"│ 💰 Price: {config.CURRENCY}{s.get('price', 0):.0f}",
        f"│ 💳 Payment: {ps_emoji} {esc(ps)}",
    ]
    lines.append(f"│ 📅 Sold: {esc(str(s.get('sold_at', ''))[:10])}")
    lines.append(f"│ 👨‍💼 Seller: {esc(s.get('seller_name', '—'))}")
    lines.append(f"│ 🔗 Profile: {reddit_url(s.get('username', ''))}")
    lines.append(f"│ 📂 Category: {esc(s.get('category_name', '—'))}")
    if s.get("notes"):
        lines.append(f"│ 📝 Notes: {esc(s['notes'])}")
    lines.append("╰──────────────────────────")
    return "\n".join(lines)


def fmt_receipt(sale):
    s = _d(sale)
    username = str(s.get("username", ""))
    password = str(s.get("password", ""))
    price = s.get("price", 0)
    sale_id = s.get("id", "")
    sold_at = str(s.get("sold_at", ""))[:10]
    ps = s.get("payment_status", "pending")
    ps_label = "Pending Payment" if ps == "pending" else "Paid"
    return (
        "╔══════════════════════════════════╗\n"
        "║     🧾 Reddit Account Receipt    ║\n"
        "╠══════════════════════════════════╣\n"
        f"║ Account: {esc(username)}\n"
        f"║ Password: <tg-spoiler>{esc(password)}</tg-spoiler>\n"
        f"║ Profile: reddit.com/user/{esc(username)}\n"
        "║──────────────────────────────────║\n"
        f"║ Price: {config.CURRENCY}{price:.0f}\n"
        f"║ Status: {ps_label}\n"
        f"║ Sale ID: #{sale_id}\n"
        f"║ Date: {sold_at}\n"
        "╚══════════════════════════════════╝"
    )
