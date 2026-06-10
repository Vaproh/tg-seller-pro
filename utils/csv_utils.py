import csv
import io


def detect_columns(headers):
    mapping = {}
    for i, h in enumerate(headers):
        lower = h.lower().strip()
        if lower in ("username", "user", "login"):
            mapping["username"] = i
        elif lower in ("password", "pass", "pwd"):
            mapping["password"] = i
        elif lower in ("email", "mail"):
            mapping["email"] = i
        elif lower in ("email_password", "email_pass", "emailpassword", "mailpass"):
            mapping["email_password"] = i
        elif lower in ("2fa", "two_factor", "twofa", "has_2fa"):
            mapping["has_2fa"] = i
        elif lower in ("verified", "is_verified", "isverified"):
            mapping["is_verified"] = i
        elif lower in ("notes", "note", "comment"):
            mapping["notes"] = i
    return mapping


def build_accounts_from_csv(headers, data, column_map):
    accounts = []
    for row in data:
        if not any(row):
            continue
        item = {
            "username": row[column_map["username"]] if "username" in column_map and column_map["username"] < len(row) else "",
            "password": row[column_map["password"]] if "password" in column_map and column_map["password"] < len(row) else "",
            "email": row[column_map["email"]] if "email" in column_map and isinstance(column_map["email"], int) and column_map["email"] < len(row) else None,
            "email_password": row[column_map["email_password"]] if "email_password" in column_map and isinstance(column_map["email_password"], int) and column_map["email_password"] < len(row) else None,
            "has_2fa": column_map["has_2fa"] if "has_2fa" in column_map and isinstance(column_map["has_2fa"], bool) else (_parse_bool(row[column_map["has_2fa"]]) if "has_2fa" in column_map and isinstance(column_map["has_2fa"], int) and column_map["has_2fa"] < len(row) else False),
            "is_verified": column_map["is_verified"] if "is_verified" in column_map and isinstance(column_map["is_verified"], bool) else (_parse_bool(row[column_map["is_verified"]]) if "is_verified" in column_map and isinstance(column_map["is_verified"], int) and column_map["is_verified"] < len(row) else False),
            "notes": row[column_map["notes"]] if "notes" in column_map and isinstance(column_map["notes"], int) and column_map["notes"] < len(row) else None,
        }
        if item["username"] and item["password"]:
            accounts.append(item)
    return accounts


def _parse_bool(val):
    if not val:
        return False
    return val.strip().lower() in ("true", "1", "yes")


def export_with_sales_csv(sales_data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "sale_id", "account_id", "username", "password",
        "price", "payment_status", "tags",
        "seller", "category", "sold_at"
    ])
    for s in sales_data:
        writer.writerow([
            s["id"], s["account_id"], s["username"], s["password"],
            s["price"], s["payment_status"],
            s.get("tags", ""), s.get("seller_name", ""),
            s.get("category_name", ""), s["sold_at"],
        ])
    return output.getvalue().encode("utf-8")
