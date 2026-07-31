from api.db.db_models import AdminUser, User, UserGroup, SyncDept
from api.db.db_models import AdminUser
from api.apps import login_required, current_user
from api.utils.api_utils import get_json_result, server_error_response, validate_request, get_request_json
from common.constants import RetCode
from api.db.services.role_service import RoleService, validate_file_permission_level, validate_operation_permissions, build_operation_permission_mask

import json
@manager.route('/tree', methods=['POST'])
@login_required
async def get_dept_tree():
    """
    获取公司 + 部门树
    companyCode 作为公司根节点
    mdmCode 作为部门节点 ID
    parentAdminOrgCode 作为父级部门 ID
    """
    req = await get_request_json()
    keyword = req.get("keyword", "").strip() if req else ""

    try:
        query = SyncDept.select()

        if keyword:
            query = query.where(
                (SyncDept.departmentName.contains(keyword)) |
                (SyncDept.mdmName.contains(keyword)) |
                (SyncDept.mdmCode.contains(keyword)) |
                (SyncDept.companyCode.contains(keyword)) |
                (SyncDept.longName.contains(keyword)) |
                (SyncDept.corporateName.contains(keyword))
            )

        dept_list = []
        company_map = {}

        for item in query:
            dept_id = item.mdmCode

            if not dept_id:
                continue

            company_code = item.companyCode
            company_name = item.corporateName or company_code or "未知公司"

            if company_code and company_code not in company_map:
                company_map[company_code] = {
                    "id": "company_{}".format(company_code),
                    "key": "company_{}".format(company_code),
                    "value": "company_{}".format(company_code),
                    "title": company_name,
                    "type": "company",
                    "companyCode": company_code,
                    "children": [],
                }

            dept_name = (
                item.departmentName
                or item.mdmName
                or item.nameOfAdminOrg
                or item.longName
                or dept_id
            )

            dept_code = item.mdmCode or item.departmentCode

            title = dept_name
            if dept_code:
                title = "{}（{}）".format(dept_name, dept_code)

            dept_list.append({
                "id": dept_id,
                "key": dept_id,
                "value": dept_id,
                "title": title,
                "type": "dept",

                # parentAdminOrgCode 是父部门 ID
                "parentId": item.parentAdminOrgCode,

                # 公司
                "companyCode": company_code,
                "corporateName": item.corporateName,

                # 其他字段
                "mdmCode": item.mdmCode,
                "mdmName": item.mdmName,
                "parentAdminOrgCode": item.parentAdminOrgCode,
                "departmentName": item.departmentName,
                "departmentCode": item.departmentCode,
                "longName": item.longName,
                "longCode": item.longCode,
                "sealed": item.sealed,
                "children": [],
            })

        node_map = {}
        dept_roots = []

        for dept in dept_list:
            node_map[dept["id"]] = dept

        ROOT_PARENT_IDS = [None, "", "0", "-1", "ROOT", "root"]

        for dept in dept_list:
            parent_id = dept.get("parentId")

            if parent_id not in ROOT_PARENT_IDS and parent_id in node_map:
                node_map[parent_id]["children"].append(dept)
            else:
                dept_roots.append(dept)

        # 把部门根节点挂到公司下面
        no_company_roots = []

        for dept in dept_roots:
            company_code = dept.get("companyCode")

            if company_code and company_code in company_map:
                company_map[company_code]["children"].append(dept)
            else:
                no_company_roots.append(dept)

        roots = list(company_map.values()) + no_company_roots

        def clean_empty_children(nodes):
            for node in nodes:
                children = node.get("children") or []

                if children:
                    clean_empty_children(children)
                else:
                    node.pop("children", None)

        clean_empty_children(roots)

        return get_json_result(data=roots)

    except Exception as e:
        return server_error_response(e)


@manager.route('/list', methods=['POST'])
@login_required
async def get_dept_list():
    """
    获取部门平铺列表
    """
    req = await get_request_json()

    keyword = req.get("keyword", "").strip() if req else ""

    try:
        # 如果需要管理员权限，可以打开
        # error_response = check_group_admin(current_user)
        # if error_response:
        #     return error_response

        query = SyncDept.select()

        if keyword:
            query = query.where(
                (SyncDept.departmentName.contains(keyword)) |
                (SyncDept.departmentCode.contains(keyword)) |
                (SyncDept.longName.contains(keyword)) |
                (SyncDept.corporateName.contains(keyword))
            )

        data = []

        for item in query:
            data.append({
                "id": item.id,
                "mdmCode": item.mdmCode,
                "mdmName": item.mdmName,
                "companyCode": item.companyCode,
                "corporateName": item.corporateName,
                "nameOfAdminOrg": item.nameOfAdminOrg,
                "administrativeOrganizationCode": item.administrativeOrganizationCode,
                "parentId": item.parentId,
                "parentAdminOrgCode": item.parentAdminOrgCode,
                "departmentName": item.departmentName,
                "departmentCode": item.departmentCode,
                "remarks": item.remarks,
                "sealed": item.sealed,
                "administrativeOrganizationType": item.administrativeOrganizationType,
                "longName": item.longName,
                "longCode": item.longCode,
                "erpid": item.erpid,
            })

        return get_json_result(data=data)

    except Exception as e:
        return server_error_response(e)