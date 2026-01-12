from quart import request
from api.db.db_models import AdminUser, User, UserGroup
from api.db.services.group_service import GroupService
from api.utils.api_utils import get_json_result, server_error_response, validate_request, get_request_json
from api.apps import login_required, current_user
from common.constants import RetCode
from peewee import fn

def check_admin(user):
    admin_user = AdminUser.query(user_id=user.id)
    if not admin_user:
        return get_json_result(
            data=False, message='Only admin users can perform this action.', code=RetCode.OPERATING_ERROR
        )
    return None

@manager.route('/new', methods=['POST'])  # noqa: F821
@login_required
@validate_request("group_name")
async def new_group():
    req = await get_request_json()
    group_name = req['group_name']
    try:
        # Check if user is admin
        error_response = check_admin(current_user)
        if error_response:
            return error_response
            
        GroupService.save(group_name=group_name, created_by=current_user.id)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

@manager.route('/list', methods=['GET'])  # noqa: F821
@login_required
async def list_groups():
    try:
        # Check if user is admin
        error_response = check_admin(current_user)
        if error_response:
            return error_response
            
        groups = GroupService.get_all()
        created_by_ids = list({g.created_by for g in groups if getattr(g, "created_by", None)})
        nickname_by_user_id = {}
        if created_by_ids:
            nickname_by_user_id = {
                u.id: u.nickname
                for u in User.select(User.id, User.nickname).where(User.id.in_(created_by_ids))
            }
        
        # Calculate member count for each group
        # Using a single query with group_by is more efficient, but let's stick to simple logic first or optimized query
        # Optimized: SELECT group_id, COUNT(*) FROM user_group GROUP BY group_id
        member_counts = {
            res.group_id: res.count 
            for res in UserGroup.select(UserGroup.group_id, fn.COUNT(UserGroup.id).alias('count')).group_by(UserGroup.group_id)
        }

        group_list = [
            {
                "id": g.group_id,
                "group_name": g.group_name,
                "created_by": g.created_by,
                "created_by_nickname": nickname_by_user_id.get(g.created_by),
                "create_time": g.created_time,
                "member_count": member_counts.get(g.group_id, 0)
            } 
            for g in groups
        ]
        return get_json_result(data=group_list)
        
    except Exception as e:
        return server_error_response(e)

@manager.route('/delete', methods=['POST'])  # noqa: F821
@login_required
@validate_request("group_id")
async def delete_group():
    req = await get_request_json()
    group_id = req["group_id"]
    
    try:
        # Check if user is admin
        error_response = check_admin(current_user)
        if error_response:
            return error_response
            
        GroupService.delete_by_id(group_id)
        return get_json_result(data=True)
        
    except Exception as e:
        return server_error_response(e)
