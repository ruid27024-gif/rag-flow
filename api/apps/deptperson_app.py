from api.db.db_models import AdminUser, User, UserGroup, SyncDept,SyncPerson
from api.db.db_models import AdminUser
from api.apps import login_required, current_user
from api.utils.api_utils import get_json_result, server_error_response, validate_request, get_request_json
from common.constants import RetCode
from api.db.services.role_service import RoleService, validate_file_permission_level, validate_operation_permissions, build_operation_permission_mask
import logging

@manager.route('/person-tree', methods=['POST'])
@login_required
async def get_person_tree():
    """
    获取公司 + 部门 + 人员树

    部门结构：
      SyncDept.mdmCode 作为部门节点 ID
      SyncDept.parentAdminOrgCode 作为父级部门 ID

    人员挂载：
      SyncPerson.organizationCode == SyncDept.mdmCode

    绑定关系：
      人员节点 value = SyncPerson.phone
      保存绑定时：SyncPerson.phone == User.email -> User.id -> role_user.user_id

    搜索逻辑：
      1. 部门始终查全量，用于保证组织架构完整
      2. keyword 可搜索人员字段
      3. keyword 也可搜索部门字段
      4. 如果命中部门，则展示该部门及其子部门下的人员
      5. 搜索时裁剪掉没有人员的空组织节点
    """
    req = await get_request_json()
    keyword = req.get("keyword", "").strip() if req else ""

    try:
        # 部门必须全量查询，否则搜索人员或部门时组织架构会断
        dept_query = SyncDept.select()

        dept_list = []
        company_map = {}
        matched_dept_ids = set()

        keyword_lower = keyword.lower() if keyword else ""

        # 1. 构建公司节点、部门节点，同时记录搜索命中的部门
        for item in dept_query:
            dept_id = item.mdmCode

            if not dept_id:
                continue

            dept_id = str(dept_id).strip()

            if not dept_id:
                continue

            # 搜索部门字段，记录命中的部门
            if keyword_lower:
                dept_search_text = " ".join([
                    str(getattr(item, "departmentName", "") or ""),
                    str(getattr(item, "mdmName", "") or ""),
                    str(getattr(item, "mdmCode", "") or ""),
                    str(getattr(item, "companyCode", "") or ""),
                    str(getattr(item, "longName", "") or ""),
                    str(getattr(item, "corporateName", "") or ""),
                    str(getattr(item, "departmentCode", "") or ""),
                    str(getattr(item, "nameOfAdminOrg", "") or ""),
                ]).lower()

                if keyword_lower in dept_search_text:
                    matched_dept_ids.add(dept_id)

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
                    "selectable": False,
                    "disabled": True,
                    "children": [],
                }

            dept_name = (
                item.departmentName
                or item.mdmName
                or getattr(item, "nameOfAdminOrg", None)
                or item.longName
                or dept_id
            )

            dept_code = item.mdmCode or item.departmentCode

            title = dept_name
            if dept_code:
                title = "{}（{}）".format(dept_name, dept_code)

            parent_id = item.parentAdminOrgCode

            if parent_id:
                parent_id = str(parent_id).strip()

            dept_list.append({
                "id": dept_id,
                "key": "dept_{}".format(dept_id),
                "value": "dept_{}".format(dept_id),
                "title": title,
                "type": "dept",

                # 部门只作为结构，不参与绑定
                "selectable": False,
                "disabled": True,

                # 搜索命中标记
                "matched": dept_id in matched_dept_ids,

                # 父部门
                "parentId": parent_id,

                # 公司信息
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

        # 2. 构建部门父子关系
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

        # 3. 获取命中部门的所有子部门 ID
        def collect_child_dept_ids(dept_id):
            result = []

            dept_node = node_map.get(dept_id)

            if not dept_node:
                return result

            children = dept_node.get("children") or []

            for child in children:
                if child.get("type") == "dept":
                    child_id = child.get("id")

                    if child_id:
                        result.append(child_id)
                        result.extend(collect_child_dept_ids(child_id))

            return result

        matched_dept_scope_ids = set(matched_dept_ids)

        for dept_id in matched_dept_ids:
            matched_dept_scope_ids.update(collect_child_dept_ids(dept_id))

        # 4. 把部门根节点挂到公司下面
        no_company_roots = []

        for dept in dept_roots:
            company_code = dept.get("companyCode")

            if company_code and company_code in company_map:
                company_map[company_code]["children"].append(dept)
            else:
                no_company_roots.append(dept)

        # 5. 查询人员
        person_query = SyncPerson.select()

        if keyword:
            person_condition = (
                (SyncPerson.mdmName.contains(keyword)) |
                (SyncPerson.phone.contains(keyword)) |
                (SyncPerson.email.contains(keyword)) |
                (SyncPerson.erpid.contains(keyword)) |
                (SyncPerson.organize.contains(keyword)) |
                (SyncPerson.organizationCode.contains(keyword)) |
                (SyncPerson.mdmCode.contains(keyword)) |
                (SyncPerson.part.contains(keyword))
            )

            if matched_dept_scope_ids:
                # 关键：人员所属部门关系
                # SyncPerson.organizationCode == SyncDept.mdmCode
                dept_person_condition = SyncPerson.organizationCode.in_(matched_dept_scope_ids)

                person_query = person_query.where(
                    person_condition | dept_person_condition
                )
            else:
                person_query = person_query.where(person_condition)

        persons = list(person_query)

        # 6. 判断哪些人员能绑定
        # 绑定条件：SyncPerson.phone == User.email
        phones = [
            str(person.phone).strip()
            for person in persons
            if person.phone and str(person.phone).strip()
        ]

        user_map = {}

        if phones:
            users = User.select(User.id, User.email).where(
                User.email.in_(phones)
            )

            user_map = {
                str(user.email).strip(): user.id
                for user in users
                if user.email
            }

        # 7. 把人员挂到部门节点下面
        no_dept_person_nodes = []

        for person in persons:
            phone = str(person.phone).strip() if person.phone else ""
            user_id = user_map.get(phone)

            person_name = (
                person.mdmName
                or person.email
                or person.phone
                or person.erpid
                or "未知人员"
            )

            person_title = person_name

            if phone:
                person_title = "{}（{}）".format(person_name, phone)

            can_bind = bool(phone and user_id)

            person_key_suffix = person.id or phone or person.erpid or person_name

            person_node = {
                "id": "person_{}".format(person_key_suffix),
                "key": "person_{}".format(person_key_suffix),

                # 关键：value 用 phone，前端保存时提交 phones
                "value": phone,

                "title": person_title,
                "type": "person",

                # 只有匹配到 User 的人员才允许选择
                "selectable": can_bind,
                "disabled": not can_bind,

                "personId": person.id,
                "mdmName": person.mdmName,
                "mdmCode": person.mdmCode,
                "phone": person.phone,
                "email": person.email,
                "erpid": person.erpid,
                "organize": person.organize,
                "organizationCode": person.organizationCode,
                "part": person.part,
                "gender": person.gender,
                "onDutyOrNot": person.onDutyOrNot,
                "personnelCategory": person.personnelCategory,

                # 匹配到的 User.id
                "user_id": user_id,
                "bindable": can_bind,
            }

            # 关键：人员挂部门
            # SyncPerson.organizationCode == SyncDept.mdmCode
            person_dept_code = person.organizationCode

            if person_dept_code:
                person_dept_code = str(person_dept_code).strip()

            if person_dept_code and person_dept_code in node_map:
                node_map[person_dept_code]["children"].append(person_node)
            else:
                no_dept_person_nodes.append(person_node)

        # 8. 根节点
        roots = list(company_map.values()) + no_company_roots

        if no_dept_person_nodes:
            roots.append({
                "id": "unmatched_persons",
                "key": "unmatched_persons",
                "value": "unmatched_persons",
                "title": "未匹配部门人员",
                "type": "group",
                "selectable": False,
                "disabled": True,
                "children": no_dept_person_nodes,
            })

        # 9. 搜索时裁剪空组织节点
        def prune_empty_nodes(nodes):
            result = []

            for node in nodes:
                children = node.get("children") or []

                if children:
                    node["children"] = prune_empty_nodes(children)

                # 人员节点保留
                if node.get("type") == "person":
                    result.append(node)
                    continue

                # 命中的部门保留
                if node.get("matched"):
                    result.append(node)
                    continue

                # 公司/部门/group 只要下面还有子节点就保留
                if node.get("children"):
                    result.append(node)

            return result

        # 10. 清理空 children
        def clean_empty_children(nodes):
            for node in nodes:
                children = node.get("children") or []

                if children:
                    clean_empty_children(children)
                else:
                    node.pop("children", None)

        if keyword:
            roots = prune_empty_nodes(roots)

        clean_empty_children(roots)

        return get_json_result(data=roots)

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)