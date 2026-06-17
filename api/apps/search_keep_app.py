
from quart import request
from api.apps import current_user, login_required

from api.constants import DATASET_NAME_LIMIT
from api.db.db_models import DB, SearchMessage
from api.db.services import duplicate_name
from api.db.services.search_service import SearchService
from api.db.services.user_service import TenantService, UserTenantService
from common.misc_utils import get_uuid
from common.constants import RetCode, StatusEnum
from api.utils.api_utils import get_data_error_result, get_json_result, not_allowed_parameters, get_request_json, server_error_response, validate_request
import time
import uuid

@manager.route("/message", methods=["POST"])  # noqa: F821
# @login_required
async def create_search_message():
    print("开始写入数据库")
    req = await get_request_json()

    search_id = req.get("search_id")
    print(search_id)
    content = req.get("content", "").strip()
    print(content)

    if not search_id or not content:
        return get_json_result(message="search_id and content are required")

    try:
        new_uuid = str(uuid.uuid4())
        SearchMessage.create(
            id=new_uuid,
            search_id=search_id,
            # user_id=current_user.id,
            content=content,
            create_time=int(time.time() * 1000),
        )

        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)
    
@manager.route("/messages", methods=["POST"])  # noqa: F821
# @login_required
async def list_search_messages():
    print("获取梭梭历史列表")
    req = await get_request_json()
    search_id = req.get("search_id")

    if not search_id:
        return get_json_result(message="search_id is required")

    try:
        messages = (
            SearchMessage
            .select()
            .where(
                (SearchMessage.search_id == search_id) 
                
            )
            .order_by(SearchMessage.create_time.desc())
            .dicts()
        )

        return get_json_result(data=list(messages))
    except Exception as e:
        return server_error_response(e)
    
@manager.route("/message/delete", methods=["POST"])  # noqa: F821
async def delete_search_message():
    req = await get_request_json()
    message_id = req.get("id")

    if not message_id:
        return get_json_result(message="id is required")

    try:
        SearchMessage.delete().where(
            (SearchMessage.id == message_id) 
        ).execute()

        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)