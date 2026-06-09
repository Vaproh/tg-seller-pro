from database.connection import connect, init_db, get_schema_version, set_schema_version
from database.categories import (
    add_category, delete_category, list_categories,
    get_category_name, get_category_id_by_name, update_category_price,
)
from database.accounts import (
    add_account, add_accounts_bulk, get_account_by_id,
    list_accounts, count_accounts, search_accounts,
    set_account_status, update_account_notes,
    update_account_optional_fields, delete_account, delete_accounts_by_ids,
    delete_accounts_in_category, get_accounts_for_category,
    get_available_accounts_for_category, export_accounts_csv,
    get_available_account_ids,
)
from database.sales import (
    sell_account, bulk_sell_accounts, mark_payment,
    get_sales, count_sales, get_sale_by_id, get_sales_summary, void_sale,
)
from database.sellers import (
    add_seller, remove_seller, list_sellers,
    get_seller_by_user_id, get_seller_by_id, is_seller_active,
)
from database.sessions import (
    create_retrieval_session, add_retrieval_item,
    list_recent_sessions, get_session, get_session_items,
    delete_session, get_item, set_item_used,
    list_pending_items, count_pending_items, stats_summary,
)

__all__ = [
    "connect", "init_db", "get_schema_version", "set_schema_version",
    "add_category", "delete_category", "list_categories",
    "get_category_name", "get_category_id_by_name", "update_category_price",
    "add_account", "add_accounts_bulk", "get_account_by_id",
    "list_accounts", "count_accounts", "search_accounts",
    "set_account_status", "update_account_notes",
    "update_account_optional_fields", "delete_account", "delete_accounts_by_ids",
    "delete_accounts_in_category", "get_accounts_for_category",
    "get_available_accounts_for_category", "export_accounts_csv",
    "get_available_account_ids",
    "sell_account", "bulk_sell_accounts", "mark_payment",
    "get_sales", "count_sales", "get_sale_by_id", "get_sales_summary", "void_sale",
    "add_seller", "remove_seller", "list_sellers",
    "get_seller_by_user_id", "get_seller_by_id", "is_seller_active",
    "create_retrieval_session", "add_retrieval_item",
    "list_recent_sessions", "get_session", "get_session_items",
    "delete_session", "get_item", "set_item_used",
    "list_pending_items", "count_pending_items", "stats_summary",
]
