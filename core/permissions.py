import logging
import config
from database.sellers import get_seller_by_user_id

logger = logging.getLogger(__name__)


def get_user_role(user_id):
    if user_id == config.ADMIN_USER_ID:
        return "admin"
    seller = get_seller_by_user_id(user_id)
    if seller and seller["active"]:
        return "seller"
    return None


def require_admin(update):
    user_id = update.effective_user.id
    if get_user_role(user_id) == "admin":
        return True
    logger.warning("Unauthorized admin access from user_id=%s", user_id)
    return False


def require_seller(update):
    user_id = update.effective_user.id
    if get_user_role(user_id) in ("admin", "seller"):
        return True
    logger.warning("Unauthorized seller access from user_id=%s", user_id)
    return False
