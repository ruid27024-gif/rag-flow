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

        def sync_member_files_to_file_admin(person_root_id):
            """
            把成员根目录下面的所有非根文件同步到一级表 File_Admin
            person_root_id: 成员根目录 id
            """
            member_files = File.select().where(
                (File.id != File.parent_id)
                & (File.tenant_id == person_root_id)
            )

            print(f"开始同步成员文件到一级表，person_root_id={person_root_id}, count={member_files.count()}")

            for item in member_files:
                data = item.to_dict()
                file_id = data.get("id")

                exists_file = File_Admin.select().where(
                    File_Admin.id == file_id
                ).first()

                if exists_file:
                    continue

                try:
                    File_Admin.create(**data)
                    print(f"成员文件写入 File_Admin 成功: {file_id}")
                except Exception as e:
                    print(f"成员文件写入 File_Admin 失败: {file_id}, error={e}")

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
        from api.db.db_models import File, File_Admin, File_Group

        error_response = check_admin(current_user)
        if error_response:
            return error_response

        # =====================================================
        # 查询当前组是否已有二级管理员
        # =====================================================
        manager_query = (
            AdminUser
            .select()
            .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))
            .where(
                (UserGroup.group_id == group_id)
                & (AdminUser.role_level == 2)
            )
        )

        existing_manager = manager_query.get_or_none()

        # 判断当前拉入用户是否是二级管理员
        is_new_user_manager = AdminUser.query(
            user_id=user_id,
            role_level=2
        )

        # 如果当前组没有二级管理员，并且当前拉入的人也不是二级管理员，则不允许拉普通成员
        if not existing_manager and not is_new_user_manager:
            return get_json_result(
                code=RetCode.DATA_ERROR,
                message="请先拉一个组管理员入组",
            )

        # 判断是否已经在组内
        exists = UserGroup.get_or_none(
            (UserGroup.user_id == user_id)
            & (UserGroup.group_id == group_id)
        )

        if exists:
            return get_json_result(
                code=RetCode.DATA_ERROR,
                message="User already in group.",
                data={"id": exists.id},
            )

        # =====================================================
        # 保存用户入组
        # =====================================================
        obj = UserGroupService.save(
            user_id=user_id,
            group_id=group_id,
            created_by=current_user.id,
        )

        # 当前被拉入用户信息
        add_user = UserService.filter_by_id(user_id)

        if not add_user:
            raise Exception(f"用户不存在: {user_id}")

        # 当前被拉入用户根目录
        user_root = FileService.get_root_folder(add_user.id)

        if not user_root:
            raise Exception(f"用户 {user_id} 没有根目录")

        user_root_id = user_root["id"]

        # =====================================================
        # 工具方法：同步某个用户下面的所有文件到一级表 File_Admin
        # =====================================================
        def sync_member_files_to_file_admin(member_root_id):
            member_files = File.select().where(
                (File.id != File.parent_id)
                & (File.tenant_id == member_root_id)
            )

            print(
                f"开始同步成员文件到 File_Admin，"
                f"member_root_id={member_root_id}, count={member_files.count()}"
            )

            for item in member_files:
                data = item.to_dict()
                file_id = data.get("id")

                if not file_id:
                    continue

                exists_file = File_Admin.select().where(
                    File_Admin.id == file_id
                ).first()

                if exists_file:
                    continue

                try:
                    File_Admin.create(**data)
                    print(f"成员文件写入 File_Admin 成功: {file_id}")
                except Exception as e:
                    print(f"成员文件写入 File_Admin 失败: {file_id}, error={e}")

        # =====================================================
        # 工具方法：把成员挂到一级表 File_Admin，并同步成员文件
        # =====================================================
        def mount_member_to_file_admin(member_user_id):
            member = UserService.filter_by_id(member_user_id)

            if not member:
                print(f"成员不存在: {member_user_id}")
                return

            member_root = FileService.get_root_folder(member_user_id)

            if not member_root:
                print(f"成员 {member_user_id} 没有根目录")
                return

            member_root_id = member_root["id"]

            exists_root = File_Admin.select().where(
                File_Admin.id == member_root_id
            ).first()

            if not exists_root:
                try:
                    FileAdminService.insert({
                        "id": member_root_id,
                        "parent_id": group_id,
                        "tenant_id": current_user.id,
                        "created_by": current_user.id,
                        "name": member.nickname,
                        "location": "",
                        "size": 0,
                        "type": FileType.FOLDER.value,
                    })
                    print(f"成员根节点写入 File_Admin 成功: {member_root_id}")
                except Exception as e:
                    print(f"成员根节点写入 File_Admin 失败: {member_root_id}, error={e}")
            else:
                if exists_root.parent_id != group_id:
                    try:
                        File_Admin.update({
                            File_Admin.parent_id: group_id,
                            File_Admin.tenant_id: current_user.id,
                            File_Admin.created_by: current_user.id,
                            File_Admin.name: member.nickname,
                        }).where(
                            File_Admin.id == member_root_id
                        ).execute()

                        print(f"成员根节点更新 File_Admin 成功: {member_root_id}")
                    except Exception as e:
                        print(f"成员根节点更新 File_Admin 失败: {member_root_id}, error={e}")

            # 同步成员文件到一级表
            sync_member_files_to_file_admin(member_root_id)

        # =====================================================
        # 工具方法：同步某个成员下面所有文件到二级表 File_Group
        # =====================================================
        def sync_member_files_to_file_group(member_root_id):
            member_files = File.select().where(
                (File.id != File.parent_id)
                & (File.tenant_id == member_root_id)
            )

            print(
                f"开始同步成员文件到 File_Group，"
                f"member_root_id={member_root_id}, count={member_files.count()}"
            )

            for item in member_files:
                data = item.to_dict()
                file_id = data.get("id")

                if not file_id:
                    continue

                exists_file = File_Group.select().where(
                    File_Group.id == file_id
                ).first()

                if exists_file:
                    continue

                try:
                    File_Group.create(**data)
                    print(f"成员文件写入 File_Group 成功: {file_id}")
                except Exception as e:
                    print(f"成员文件写入 File_Group 失败: {file_id}, error={e}")

        # =====================================================
        # 工具方法：确保二级管理员自己的根目录存在于 File_Group
        # =====================================================
        def ensure_manager_root_in_file_group(manager_user_id, manager_root_id):
            exists_root = File_Group.select().where(
                File_Group.id == manager_root_id
            ).first()

            if not exists_root:
                try:
                    FileGroupService.insert({
                        "id": manager_root_id,
                        "parent_id": manager_root_id,
                        "tenant_id": manager_user_id,
                        "created_by": manager_user_id,
                        "name": "/",
                        "location": "",
                        "size": 0,
                        "type": FileType.FOLDER.value,
                    })
                    print(f"二级管理员根目录写入 File_Group 成功: {manager_root_id}")
                except Exception as e:
                    print(f"二级管理员根目录写入 File_Group 失败: {manager_root_id}, error={e}")
            else:
                try:
                    File_Group.update({
                        File_Group.parent_id: manager_root_id,
                        File_Group.tenant_id: manager_user_id,
                        File_Group.created_by: manager_user_id,
                        File_Group.name: "/",
                    }).where(
                        File_Group.id == manager_root_id
                    ).execute()
                    print(f"二级管理员根目录更新 File_Group 成功: {manager_root_id}")
                except Exception as e:
                    print(f"二级管理员根目录更新 File_Group 失败: {manager_root_id}, error={e}")

        # =====================================================
        # 工具方法：把成员挂到二级管理员下面，并同步成员文件
        # =====================================================
        def mount_member_to_group_manager(member_user_id, manager_user_id, manager_root_id):
            member = UserService.filter_by_id(member_user_id)

            if not member:
                print(f"成员不存在: {member_user_id}")
                return

            member_root = FileService.get_root_folder(member_user_id)

            if not member_root:
                print(f"成员 {member_user_id} 没有根目录")
                return

            member_root_id = member_root["id"]

            exists_root = File_Group.select().where(
                File_Group.id == member_root_id
            ).first()

            if not exists_root:
                try:
                    FileGroupService.insert({
                        "id": member_root_id,
                        "parent_id": manager_root_id,
                        "tenant_id": manager_user_id,
                        "created_by": manager_user_id,
                        "name": member.nickname,
                        "location": "",
                        "size": 0,
                        "type": FileType.FOLDER.value,
                    })
                    print(f"成员根节点写入 File_Group 成功: {member_root_id}")
                except Exception as e:
                    print(f"成员根节点写入 File_Group 失败: {member_root_id}, error={e}")
            else:
                if exists_root.parent_id != manager_root_id:
                    try:
                        File_Group.update({
                            File_Group.parent_id: manager_root_id,
                            File_Group.tenant_id: manager_user_id,
                            File_Group.created_by: manager_user_id,
                            File_Group.name: member.nickname,
                        }).where(
                            File_Group.id == member_root_id
                        ).execute()

                        print(f"成员根节点更新 File_Group 成功: {member_root_id}")
                    except Exception as e:
                        print(f"成员根节点更新 File_Group 失败: {member_root_id}, error={e}")

            # 同步成员文件到二级表
            sync_member_files_to_file_group(member_root_id)

        # =====================================================
        # 工具方法：把参考库挂到一级表 File_Admin
        # 如果你的一级表已经在别的地方处理参考库，可以不调用这个方法
        # =====================================================
        def mount_reference_to_file_admin():
            cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
            group_public_id = cfg_map.get(group_id) or cfg_map.get(str(group_id))

            print("一级表参考库 group_id:", group_id)
            print("一级表参考库 group_public_id:", group_public_id)

            if not group_public_id:
                print(f"当前组 {group_id} 没有配置参考库")
                return

            ref_root = FileService.get_root_folder(group_public_id)

            if not ref_root:
                print(f"参考库 {group_public_id} 没有根目录")
                return

            ref_root_id = ref_root["id"]

            exists_ref_root = File_Admin.select().where(
                File_Admin.id == ref_root_id
            ).first()

            if not exists_ref_root:
                try:
                    FileAdminService.insert({
                        "id": ref_root_id,
                        "parent_id": group_id,
                        "tenant_id": current_user.id,
                        "created_by": current_user.id,
                        "name": "组参考库+文献库",
                        "location": "",
                        "size": 0,
                        "type": FileType.FOLDER.value,
                    })
                    print(f"参考库根节点写入 File_Admin 成功: {ref_root_id}")
                except Exception as e:
                    print(f"参考库根节点写入 File_Admin 失败: {ref_root_id}, error={e}")
            else:
                if exists_ref_root.parent_id != group_id:
                    try:
                        File_Admin.update({
                            File_Admin.parent_id: group_id,
                            File_Admin.tenant_id: current_user.id,
                            File_Admin.created_by: current_user.id,
                            File_Admin.name: "组参考库+文献库",
                        }).where(
                            File_Admin.id == ref_root_id
                        ).execute()
                        print(f"参考库根节点更新 File_Admin 成功: {ref_root_id}")
                    except Exception as e:
                        print(f"参考库根节点更新 File_Admin 失败: {ref_root_id}, error={e}")

            # 参考库下面文件写入一级表
            # 保留你的逻辑：File.tenant_id == group_public_id
            ref_files = File.select().where(
                (File.id != File.parent_id)
                & (File.tenant_id == group_public_id)
            )

            print(f"参考库文件写入 File_Admin 数量: {ref_files.count()}")

            for item in ref_files:
                data = item.to_dict()
                file_id = data.get("id")

                if not file_id:
                    continue

                exists_file = File_Admin.select().where(
                    File_Admin.id == file_id
                ).first()

                if exists_file:
                    continue

                try:
                    File_Admin.create(**data)
                    print(f"参考库文件写入 File_Admin 成功: {file_id}")
                except Exception as e:
                    print(f"参考库文件写入 File_Admin 失败: {file_id}, error={e}")

        # =====================================================
        # 工具方法：把参考库挂到二级管理员 File_Group
        # =====================================================
        def mount_reference_to_group_manager(manager_user_id, manager_root_id):
            cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
            group_public_id = cfg_map.get(group_id) or cfg_map.get(str(group_id))

            print("二级表参考库 group_id:", group_id)
            print("二级表参考库 group_public_id:", group_public_id)

            if not group_public_id:
                print(f"当前组 {group_id} 没有配置参考库")
                return

            # 获取参考库根目录
            ref_root = FileService.get_root_folder(group_public_id)

            if not ref_root:
                print(f"参考库 {group_public_id} 没有根目录")
                return

            ref_root_id = ref_root["id"]

            # 1. 参考库根节点写入 File_Group
            exists_ref_root = File_Group.select().where(
                File_Group.id == ref_root_id
            ).first()

            if not exists_ref_root:
                try:
                    FileGroupService.insert({
                        "id": ref_root_id,
                        "parent_id": manager_root_id,
                        "tenant_id": manager_user_id,
                        "created_by": manager_user_id,
                        "name": "组参考库+文献库",
                        "location": "",
                        "size": 0,
                        "type": FileType.FOLDER.value,
                    })
                    print(f"参考库根节点写入 File_Group 成功: {ref_root_id}")
                except Exception as e:
                    print(f"参考库根节点写入 File_Group 失败: {ref_root_id}, error={e}")
            else:
                if exists_ref_root.parent_id != manager_root_id:
                    try:
                        File_Group.update({
                            File_Group.parent_id: manager_root_id,
                            File_Group.tenant_id: manager_user_id,
                            File_Group.created_by: manager_user_id,
                            File_Group.name: "组参考库+文献库",
                        }).where(
                            File_Group.id == ref_root_id
                        ).execute()
                        print(f"参考库根节点更新 File_Group 成功: {ref_root_id}")
                    except Exception as e:
                        print(f"参考库根节点更新 File_Group 失败: {ref_root_id}, error={e}")

            # 2. 参考库下面所有文件写入 File_Group
            # 这里保留你的条件：File.tenant_id == group_public_id
            ref_files = File.select().where(
                (File.id != File.parent_id)
                & (File.tenant_id == group_public_id)
            )

            print(f"参考库文件写入 File_Group 数量: {ref_files.count()}")

            for item in ref_files:
                data = item.to_dict()
                file_id = data.get("id")

                if not file_id:
                    continue

                exists_file = File_Group.select().where(
                    File_Group.id == file_id
                ).first()

                if exists_file:
                    continue

                try:
                    File_Group.create(**data)
                    print(f"参考库文件写入 File_Group 成功: {file_id}")
                except Exception as e:
                    print(f"参考库文件写入 File_Group 失败: {file_id}, error={e}")

        # =====================================================
        # 第一步：无论拉入的是普通成员还是二级管理员，
        # 都先写入一级表 File_Admin，并同步其文件
        # =====================================================
        mount_member_to_file_admin(user_id)

        # 如果当前组配置了参考库，也挂到一级表
        mount_reference_to_file_admin()

        # =====================================================
        # 第二步：处理二级表 File_Group
        # =====================================================

        # -----------------------------------------------------
        # 情况一：当前拉入的是二级管理员
        # -----------------------------------------------------
        if is_new_user_manager:
            manager_user_id = user_id
            manager_root_id = user_root_id

            # 确保二级管理员自己的根目录存在于 File_Group
            ensure_manager_root_in_file_group(
                manager_user_id=manager_user_id,
                manager_root_id=manager_root_id
            )

            # 把参考库挂到二级管理员下面
            mount_reference_to_group_manager(
                manager_user_id=manager_user_id,
                manager_root_id=manager_root_id
            )

            # 把当前组已有普通成员挂到这个二级管理员下面
            group_members = UserGroup.select().where(
                UserGroup.group_id == group_id
            )

            for member_group in group_members:
                member_user_id = member_group.user_id

                # 跳过二级管理员自己
                if member_user_id == manager_user_id:
                    continue

                # 跳过其他二级管理员
                if AdminUser.query(user_id=member_user_id, role_level=2):
                    continue

                mount_member_to_group_manager(
                    member_user_id=member_user_id,
                    manager_user_id=manager_user_id,
                    manager_root_id=manager_root_id
                )

        # -----------------------------------------------------
        # 情况二：当前拉入的是普通成员
        # -----------------------------------------------------
        else:
            # 获取当前组第一个二级管理员
            group_manager = (
                AdminUser
                .select()
                .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))
                .where(
                    (UserGroup.group_id == group_id)
                    & (AdminUser.role_level == 2)
                )
                .first()
            )

            if not group_manager:
                raise Exception("请先拉一个组管理员入组")

            manager_user_id = group_manager.user_id

            # 获取二级管理员根目录
            manager_root = FileService.model.select().where(
                (FileService.model.tenant_id == manager_user_id)
                & (FileService.model.parent_id == FileService.model.id)
            ).first()

            if not manager_root:
                raise Exception(f"二级管理员 {manager_user_id} 没有根目录")

            manager_root_id = manager_root.id

            # 确保二级管理员自己的根目录存在于 File_Group
            ensure_manager_root_in_file_group(
                manager_user_id=manager_user_id,
                manager_root_id=manager_root_id
            )

            # 把当前普通成员挂到二级管理员下面，并同步成员文件
            mount_member_to_group_manager(
                member_user_id=user_id,
                manager_user_id=manager_user_id,
                manager_root_id=manager_root_id
            )

            # 确保参考库也挂到二级管理员下面
            mount_reference_to_group_manager(
                manager_user_id=manager_user_id,
                manager_root_id=manager_root_id
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
