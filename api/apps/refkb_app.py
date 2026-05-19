from quart import request
from api.db.db_models import AdminUser, User, UserGroup
from api.db.services.group_service import GroupService
from api.db.services.kb_access_service import KnowledgebaseAccessService
from api.utils.api_utils import get_json_result, server_error_response, validate_request, get_request_json
from api.apps import login_required, current_user
from common.constants import RetCode
from peewee import fn
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_group_service import UserGroupService
from api.db.services.file_service import FileService
from api.db.services.file_admin_service import FileAdminService
from api.db.services.file_group_service import FileGroupService
from api.db import FileType
from api.db.services import UserService
from peewee import IntegrityError
from api.db.db_models import DB
from common import settings

def check_admin(user):
    admin_user = AdminUser.query(user_id=user.id, role_level=1)
    if not admin_user:
        return get_json_result(
            data=False, message='Only admin users can perform this action.', code=RetCode.OPERATING_ERROR
        )
    return None

def check_group_admin(user):
    admin_user = AdminUser.query(user_id=user.id)
    if not admin_user:
        return get_json_result(
            data=False, message='Only admin users can perform this action.', code=RetCode.OPERATING_ERROR
        )
    return None

# 增加权限接口
@manager.route('/add', methods=['POST'])  # 建议改为 POST
@login_required
async def add():
    req = await get_request_json()
    kb_id = req.get("kb_id")
    mems = req.get("mems")  # 假设 mems 是一个包含 user_id 的数组，例如 ["u_1001", "u_1002"]
    print(mems)
    try:
        # 遍历前端传来的用户ID列表，批量增加写权限
        if mems:
            for user_id in mems:
                KnowledgebaseAccessService.add_permission(kb_id, user_id, 'write')
        
        return get_json_result(data={"success": True, "added_count": len(mems) if mems else 0})
    except Exception as e:
        return server_error_response(e)
    

# 删除权限接口
@manager.route('/del', methods=['POST'])  # 建议改为 POST
@login_required
async def del_mems():
    req = await get_request_json()
    kb_id = req.get("kb_id")
    mems = req.get("mems")  # 假设 mems 是一个包含 user_id 的数组

    try:
        # 遍历前端传来的用户ID列表，批量删除写权限
        if mems:
            for user_id in mems:
                # 第三个参数传 'write'，表示只删除写权限；如果不传则删除该用户在该知识库下的所有权限
                KnowledgebaseAccessService.remove_permission(kb_id, user_id, 'write')
        
        return get_json_result(data={"success": True, "removed_count": len(mems) if mems else 0})
    except Exception as e:
        return server_error_response(e)

