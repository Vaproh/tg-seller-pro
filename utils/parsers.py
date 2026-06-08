import csv
import io


def parse_bulk_lines(text):
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    items = []
    for line in lines:
        parts = [p.strip() for p in line.split(":")]
        if len(parts) < 2:
            continue
        username = parts[0]
        rest = ":".join(parts[1:])
        fields = [f.strip() for f in rest.split(",")]
        item = {
            "username": username,
            "password": fields[0] if fields else "",
            "email": fields[1] if len(fields) > 1 and fields[1] else None,
            "email_password": fields[2] if len(fields) > 2 and fields[2] else None,
            "has_2fa": fields[3].lower() in ("true", "1", "yes") if len(fields) > 3 else False,
            "is_verified": fields[4].lower() in ("true", "1", "yes") if len(fields) > 4 else False,
            "notes": fields[5] if len(fields) > 5 and fields[5] else None,
        }
        items.append(item)
    return items


def parse_csv_file(file_content):
    text = file_content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    headers = rows[0]
    data = rows[1:]
    return headers, data


def search_query_tokenizer(query):
    tokens = []
    for part in query.split():
        if "=" in part:
            key, val = part.split("=", 1)
            tokens.append((key.lower(), val))
        else:
            tokens.append(("general", part))
    return tokens
