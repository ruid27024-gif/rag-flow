from quart import request
from api.apps import login_required, current_user
from api.utils.api_utils import (
    get_json_result,
    server_error_response,
    validate_request,
    get_request_json,
)
from api.db.db_models import DB
from api.db.services.knowledge_tag_type import KnowledgeTagTypeService
from api.db.services.knowledge_tag_option import KnowledgeTagOptionService
from api.db.services.knowledge_tag_manage import KnowledgeTagManageService

@manager.route('/tag/config', methods=['GET'])  # noqa: F821
@login_required
async def list_tag_config():
    """
    获取标签配置：类型 + 选项
    前端用于渲染上传文件时的勾选项
    """
    try:
        data = KnowledgeTagManageService.list_tag_config()
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/type/create_with_options', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "type_name")
async def create_tag_type_with_options():
    req = await get_request_json()

    try:

        tag_type = KnowledgeTagManageService.create_type_with_options(req)

        return get_json_result(data={
            "id": tag_type.id,
            "type_code": tag_type.type_code,
            "type_name": tag_type.type_name
        })

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/type/create', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "type_name")
async def create_tag_type():
    """
    新增标签类型
    """
    req = await get_request_json()

    try:
        # error_response = check_admin(current_user)
        # if error_response:
        #     return error_response

        obj = KnowledgeTagTypeService.save(
            type_code=req.get("type_code"),
            type_name=req.get("type_name"),
            multi_select=1 if req.get("multi_select", False) else 0,
            required=1 if req.get("required", False) else 0,
            sort_order=req.get("sort_order", 0),
            enabled=1 if req.get("enabled", True) else 0,
        )

        return get_json_result(data={
            "id": obj.id,
            "type_code": obj.type_code,
            "type_name": obj.type_name
        })

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/type/update', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code")
async def update_tag_type():
    """
    修改标签类型
    """
    req = await get_request_json()

    try:

        type_code = req.get("type_code")

        update_data = {}

        if "type_name" in req:
            update_data["type_name"] = req.get("type_name")

        if "multi_select" in req:
            update_data["multi_select"] = 1 if req.get("multi_select") else 0

        if "required" in req:
            update_data["required"] = 1 if req.get("required") else 0

        if "sort_order" in req:
            update_data["sort_order"] = req.get("sort_order")

        if "enabled" in req:
            update_data["enabled"] = 1 if req.get("enabled") else 0

        if not update_data:
            return get_json_result(data=True)

        KnowledgeTagTypeService.update_by_type_code(
            type_code,
            **update_data
        )

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/type/disable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code")
async def disable_tag_type():
    """
    禁用标签类型
    """
    req = await get_request_json()
    type_code = req.get("type_code")

    try:
        # error_response = check_admin(current_user)
        # if error_response:
        #     return error_response

        KnowledgeTagTypeService.disable_by_type_code(type_code)

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/option/create', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "option_code", "option_name")
async def create_tag_option():
    """
    新增标签选项
    """
    req = await get_request_json()

    try:
        # error_response = check_admin(current_user)
        # if error_response:
        #     return error_response

        obj = KnowledgeTagOptionService.save(
            type_code=req.get("type_code"),
            option_code=req.get("option_code"),
            option_name=req.get("option_name"),
            sort_order=req.get("sort_order", 0),
            enabled=1 if req.get("enabled", True) else 0,
        )

        return get_json_result(data={
            "id": obj.id,
            "type_code": obj.type_code,
            "option_code": obj.option_code,
            "option_name": obj.option_name
        })

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/option/batch_create', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "options")
async def batch_create_tag_options():
    """
    批量新增标签选项
    """
    req = await get_request_json()

    try:
        # error_response = check_admin(current_user)
        # if error_response:
        #     return error_response

        type_code = req.get("type_code")
        options = req.get("options", [])

        KnowledgeTagOptionService.batch_save(type_code, options)

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/option/update', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "option_code")
async def update_tag_option():
    """
    修改标签选项
    """
    req = await get_request_json()

    try:
        

        type_code = req.get("type_code")
        option_code = req.get("option_code")

        update_data = {}

        if "option_name" in req:
            update_data["option_name"] = req.get("option_name")

        if "sort_order" in req:
            update_data["sort_order"] = req.get("sort_order")

        if "enabled" in req:
            update_data["enabled"] = 1 if req.get("enabled") else 0

        if not update_data:
            return get_json_result(data=True)

        KnowledgeTagOptionService.update_option(
            type_code,
            option_code,
            **update_data
        )

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/option/disable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "option_code")
async def disable_tag_option():
    """
    禁用标签选项
    """
    req = await get_request_json()

    try:

        KnowledgeTagOptionService.disable_option(
            req.get("type_code"),
            req.get("option_code")
        )

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/option/list', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code")
async def list_tag_options():
    """
    获取某个标签类型下的选项
    """
    req = await get_request_json()

    try:
        type_code = req.get("type_code")

        options = KnowledgeTagOptionService.list_by_type_code(type_code)

        data = [
            {
                "id": item.id,
                "type_code": item.type_code,
                "option_code": item.option_code,
                "option_name": item.option_name,
                "sort_order": item.sort_order,
                "enabled": bool(item.enabled)
            }
            for item in options
        ]

        return get_json_result(data=data)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/config_all', methods=['GET'])  # noqa: F821
@login_required
async def list_tag_config_all():
    """
    标签管理页面使用：返回全部标签类型和选项，包括禁用的
    """ 
    try:

        data = KnowledgeTagManageService.list_tag_config_all()
        return get_json_result(data=data)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/type/enable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code")
async def enable_tag_type():
    """
    启用标签类型
    """
    req = await get_request_json()
    type_code = req.get("type_code")

    try:

        KnowledgeTagTypeService.enable_by_type_code(type_code)

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/option/enable', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "option_code")
async def enable_tag_option():
    """
    启用标签选项
    """
    req = await get_request_json()

    try:

        KnowledgeTagOptionService.enable_option(
            req.get("type_code"),
            req.get("option_code")
        )

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/type/delete', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code")
async def delete_tag_type():
    """
    删除标签类型
    当前没有 DocumentTagRelation，直接删除类型和其下选项。
    """
    req = await get_request_json()
    type_code = req.get("type_code")

    try:

        KnowledgeTagTypeService.delete_by_type_code(type_code)

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)

@manager.route('/tag/option/delete', methods=['POST'])  # noqa: F821
@login_required
@validate_request("type_code", "option_code")
async def delete_tag_option():
    """
    删除标签选项
    当前没有 DocumentTagRelation，直接删除选项。
    """
    req = await get_request_json()

    try:
        KnowledgeTagOptionService.delete_option(
            req.get("type_code"),
            req.get("option_code")
        )

        return get_json_result(data=True)

    except Exception as e:
        return server_error_response(e)