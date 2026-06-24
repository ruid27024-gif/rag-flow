from quart import request

from api.apps import current_user, login_required
from api.db.db_models import AdminUser, Group, User, UserGroup, SyncPerson, SyncDept
from api.db.services.user_group_service import UserGroupService
from api.db.services.group_service import GroupService
from api.utils.api_utils import get_json_result, get_request_json, server_error_response, validate_request
from common.constants import RetCode
from common import settings
from api.db.services.kb_access_service import KnowledgebaseAccessService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.file_admin_service import FileAdminService
from api.db.services.file_group_service import FileGroupService
from api.db.services.file_service import FileService
from api.db import FileType
from api.db.services import UserService
from peewee import IntegrityError
from api.db.db_models import DB
from peewee import JOIN
from api.db.db_models import File, File_Group,File_Admin

def check_admin(user):
    is_admin = AdminUser.query(user_id=user.id, role_level=1)
    if not is_admin:
        return get_json_result(
            data=False,
            message="Only admin users can perform this action.",
            code=RetCode.OPERATING_ERROR,
        )
    return None


def check_group_admin(user):
    is_admin = AdminUser.query(user_id=user.id)
    if not is_admin:
        return get_json_result(
            data=False,
            message="Only admin users can perform this action.",
            code=RetCode.OPERATING_ERROR,
        )
    return None


# @manager.route("/my_group/members", methods=["GET"])  # noqa: F821
# @login_required
# async def list_my_group_members():
#     try:
#         error_response = check_group_admin(current_user)
#         if error_response:
#             return error_response

#         # Find current user's group
#         user_group = UserGroup.select().where(UserGroup.user_id == current_user.id).first()
#         if not user_group:
#             return get_json_result(data=[])

#         group_id = user_group.group_id
        
#         rows = list(
#             UserGroup.select(UserGroup.user_id, UserGroup.created_by, UserGroup.created_time).where(
#                 UserGroup.group_id == group_id
#             )
#         )
#         user_ids = list({r.user_id for r in rows} | {r.created_by for r in rows})
#         nickname_by_user_id = {}
#         if user_ids:
#             # nickname_by_user_id = {
#             #     u.id: u.nickname
#             #     for u in User.select(User.id, User.nickname).where(User.id.in_(user_ids))
#             # }

#             query = (
#                 User
#                 .select(
#                     User.id,
#                     User.nickname,
#                     SyncPerson.phone,
#                     SyncPerson.gender,
#                     SyncDept.mdmCode,         
#                     SyncDept.nameOfAdminOrg, 
#                     SyncDept.corporateName 
#                 )
#                 # 1. User 关联 SyncPerson
#                 # 保持原样，假设 User.email 和 SyncPerson.phone 都是 unicode_ci
#                 .join(
#                     SyncPerson, 
#                     on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
#                     join_type=JOIN.LEFT_OUTER
#                 )
#                 .switch(User)
#                 # 2. SyncPerson 关联 SyncDept (关键修改点)
#                 # 将 collate 改为 'utf8mb4_0900_ai_ci' 以匹配 SyncDept 表的默认规则
#                 .join(
#                     SyncDept, 
#                     on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
#                     join_type=JOIN.LEFT_OUTER
#                 )
#             )

#             results = (
#                 query
#                 .where(User.id.in_(user_ids))
#                 .dicts() 
#             )

#             # 2. 处理结果：把列表转成以 id 为 key 的字典
#             # 结构示例: { 101: { "id": 101, "nickname": "...", "phone": "...", ... }, ... }
#             user_info_map = {item['id']: item for item in results}


#         data = [
#             {
#                 "user_id": r.user_id,
#                 "nickname": user_info_map.get(r.user_id, {}).get("nickname"),
#                 "created_by": r.created_by,
#                 "created_by_nickname": nickname_by_user_id.get(r.created_by),
#                 "created_time": r.created_time,

#                 "phone": user_info_map.get(r.user_id, {}).get("phone"),
#                 "gender": user_info_map.get(r.user_id, {}).get("gender"),
        
#                 "mdmCode": user_info_map.get(r.user_id, {}).get("mdmCode"),
#                 "nameOfAdminOrg": user_info_map.get(r.user_id, {}).get("nameOfAdminOrg"),
#                 "corporateName": user_info_map.get(r.user_id, {}).get("corporateName"),
#             }
#             for r in rows
#         ]

#         print(data)
#         return get_json_result(data=data)
#     except Exception as e:
#         return server_error_response(e)

@manager.route("/my_group/members", methods=["GET"])  # noqa: F821
@login_required
async def list_my_group_members():
    try:
        error_response = check_group_admin(current_user)
        if error_response:
            return error_response

        # Find current user's group
        user_group = UserGroup.select().where(UserGroup.user_id == current_user.id).first()
        if not user_group:
            return get_json_result(data=[])

        group_id = user_group.group_id
        
        rows = list(
            UserGroup.select(UserGroup.user_id, UserGroup.created_by, UserGroup.created_time).where(
                UserGroup.group_id == group_id
            )
        )
        # 注意：这里也要把 created_by 的 user_id 加入集合，防止创建者信息漏查
        user_ids = list({r.user_id for r in rows} | {r.created_by for r in rows})
        
        # 初始化字典
        user_info_map = {}
        
        if user_ids:
            query = (
                User
                .select(
                    User.id,
                    User.nickname,
                    SyncPerson.phone,
                    SyncPerson.gender,
                    SyncDept.mdmCode,         
                    SyncDept.nameOfAdminOrg, 
                    SyncDept.corporateName,
                    AdminUser.role_level  # 💡 1. 新增：选中管理员等级字段
                )
                # 1. User 关联 SyncPerson
                .join(
                    SyncPerson, 
                    on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                    join_type=JOIN.LEFT_OUTER
                )
                .switch(User)
                # 2. SyncPerson 关联 SyncDept
                .join(
                    SyncDept, 
                    on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                    join_type=JOIN.LEFT_OUTER
                )
                .switch(User) # 💡 2. 新增：切回 User 表，准备关联 AdminUser
                # 3. User 关联 AdminUser
                .join(
                    AdminUser, 
                    on=(User.id == AdminUser.user_id), 
                    join_type=JOIN.LEFT_OUTER # 使用左连接，确保普通用户也能查出来
                )
            )

            results = (
                query
                .where(User.id.in_(user_ids))
                .dicts() 
            )

            # 将查询结果转为字典，方便后续取值
            user_info_map = {item['id']: item for item in results}

        # 组装最终返回的数据
        data = []
        for r in rows:
            info = user_info_map.get(r.user_id, {})
            role_level = info.get("role_level")
            
            data.append({
                "user_id": r.user_id,
                "nickname": info.get("nickname"),
                "created_by": r.created_by,
                "created_by_nickname": user_info_map.get(r.created_by, {}).get("nickname"),
                "created_time": r.created_time,

                "phone": info.get("phone"),
                "gender": info.get("gender"),
        
                "mdmCode": info.get("mdmCode"),
                "nameOfAdminOrg": info.get("nameOfAdminOrg"),
                "corporateName": info.get("corporateName"),
                
                # 💡 3. 新增：返回管理员相关字段
                "role_level": role_level,
                # 如果 role_level 大于 0，则 is_admin 为 True
                "is_admin": bool(role_level and role_level > 0) 
            })

        print(data)

        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)
    
# 二级管理员一键拉取用户到自己的组内
@manager.route("/my_group/members/add_all", methods=["POST"])  # noqa: F821
@login_required
@validate_request()
async def add_member_to_my_group_all():
    req = await get_request_json()


    error_response = check_group_admin(current_user)
    if error_response:
        return error_response

    user_group = UserGroup.select().where(UserGroup.user_id == current_user.id).first()
    if not user_group:
            return get_json_result(
            code=RetCode.OPERATING_ERROR,
            message="You do not have a group. Please create one first."
        )
    


    admin = AdminUser.select().where(AdminUser.role_level  == 1).first()
    admin_id = admin.user_id

    # 获取当前的组id
    group_id = req["group_id"]
    print(f'当前组id为：{group_id}')

    # 根据组id获取组名称
    group_name = GroupService.get_name_by_id(group_id)
    print(group_name)

    # 通过组名称获取所有人
    persons = SyncPerson.select().where(SyncPerson.organize == group_name.strip())
    print(persons)
    for p in persons:
        # 打印你需要的字段，比如 mdmName、phone、email 等
        print(f"姓名: {p.mdmName}, 手机号: {p.phone}, 邮箱: {p.email}")

    success_count = 0
    # 遍历每一个人
    for person in persons:
        # 获取每一个人的账号
        phone = person.phone
        print(person.mdmName)
        # 过滤自己
        if User.email != phone:
            # 通过账号获取每一个人的id
            try:
                # 尝试获取匹配该邮箱的用户对象
                user = User.get(User.email == phone)
                # 获取该用户的 id
                user_id = user.id
                print(f"获取到的用户ID为: {user_id}")
                # 判断该用户是否已经存在组内
                user_in_group = UserGroup.get_or_none(
                    (UserGroup.user_id == user_id) &
                    (UserGroup.group_id == group_id)
                )
                print(user_in_group)
                if not user_in_group:
                    print("存在未录入的数据")
                    # 把人员拉入组内
                    obj = UserGroupService.save(
                        user_id=user_id,
                        group_id=group_id,
                        created_by=current_user.id,
                    )

                    # 拿到当前用户的根
                    add_user = UserService.filter_by_id(user_id)

                    file = FileService.get_root_folder(user_id)
                    print(file)
                    # 直接把人挂到1级表的对应组号上
                    file1 = FileAdminService.insert({
                        "id": file['id'],  # 昵称的id
                        "parent_id": group_id,
                        "tenant_id": admin_id,
                        "created_by": current_user.id,
                        "name": user.nickname,
                        "location": "",
                        "size": 0,
                        "type": FileType.FOLDER.value
                    })

                    # 将非根目录全部写入到一级表
                    # 获取当前人员的根
                    file_mem = FileService.get_root_folder(user_id)
                    person_id = file_mem['id']
                    # 将人员文件全部挂在组id下面
                    # 当前人员的非根文件
                    file_person_root_fei = File.select().where((File.id != File.parent_id)
                                                            & (File.tenant_id == person_id)
                                                            )
                    # 1级表中是否已经存在
                    file_person_admin = File_Admin.select().where((File_Admin.parent_id == person_id)
                                                            & (File_Admin.tenant_id == user_id)
                                                            )
                    
                    # 如果之前1级表中不存在就写入
                    if not file_person_admin.exists():
                    # 将文件全部写入1级表
                        for i in file_person_root_fei:
                            i.to_dict()

                            try:
                                File_Admin.create(**i.to_dict())
                            except:
                                pass


                    # 判断组内是否存在二级管理员
                    query = (AdminUser
                            .select()
                            .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))  # 通过 user_id 进行连接
                            .where((UserGroup.group_id == group_id) & (AdminUser.role_level == 2)))  # 设置筛选条件

                    admin = query.get_or_none()
                    if admin:
                        # 2. 获取第一个结果 （组管理员）
                        group_user = query.first()
                        # 获取组管理员的根目录
                        root_folder = FileService.model.select().where(
                            (FileService.model.tenant_id == group_user.user_id), (
                                    FileService.model.parent_id == FileService.model.id)).first()
                        # 根目录id
                        pf_id = root_folder.id
                        # 将新增用户添加到二级别表
                        file3 = FileGroupService.insert({
                            "id": file['id'],  # 昵称的id
                            "parent_id": pf_id,
                            "tenant_id": group_user.user_id,
                            "created_by": group_user.user_id,
                            "name": add_user.nickname,
                            "location": "",
                            "size": 0,
                            "type": FileType.FOLDER.value
                        })

                        # 将非根目录全部写入到二级表
                        # 2级表中是否已经存在
                        file_person_group = File_Group.select().where((File_Group.parent_id == person_id)
                                                                & (File_Group.tenant_id == user_id)
                                                                )
                        
                        # 文件全部写入到2级表
                        if not file_person_group.exists():
                            for i in file_person_root_fei:
                                i.to_dict()
                                print(i.to_dict())
                                try:
                                    File_Group.create(**i.to_dict())
                                except:
                                    pass
                        success_count += 1
                            
            except User.DoesNotExist:
                print("该邮箱没有对应的用户")


    return get_json_result(data={
        "success_count": success_count, 
        "msg": f"成功拉取 {success_count} 名成员"
    })  



# 二级管理员添加用户到自己的组内
@manager.route("/my_group/members/add", methods=["POST"])  # noqa: F821
@login_required
@validate_request("user_id")
async def add_member_to_my_group():
    req = await get_request_json()
    user_id = req["user_id"]
    try:
        error_response = check_group_admin(current_user)
        if error_response:
            return error_response

        user_group = UserGroup.select().where(UserGroup.user_id == current_user.id).first()
        if not user_group:
             return get_json_result(
                code=RetCode.OPERATING_ERROR,
                message="You do not have a group. Please create one first."
            )
        group_id = user_group.group_id

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


        user = UserService.filter_by_id(user_id)
        root_folder = FileService.get_root_folder(tenant_id=user_id)
        pf_id = root_folder["id"]

        admin = AdminUser.select().where(AdminUser.role_level  == 1).first()
        admin_id = admin.user_id

        # 1级表 人员挂到组内
        file = FileAdminService.insert({
            "id": pf_id,  # 昵称的id
            "parent_id": group_id,
            "tenant_id": admin_id,
            "created_by": admin_id,
            "name": user.nickname,
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value
        })

        team_id = current_user.id
        # 获取自己的根id
        root_folder = FileService.get_root_folder(team_id)
        root_id = root_folder["id"]        

        # 二级表
        # todo : 人员挂到自己身上
        file = FileGroupService.insert({
            "id": pf_id,  # 昵称的id
            "parent_id": root_id,
            "tenant_id": team_id,
            "created_by": team_id,
            "name": user.nickname,
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value
        })

        return get_json_result(data={"id": obj.id})
    except Exception as e:
        return server_error_response(e)


@manager.route("/my_group/members/remove", methods=["POST"])  # noqa: F821
@login_required
@validate_request("user_id")
async def remove_member_from_my_group():
    req = await get_request_json()
    user_id = req["user_id"]
    try:
        error_response = check_group_admin(current_user)
        if error_response:
            return error_response

        user_group = UserGroup.select().where(UserGroup.user_id == current_user.id).first()
        if not user_group:
             return get_json_result(
                code=RetCode.OPERATING_ERROR,
                message="You do not have a group."
            )
        group_id = user_group.group_id

        deleted = UserGroupService.delete_by_user_group(user_id=user_id, group_id=group_id)
        root_folder = FileService.get_root_folder(tenant_id=user_id)
        pf_id = root_folder["id"]
        print(pf_id)
        print(user_id)
        # 移除1、2级别表
        # 执行删除
        admin_deleted = FileAdminService.model.delete().where(FileAdminService.model.id == pf_id).execute()
        group_deleted = FileGroupService.model.delete().where(FileGroupService.model.id == pf_id).execute()
        
        print(f">>> 4. 删除执行完毕，Admin表影响行数: {admin_deleted}, Group表影响行数: {group_deleted}")

        return get_json_result(data={"deleted": deleted})
    except Exception as e:
        return server_error_response(e)
    
    
# 拉取全量的人员数据入组
# 1级别管理员拉人 + 参考库挂接
# @manager.route("/new_all", methods=["POST"])  # noqa: F821
# @login_required
# @validate_request("group_id")
# async def add_all_user_to_group():
#     req = await get_request_json()
#     # 获取当前的组id
#     group_id = req["group_id"]
#     print(group_id)

#     # 根据组id获取组名称
#     group_name = GroupService.get_name_by_id(group_id)

#     # 通过组名称获取所有人
#     persons = SyncPerson.select().where(SyncPerson.organize == group_name)
#     for p in persons:
#     # 打印你需要的字段，比如 mdmName、phone、email 等
#         print(f"姓名: {p.mdmName}, 手机号: {p.phone}, 邮箱: {p.email}")
#     success_count = 0
#     # 遍历每一个人
#     for person in persons:
#         # 获取每一个人的账号
#         phone = person.phone
#         # 通过账号获取每一个人的id
        
#         # 尝试获取匹配该邮箱的用户对象
#         user = User.get(User.email == phone)
#         # 获取该用户的 id
#         user_id = user.id
#         print(f"获取到的用户ID为: {user_id}")
#         # 判断该用户是否已经存在组内
#         user_in_group = UserGroup.get_or_none(
#             (UserGroup.user_id == user_id) &
#             (UserGroup.group_id == group_id)
#         )
#         # 💡 优化1：增加计数器，统计成功拉取的人数
#         print(user_in_group)

#         if not user_in_group:
#             success_count += 1
#             print(success_count)
#             # 把人员拉入组内
#             obj = UserGroupService.save(
#                 user_id=user_id,
#                 group_id=group_id,
#                 created_by=current_user.id,
#             )

#             # 拿到当前用户的根
#             add_user = UserService.filter_by_id(user_id)

#             file = FileService.get_root_folder(user_id)

#             # 直接把人挂到1级表的组id下面
#             file1 = FileAdminService.insert({
#                 "id": file['id'],  # 昵称的id
#                 "parent_id": group_id,
#                 "tenant_id": current_user.id,
#                 "created_by": current_user.id,
#                 "name": user.nickname,
#                 "location": "",
#                 "size": 0,
#                 "type": FileType.FOLDER.value
#             })

#             # 获取当前人员的根
#             file_mem = FileService.get_root_folder(user_id)
#             person_id = file_mem['id']
#             # 将人员文件全部挂在组id下面
#             # 当前人员的非根文件
#             file_person_root_fei = File.select().where((File.id != File.parent_id)
#                                                     & (File.tenant_id == person_id)
#                                                     )
#             # 1级表中是否已经存在
#             file_person_admin = File_Admin.select().where((File_Admin.parent_id == person_id)
#                                                     & (File_Admin.tenant_id == user_id)
#                                                     )
            
#             # 如果之前二级表中不存在就写入
#             if not file_person_admin.exists():
#                 print("不存在")
#                 # 将文件全部写入到全局参考库下
#                 for i in file_person_root_fei:
#                     i.to_dict()
#                     print(i.to_dict())
#                     try:
#                         File_Admin.create(**i.to_dict())
#                     except:
#                         pass

            
#             # 2级表中是否已经存在
#             file_person_group = File_Group.select().where((File_Group.parent_id == person_id)
#                                                     & (File_Group.tenant_id == user_id)
#                                                     )

#             # 判断组内是否存在二级管理员
#             query = (AdminUser
#                         .select()
#                         .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))  # 通过 user_id 进行连接
#                         .where((UserGroup.group_id == group_id) & (AdminUser.role_level == 2)))  # 设置筛选条件

#             admin_group = query.get_or_none()
#             if admin_group:
#                 # 2. 获取第一个结果 （组管理员）
#                 group_user = query.first()
#                 # 获取组管理员的根目录
#                 root_folder = FileService.model.select().where((FileService.model.tenant_id == group_user.user_id), (
#                         FileService.model.parent_id == FileService.model.id)).first()
#                 # 根目录id
#                 pf_id = root_folder.id
#                 # 将新增用户添加到二级别表
#                 file3 = FileGroupService.insert({
#                     "id": file['id'],  # 昵称的id
#                     "parent_id": pf_id,
#                     "tenant_id": group_user.user_id,
#                     "created_by": group_user.user_id,
#                     "name": add_user.nickname,
#                     "location": "",
#                     "size": 0,
#                     "type": FileType.FOLDER.value
#                 })

#                 # 文件全部写入到2级表
#                 if not file_person_group.exists():
#                     for i in file_person_root_fei:
#                         i.to_dict()
#                         print(i.to_dict())
#                         try:
#                             File_Group.create(**i.to_dict())
#                         except:
#                             pass

#     # 💡 优化4：返回标准的 JSON 结果
#     return get_json_result(data={
#         "success_count": success_count, 
#         "msg": f"全量拉取完成，成功拉取 {success_count} 名成员"
#     })

# 拉取全量的人员数据入组
# 1级别管理员拉人 + 参考库挂接
@manager.route("/new_all", methods=["POST"])  # noqa: F821
@login_required
@validate_request("group_id")
async def add_all_user_to_group():
    req = await get_request_json()

    # 获取当前的组id
    group_id = req["group_id"]
    print(group_id)

    # 根据组id获取组名称
    group_name = GroupService.get_name_by_id(group_id)

    # ===============================
    # 参考库挂到 1 级表 File_Admin
    # 逻辑：
    # 1. 当前组配置了参考库 tenant
    # 2. 查到参考库根目录
    # 3. File_Admin 中不存在该参考库 id，则插入
    # 4. 如果已存在但 parent_id 不是当前 group_id，则更新 parent_id
    # ===============================
    cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
    group_public_id = cfg_map.get(group_id)

    if group_public_id:
        ref_root = File.select().where(
            (File.parent_id == File.id)
            & (File.tenant_id == group_public_id)
        ).first()

        if ref_root:
            print(ref_root)
            exists_ref = File_Admin.select().where(
                File_Admin.id == ref_root.id
            ).first()

            print(exists_ref)
            print("----------------------------")
            if not exists_ref:
                FileAdminService.insert({
                    "id": ref_root.id,
                    "parent_id": group_id,
                    "tenant_id": current_user.id,
                    "created_by": current_user.id,
                    "name": '参考库+报告库',
                    "location": ref_root.location or "",
                    "size": ref_root.size or 0,
                    "type": ref_root.type or FileType.FOLDER.value,
                })
            elif exists_ref.parent_id != group_id:
                File_Admin.update({
                    File_Admin.parent_id: group_id,
                    File_Admin.tenant_id: current_user.id,
                    File_Admin.created_by: current_user.id,
                    File_Admin.name: '参考库+报告库',
                }).where(
                    File_Admin.id == ref_root.id
                ).execute()

    # 通过组名称获取所有人
    persons = SyncPerson.select().where(SyncPerson.organize == group_name)

    for p in persons:
        print(f"姓名: {p.mdmName}, 手机号: {p.phone}, 邮箱: {p.email}")

    success_count = 0

    # 遍历每一个人
    for person in persons:
        # 获取每一个人的账号
        phone = person.phone

        # 通过账号获取每一个人的id
        user = User.get(User.email == phone)
        user_id = user.id
        print(f"获取到的用户ID为: {user_id}")

        # 判断该用户是否已经存在组内
        user_in_group = UserGroup.get_or_none(
            (UserGroup.user_id == user_id)
            & (UserGroup.group_id == group_id)
        )

        print(user_in_group)

        if not user_in_group:
            success_count += 1
            print(success_count)

            # 把人员拉入组内
            obj = UserGroupService.save(
                user_id=user_id,
                group_id=group_id,
                created_by=current_user.id,
            )

            # 拿到当前用户
            add_user = UserService.filter_by_id(user_id)

            # 拿到当前用户的根目录
            file = FileService.get_root_folder(user_id)

            # 直接把人挂到 1 级表的组id下面
            FileAdminService.insert({
                "id": file["id"],
                "parent_id": group_id,
                "tenant_id": current_user.id,
                "created_by": current_user.id,
                "name": user.nickname,
                "location": "",
                "size": 0,
                "type": FileType.FOLDER.value,
            })

            # 获取当前人员的根
            file_mem = FileService.get_root_folder(user_id)
            person_id = file_mem["id"]

            # 当前人员的非根文件
            file_person_root_fei = File.select().where(
                (File.id != File.parent_id)
                & (File.tenant_id == person_id)
            )

            # 1级表中是否已经存在当前人员文件
            file_person_admin = File_Admin.select().where(
                (File_Admin.parent_id == person_id)
                & (File_Admin.tenant_id == user_id)
            )

            # 如果之前1级表中不存在就写入
            if not file_person_admin.exists():
                print("不存在")
                for i in file_person_root_fei:
                    print(i.to_dict())
                    try:
                        File_Admin.create(**i.to_dict())
                    except Exception:
                        pass

            # 2级表中是否已经存在
            file_person_group = File_Group.select().where(
                (File_Group.parent_id == person_id)
                & (File_Group.tenant_id == user_id)
            )

            # 判断组内是否存在二级管理员
            query = (
                AdminUser
                .select()
                .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))
                .where(
                    (UserGroup.group_id == group_id)
                    & (AdminUser.role_level == 2)
                )
            )

            admin_group = query.get_or_none()

            if admin_group:
                # 获取第一个组管理员
                group_user = query.first()

                # 获取组管理员的根目录
                root_folder = FileService.model.select().where(
                    (FileService.model.tenant_id == group_user.user_id)
                    & (FileService.model.parent_id == FileService.model.id)
                ).first()

                # 根目录id
                pf_id = root_folder.id

                # 将新增用户添加到二级表
                FileGroupService.insert({
                    "id": file["id"],
                    "parent_id": pf_id,
                    "tenant_id": group_user.user_id,
                    "created_by": group_user.user_id,
                    "name": add_user.nickname,
                    "location": "",
                    "size": 0,
                    "type": FileType.FOLDER.value,
                })

                # 文件全部写入到2级表
                if not file_person_group.exists():
                    for i in file_person_root_fei:
                        print(i.to_dict())
                        try:
                            File_Group.create(**i.to_dict())
                        except Exception:
                            pass

    return get_json_result(data={
        "success_count": success_count,
        "msg": f"全量拉取完成，成功拉取 {success_count} 名成员",
    })


# 1级别管理员拉人
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
        
        # --- 修改开始：在保存前检查组内是否有二级管理员 ---
        query = (AdminUser
                .select()
                .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))
                .where((UserGroup.group_id == group_id) & (AdminUser.role_level == 2)))
        

        existing_manager = query.get_or_none()

        is_new_user_manager = AdminUser.query(user_id=user_id, role_level=2)


        
        if not existing_manager and not is_new_user_manager:
             return get_json_result(
                code=RetCode.DATA_ERROR,
                message="请先拉一个组管理员入组",
            )

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

        # 拿到当前用户的根
        add_user = UserService.filter_by_id(user_id)
        # 从FILE表获取用户的file_id
        # file = File.select().where((File.parent_id == File.id)
        #                 & (File.tenant_id == add_user.id)).first()
        file = FileService.get_root_folder(add_user.id)

        # 直接把人挂到1级表
        file1 = FileAdminService.insert({
            "id": file['id'],  # 昵称的id
            "parent_id": group_id,
            "tenant_id": current_user.id,
            "created_by": current_user.id,
            "name": add_user.nickname,
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value
        })


        # 判断拉入的用户是否为二级管理员
        if AdminUser.query(user_id=user_id, role_level=2):
            # 直接把自己加入到二级表

            pf_id = file['id']
            try:
                # file2 = FileGroupService.insert({
                #     "id": pf_id,  # 昵称的id
                #     "parent_id": pf_id,
                #     "tenant_id": user_id,
                #     "created_by": user_id,
                #     "name": "/",
                #     "location": "",
                #     "size": 0,
                #     "type": FileType.FOLDER.value
                # })
                # 把当前组参考库挂载到这个根上 根据组id获取参考库的id

                cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
                if group_id and group_id in cfg_map and cfg_map[group_id]:
                    group_public_id = cfg_map[group_id]

                # 获取当前组参考库的根
                file_ref = FileService.get_root_folder(group_public_id)
                pf_id_ref = file_ref['id']

                # 把当前组参考库挂载到这个根上 根据组id获取参考库的id
                file2 = FileGroupService.insert({
                    "id": pf_id_ref,  # 昵称的id
                    "parent_id": pf_id,
                    "tenant_id": user_id,
                    "created_by": user_id,
                    "name": "组参考库+文献库",
                    "location": "",
                    "size": 0,
                    "type": FileType.FOLDER.value
                })

                # 把参考库下的所有文件挂载到当前的组参考库下
                # 把参考库中不是根目录的全部写入二级表
                from api.db.db_models import File, File_Group
                file_group_ref = File.select().where((File.id != File.parent_id)
                                & (File.tenant_id == group_public_id )
                                )
                # 将文件全部写入到全局参考库下
                for i in file_group_ref:
                    i.to_dict()
                    print(i.to_dict())
                    try:
                        File_Group.create(**i.to_dict())
                    except:
                        pass

                pass
            except Exception as e:
                pass

        else:
            try:
                # 获取当前组的管理员
                # 1. 构建查询
                query = (AdminUser
                        .select()
                        .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))  # 通过 user_id 进行连接
                        .where((UserGroup.group_id == group_id) & (AdminUser.role_level == 2)))  # 设置筛选条件

                # 2. 获取第一个结果
                group_user = query.first()

                print(group_user.to_dict())
                print(group_user.user_id)
                print("---------------------------------------------------------------")
                # 3. 将当前用户挂载到管理员
                # root_folder = FileService.get_root_folder(tenant_id=group_user.user_id)

                root_folder = FileService.model.select().where((FileService.model.tenant_id == group_user.user_id), (FileService.model.parent_id == FileService.model.id)).first()
                pf_id = root_folder.id
                file3 = FileGroupService.insert({
                    "id": file['id'],  # 昵称的id
                    "parent_id": pf_id,
                    "tenant_id": group_user.user_id,
                    "created_by": group_user.user_id,
                    "name": add_user.nickname,
                    "location": "",
                    "size": 0,
                    "type": FileType.FOLDER.value
                })
            except AdminUser.DoesNotExist:
                raise Exception("请先拉一个组管理员入组")


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


    error_response = check_admin(current_user)
    if error_response:
        return error_response
    file = FileService.get_root_folder(user_id)

    # 删除1级表、二级表中人员到组的连接
    FileAdminService.model.delete().where(FileAdminService.model.id == file['id']).execute()
    FileGroupService.model.delete().where(FileGroupService.model.id == file['id']).execute()


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
    
    # except Exception as e:
    #     return server_error_response(e)


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
        error_response = check_group_admin(current_user)
        if error_response:
            return error_response


        query = (
            User
            .select(
                User.id,
                User.nickname,
                SyncPerson.phone,
                SyncPerson.gender,
                SyncDept.mdmCode,         
                SyncDept.nameOfAdminOrg, 
                SyncDept.corporateName 
            )
            # 1. User 关联 SyncPerson
            # 保持原样，假设 User.email 和 SyncPerson.phone 都是 unicode_ci
            .join(
                SyncPerson, 
                on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                join_type=JOIN.LEFT_OUTER
            )
            .switch(User)
            # 2. SyncPerson 关联 SyncDept (关键修改点)
            # 将 collate 改为 'utf8mb4_0900_ai_ci' 以匹配 SyncDept 表的默认规则
            .join(
                SyncDept, 
                on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                join_type=JOIN.LEFT_OUTER
            )
        )

        # 1. Find all users who are already in any group
        bound_user_ids = {r.user_id for r in UserGroup.select(UserGroup.user_id)}
        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        group_ref_ids = set(cfg_map.values())
        excluded_ids_list = list(bound_user_ids | group_ref_ids)
        
        # 2. Find users NOT in that list
        if excluded_ids_list:
            candidates = list(
                query.where(
                    User.id.not_in(excluded_ids_list),
                    User.id != settings.REFERENCE_TENANT_ID if settings.REFERENCE_TENANT_ID else True,
                )
            )
        else:
            if settings.REFERENCE_TENANT_ID:
                candidates = list(
                    query.where(User.id != settings.REFERENCE_TENANT_ID)
                )
            else:
                candidates = list(query)

        # data = [{"user_id": u.id, "nickname": u.nickname, "phone": u.phone,
        #         "gender": u.gender, "mdmCode": u.mdmCode, 
        #         "nameOfAdminOrg": u.nameOfAdminOrg, "corporateName":u.corporateName} for u in candidates]

        data = []
        for u in candidates:
            # 增加空值保护，防止关联数据为 None 时报错
            sync_p = getattr(u, 'syncperson', None)
            sync_d = getattr(u, 'syncdept', None)
            
            data.append({
                "user_id": u.id, 
                "nickname": u.nickname, 
                "phone": sync_p.phone if sync_p else None,
                "gender": sync_p.gender if sync_p else None,
                "mdmCode": sync_d.mdmCode if sync_d else None, 
                "nameOfAdminOrg": sync_d.nameOfAdminOrg if sync_d else None, 
                "corporateName": sync_d.corporateName if sync_d else None
            })

        print(data[0])

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
        # 收集所有需要查询详情的 user_id
        user_ids = list({r.user_id for r in rows} | {r.created_by for r in rows})
        
        user_info_map = {}
        if user_ids:
            query = (
                User
                .select(
                    User.id,
                    User.nickname,
                    SyncPerson.phone,
                    SyncPerson.gender,
                    SyncDept.mdmCode,         
                    SyncDept.nameOfAdminOrg, 
                    SyncDept.corporateName,
                    AdminUser.role_level  # 💡 1. 新增：选中管理员等级字段
                )
                # 1. User 关联 SyncPerson
                .join(
                    SyncPerson, 
                    on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                    join_type=JOIN.LEFT_OUTER
                )
                .switch(User)
                # 2. SyncPerson 关联 SyncDept
                .join(
                    SyncDept, 
                    on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                    join_type=JOIN.LEFT_OUTER
                )
                .switch(User) # 💡 2. 新增：切回 User 表，准备关联 AdminUser
                # 3. User 关联 AdminUser (左连接，保证非管理员也能查出来)
                .join(
                    AdminUser, 
                    on=(User.id == AdminUser.user_id), 
                    join_type=JOIN.LEFT_OUTER
                )
            )

            results = (
                query
                .where(User.id.in_(user_ids))
                .dicts() 
            )

            # 把查询结果转为以 user_id 为 key 的字典，方便后续快速取值
            user_info_map = {item['id']: item for item in results}

        # 组装最终返回的数据
        data = [
            {
                "user_id": r.user_id,
                "nickname": user_info_map.get(r.user_id, {}).get("nickname"),
                "created_by": r.created_by,
                "created_by_nickname": user_info_map.get(r.created_by, {}).get("nickname"),
                "created_time": r.created_time,

                "phone": user_info_map.get(r.user_id, {}).get("phone"),
                "gender": user_info_map.get(r.user_id, {}).get("gender"),
        
                "mdmCode": user_info_map.get(r.user_id, {}).get("mdmCode"),
                "nameOfAdminOrg": user_info_map.get(r.user_id, {}).get("nameOfAdminOrg"),
                "corporateName": user_info_map.get(r.user_id, {}).get("corporateName"),
                
                # 💡 3. 新增：返回管理员相关字段
                "role_level": user_info_map.get(r.user_id, {}).get("role_level"),
                "is_admin": bool(user_info_map.get(r.user_id, {}).get("role_level") and user_info_map.get(r.user_id, {}).get("role_level") > 0)
            }
            for r in rows
        ]

        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)
    

@manager.route("/allkbmembers", methods=["GET"])  # noqa: F821
@validate_request("kb_id")
async def list_all_kb_members():
    kb_id = request.args.get("kb_id")
    # print(kb_id)
    cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
    reverse_cfg_map = {tid: gid for gid, tid in cfg_map.items()}
    # 通过kb_id获取tenant_id
    kb = KnowledgebaseService.get_detail(kb_id)
    tenant_id = kb["created_by"]
    if tenant_id == settings.REFERENCE_TENANT_ID:
        print("全局参考库权限管理")
    # 👇 优化点：用 list() 显式转换一下，防止后续出现类型问题
        group_ids = list(cfg_map.keys())
        print(group_ids)
        try:
            rows = list(
                UserGroup.select(
                UserGroup.user_id, 
                UserGroup.created_by, 
                UserGroup.created_time
            ).where(
                # 👇 核心修改：把 in 改成 .in_()
                (UserGroup.group_id.in_(group_ids)) &  
                (UserGroup.user_id != current_user.id)
                # (UserGroup.created_by != current_user.id)
            )
            )
            
            # 后面的去重、联表查询、组装 data 的逻辑完全不用动
            user_ids = list({r.user_id for r in rows} | {r.created_by for r in rows})
            
            if user_ids:
                # ... 下面保持你原有的联表查询和 data 组装逻辑不变 ...
                query = (
                    User
                    .select(
                        User.id,
                        User.nickname,
                        SyncPerson.phone,
                        SyncPerson.gender,
                        SyncDept.mdmCode,         
                        SyncDept.nameOfAdminOrg, 
                        SyncDept.corporateName 
                    )
                    .join(
                        SyncPerson, 
                        on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                        join_type=JOIN.LEFT_OUTER
                    )
                    .switch(User)
                    .join(
                        SyncDept, 
                        on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                        join_type=JOIN.LEFT_OUTER
                    )
                )

                results = (
                    query
                    .where(User.id.in_(user_ids))
                    .dicts() 
                )

                user_info_map = {item['id']: item for item in results}

            data = [
                {
                    "user_id": r.user_id,
                    "nickname": user_info_map.get(r.user_id, {}).get("nickname"),
                    "created_by": r.created_by,
                    "created_by_nickname": user_info_map.get(r.created_by, {}).get("nickname"),
                    "created_time": r.created_time,
                    "phone": user_info_map.get(r.user_id, {}).get("phone"),
                    "gender": user_info_map.get(r.user_id, {}).get("gender"),
                    "mdmCode": user_info_map.get(r.user_id, {}).get("mdmCode"),
                    "nameOfAdminOrg": user_info_map.get(r.user_id, {}).get("nameOfAdminOrg"),
                    "corporateName": user_info_map.get(r.user_id, {}).get("corporateName"),
                }
                for r in rows
            ]

            print(data)
            return get_json_result(data=data)
        except Exception as e:
            return server_error_response(e)

    # 通过kb_id获取group_id
    
    group_id = reverse_cfg_map.get(tenant_id)
    print("属于的组id为")
    print(group_id)

    # 查询所有用户信息
    try:
        rows = list(
            UserGroup.select(
            UserGroup.user_id, 
            UserGroup.created_by, 
            UserGroup.created_time
        ).where(
            (UserGroup.group_id == group_id) &  # 必须用 & 且带上括号
            (UserGroup.user_id != current_user.id) 
            # & 
            # (UserGroup.created_by != current_user.id)
        )
        )
        user_ids = list({r.user_id for r in rows} | {r.created_by for r in rows})
        
        if user_ids:
           
            query = (
                User
                .select(
                    User.id,
                    User.nickname,
                    SyncPerson.phone,
                    SyncPerson.gender,
                    SyncDept.mdmCode,         
                    SyncDept.nameOfAdminOrg, 
                    SyncDept.corporateName 
                )
                # 1. User 关联 SyncPerson
                # 保持原样，假设 User.email 和 SyncPerson.phone 都是 unicode_ci
                .join(
                    SyncPerson, 
                    on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                    join_type=JOIN.LEFT_OUTER
                )
                .switch(User)
                # 2. SyncPerson 关联 SyncDept (关键修改点)
                # 将 collate 改为 'utf8mb4_0900_ai_ci' 以匹配 SyncDept 表的默认规则
                .join(
                    SyncDept, 
                    on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                    join_type=JOIN.LEFT_OUTER
                )
            )

            results = (
                query
                .where(User.id.in_(user_ids))
                .dicts() 
            )

            # 2. 处理结果：把列表转成以 id 为 key 的字典
            # 结构示例: { 101: { "id": 101, "nickname": "...", "phone": "...", ... }, ... }
            user_info_map = {item['id']: item for item in results}


        data = [
            {
                "user_id": r.user_id,
                "nickname": user_info_map.get(r.user_id, {}).get("nickname"),
                "created_by": r.created_by,
                "created_by_nickname": user_info_map.get(r.created_by, {}).get("nickname"),
                "created_time": r.created_time,

                "phone": user_info_map.get(r.user_id, {}).get("phone"),
                "gender": user_info_map.get(r.user_id, {}).get("gender"),
        
                "mdmCode": user_info_map.get(r.user_id, {}).get("mdmCode"),
                "nameOfAdminOrg": user_info_map.get(r.user_id, {}).get("nameOfAdminOrg"),
                "corporateName": user_info_map.get(r.user_id, {}).get("corporateName"),
            }
            for r in rows
        ]

        print(data)
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)
    

@manager.route("/writeablekbmembers", methods=["GET"])  # noqa: F821
@validate_request("kb_id")
async def list_writeable_kb_members():
    kb_id = request.args.get("kb_id")
    print(kb_id)
    # 通过kb_id获取tenant_id
    kb = KnowledgebaseService.get_detail(kb_id)
    tenant_id = kb["created_by"]
    # 通过kb_id获取group_id
    cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
    reverse_cfg_map = {tid: gid for gid, tid in cfg_map.items()}
    group_id = reverse_cfg_map.get(tenant_id)

    # 直接获取可以写入的用户
    user_ids = KnowledgebaseAccessService.get_write_users(kb_id)
    print(user_ids)
    print(len(user_ids))

    # 查询所有用户信息
        # 查询所有用户信息（从 User, SyncPerson, SyncDept 联表获取详细信息）
    try:
        # 1. 先查出这些 user_ids 对应的详细用户信息
        query = (
            User
            .select(
                User.id,
                User.nickname,
                SyncPerson.phone,
                SyncPerson.gender,
                SyncDept.mdmCode,         
                SyncDept.nameOfAdminOrg, 
                SyncDept.corporateName 
            )
            .join(
                SyncPerson, 
                on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                join_type=JOIN.LEFT_OUTER
            )
            .switch(User)
            .join(
                SyncDept, 
                on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                join_type=JOIN.LEFT_OUTER
            )
        )

        # 关键：直接在这里过滤 user_ids，不需要再查一遍 UserGroup 了！
        results = (
            query
            .where(User.id.in_(user_ids))
            .dicts() 
        )

        # 2. 处理结果：把列表转成以 id 为 key 的字典，方便下面快速取值
        user_info_map = {item['id']: item for item in results}

        # 3. 最终组装数据：直接遍历最原始的 user_ids 列表
        # 这样能保证返回的数据和 get_write_users 拿到的权限用户完全一致
        data = []
        for uid in user_ids:
            info = user_info_map.get(uid, {})
            data.append({
                "user_id": uid,
                "nickname": info.get("nickname"),
                "phone": info.get("phone"),
                "gender": info.get("gender"),
                "mdmCode": info.get("mdmCode"),
                "nameOfAdminOrg": info.get("nameOfAdminOrg"),
                "corporateName": info.get("corporateName"),
                # 注意：created_by 和 created_time 在 User 表里如果没有的话，这里可能需要从 KnowledgebaseAccess 表里另外查
                # 如果必须要这两个字段，你可能需要修改 get_write_users 让它返回更完整的信息，或者在这里做更复杂的联表
            })

        print(data)
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
