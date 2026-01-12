from quart import request

from api.apps import current_user, login_required
from api.db.db_models import AdminUser, Group, User, UserGroup
from api.db.services.user_group_service import UserGroupService
from api.utils.api_utils import get_json_result, get_request_json, server_error_response, validate_request
from common.constants import RetCode


def check_admin(user):
    is_admin = AdminUser.query(user_id=user.id)
    if not is_admin:
        return get_json_result(
            data=False,
            message="Only admin users can perform this action.",
            code=RetCode.OPERATING_ERROR,
        )
    return None


@manager.route("/new", methods=["POST"])  # noqa: F821
@login_required
@validate_request("user_id", "group_id")
async def add_user_to_group():
    req = await get_request_json()
    user_id = req["user_id"]
    group_id = req["group_id"]

    try:
        error_response = check_admin(current_user)
        if error_response:
            return error_response

        exists = UserGroup.get_or_none(
            (UserGroup.user_id == user_id) & (UserGroup.group_id == group_id)
        )
        if exists:
            return get_json_result(
                code=RetCode.DATA_ERROR,
                message="User already in group.",
                data={"id": exists.id},
            )

        obj = UserGroupService.save(
            user_id=user_id,
            group_id=group_id,
            created_by=current_user.id,
        )
        return get_json_result(data={"id": obj.id})
    except Exception as e:
        return server_error_response(e)


@manager.route("/delete", methods=["POST"])  # noqa: F821
@login_required
async def delete_user_group():
    req = await get_request_json()
    pid = req.get("id")
    user_id = req.get("user_id")
    group_id = req.get("group_id")

    try:
        error_response = check_admin(current_user)
        if error_response:
            return error_response

        if pid is not None:
            deleted = UserGroupService.delete_by_id(pid)
            return get_json_result(data={"deleted": deleted})

        if user_id and group_id:
            deleted = UserGroupService.delete_by_user_group(user_id=user_id, group_id=group_id)
            return get_json_result(data={"deleted": deleted})

        return get_json_result(
            code=RetCode.ARGUMENT_ERROR,
            message="required argument are missing: id or (user_id, group_id)",
        )
    except Exception as e:
        return server_error_response(e)


@manager.route("/list", methods=["GET"])  # noqa: F821
@login_required
async def list_user_groups():
    try:
        error_response = check_admin(current_user)
        if error_response:
            return error_response

        rows = list(UserGroupService.get_all())
        user_ids = list({r.user_id for r in rows} | {r.created_by for r in rows})
        group_ids = list({r.group_id for r in rows})

        nickname_by_user_id = {}
        if user_ids:
            nickname_by_user_id = {
                u.id: u.nickname
                for u in User.select(User.id, User.nickname).where(User.id.in_(user_ids))
            }

        group_name_by_id = {}
        if group_ids:
            group_name_by_id = {
                g.group_id: g.group_name
                for g in Group.select(Group.group_id, Group.group_name).where(
                    Group.group_id.in_(group_ids)
                )
            }

        data = [
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_nickname": nickname_by_user_id.get(r.user_id),
                "group_id": r.group_id,
                "group_name": group_name_by_id.get(r.group_id),
                "created_by": r.created_by,
                "created_by_nickname": nickname_by_user_id.get(r.created_by),
                "created_time": r.created_time,
            }
            for r in rows
        ]
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/candidates", methods=["GET"])  # noqa: F821
@login_required
async def list_candidate_users():
    try:
        error_response = check_admin(current_user)
        if error_response:
            return error_response

        # 1. Find all users who are already in any group
        bound_user_ids = list({r.user_id for r in UserGroup.select(UserGroup.user_id)})
        
        # 2. Find users NOT in that list
        if bound_user_ids:
            candidates = list(
                User.select(User.id, User.nickname).where(User.id.not_in(bound_user_ids))
            )
        else:
            candidates = list(User.select(User.id, User.nickname))

        data = [{"user_id": u.id, "nickname": u.nickname} for u in candidates]
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/users", methods=["GET"])  # noqa: F821
@validate_request("group_id")
async def list_group_users():
    group_id = request.args.get("group_id")

    try:
        rows = list(UserGroup.select(UserGroup.user_id).where(UserGroup.group_id == group_id))
        user_ids = list({r.user_id for r in rows})
        nickname_by_user_id = {}
        if user_ids:
            nickname_by_user_id = {
                u.id: u.nickname
                for u in User.select(User.id, User.nickname).where(User.id.in_(user_ids))
            }
        data = [
            {"user_id": user_id, "nickname": nickname_by_user_id.get(user_id)}
            for user_id in user_ids
        ]
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/members", methods=["GET"])  # noqa: F821
@validate_request("group_id")
async def list_group_members():
    group_id = request.args.get("group_id")

    try:
        rows = list(
            UserGroup.select(UserGroup.user_id, UserGroup.created_by, UserGroup.created_time).where(
                UserGroup.group_id == group_id
            )
        )
        user_ids = list({r.user_id for r in rows} | {r.created_by for r in rows})
        nickname_by_user_id = {}
        if user_ids:
            nickname_by_user_id = {
                u.id: u.nickname
                for u in User.select(User.id, User.nickname).where(User.id.in_(user_ids))
            }

        data = [
            {
                "user_id": r.user_id,
                "nickname": nickname_by_user_id.get(r.user_id),
                "created_by": r.created_by,
                "created_by_nickname": nickname_by_user_id.get(r.created_by),
                "created_time": r.created_time,
            }
            for r in rows
        ]
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)


@manager.route("/groups", methods=["GET"])  # noqa: F821
@validate_request("user_id")
async def list_user_groups_by_user():
    user_id = request.args.get("user_id")

    try:
        rows = list(UserGroup.select(UserGroup.group_id).where(UserGroup.user_id == user_id))
        group_ids = list({r.group_id for r in rows})
        group_name_by_id = {}
        if group_ids:
            group_name_by_id = {
                g.group_id: g.group_name
                for g in Group.select(Group.group_id, Group.group_name).where(
                    Group.group_id.in_(group_ids)
                )
            }
        data = [
            {"group_id": group_id, "group_name": group_name_by_id.get(group_id)}
            for group_id in group_ids
        ]
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)
