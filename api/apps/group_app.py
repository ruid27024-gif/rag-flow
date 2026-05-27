from quart import request
from api.db.db_models import AdminUser, User, UserGroup
from api.db.services.group_service import GroupService
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
from peewee import JOIN

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

@manager.route('/my_group', methods=['GET'])
@login_required
async def get_my_group():
    try:
        error_response = check_group_admin(current_user)
        if error_response:
            return error_response

        user_group = UserGroup.select().where(UserGroup.user_id == current_user.id).first()
        if not user_group:
            return get_json_result(data=None)

        group = GroupService.get_or_none(group_id=user_group.group_id)
        if not group:
            return get_json_result(data=None)

        # Calculate member count
        member_count = UserGroup.select().where(UserGroup.group_id == group.group_id).count()

        data = {
            "id": group.group_id,
            "group_name": group.group_name,
            "created_by": group.created_by,
            "create_time": group.created_time,
            "member_count": member_count
        }
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)

# 二级管理员建组
@manager.route('/my_group/create', methods=['POST'])
@login_required
@validate_request("group_name")
async def create_my_group():
    req = await get_request_json()
    group_name = req['group_name']
    try:
        error_response = check_group_admin(current_user)
        if error_response:
            return error_response

        # Check if user is already in a group
        if UserGroup.select().where(UserGroup.user_id == current_user.id).exists():
             return get_json_result(
                code=RetCode.DATA_ERROR,
                message="You are already in a group."
            )

        group = GroupService.save(group_name=group_name, created_by=current_user.id)
        
        # Add current user to the group
        from api.db.services.user_group_service import UserGroupService
        from api.db.services.file_service import FileService
        UserGroupService.save(
            user_id=current_user.id,
            group_id=group.group_id,
            created_by=current_user.id,
        )

        # 获取1级管理员id
        admin = AdminUser.select().where(AdminUser.role_level  == 1).first()
        admin_id = admin.user_id

        # 获取1级别管理员的根
        root_folder = FileService.get_root_folder(admin_id)
        root_id = root_folder["id"]


        # 把组id挂载到根id上
        file = FileAdminService.insert({
            "id": group.group_id,
            "parent_id": root_id,
            "tenant_id": admin_id,  # 虚拟到1级管理员
            "created_by": admin_id,
            "name": group_name,
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value
        })

        # 2. 把自己挂到组id上
        root_folder = FileService.get_root_folder(tenant_id=current_user.id)
        pf_id = root_folder["id"]
        user = UserService.filter_by_id(current_user.id)

        file = FileAdminService.insert({
            "id": pf_id,
            "parent_id": group.group_id,
            "tenant_id": admin_id,  # 虚拟到1级管理员
            "created_by": admin_id,
            "name": user.nickname,
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value
        })

        # 3. 把自己挂到二级表
        file = FileGroupService.insert({
            "id": pf_id,
            "parent_id": pf_id,
            "tenant_id": current_user.id,  # 组管理员id
            "created_by": current_user.id,
            "name": "/",
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value
        })
        from api.db.db_models import File, File_Group,File_Admin

        # 当前人员的非根文件
        file_person_root_fei = File.select().where((File.id != File.parent_id)
                                                & (File.tenant_id == current_user.id)
                                                )
        # 1级表中是否已经存在
        file_person_admin = File_Admin.select().where((File_Admin.parent_id == pf_id)
                                                & (File_Admin.tenant_id == current_user.id)
                                                )
        
        # 如果之前1级表中不存在就写入建组人员的非根文件
        if not file_person_admin.exists():
        # 将文件全部写入到全局参考库下
            for i in file_person_root_fei:
                i.to_dict()

                try:
                    File_Admin.create(**i.to_dict())
                except:
                    pass


        return get_json_result(data={"group_id": group.group_id})
    except Exception as e:
        return server_error_response(e)


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
            
        group = GroupService.save(group_name=group_name, created_by=current_user.id)


        # 建组的时候把 组id挂载到自己的根上
        root_folder = FileService.get_root_folder(current_user.id)
        root_id = root_folder["id"]

        # 组挂到自己的根上
        file = FileAdminService.insert({
            "id": group.group_id,
            "parent_id": root_id,
            "tenant_id": current_user.id,
            "created_by": current_user.id,
            "name": group_name,
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value
        })

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
        dept_priority = {
            "新品事业部研发部": 0,
            "工艺研究一室": 1,
            "工艺研究二室": 2,
            "工艺研究三室": 3
        }
        groups = sorted(groups, key=lambda g: dept_priority.get(g.group_name, 99))

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
    
@manager.route('/list_ref_kbs', methods=['POST'])
@login_required
async def list_ref_kbs():
    try:
        req = await get_request_json()
        # 如果是超级管理员
        if AdminUser.query(user_id=current_user.id, role_level=1):
            cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}

            tenant_ids = list(cfg_map.values()) 
            tenant_ids.append(settings.REFERENCE_TENANT_ID)

            kbs = (KnowledgebaseService.model
                    .select(
                        KnowledgebaseService.model,  # 1. 先声明要查主表的所有字段
                        User.nickname,               # 2. 再带上关联表的字段
                        User.email
                    )
                    .join(
                        User, 
                        JOIN.LEFT_OUTER,             # 建议用左连接，防止找不到对应用户时数据丢失
                        on=(KnowledgebaseService.model.tenant_id == User.id)
                    )
                    .switch(KnowledgebaseService.model) 
                    .where(KnowledgebaseService.model.tenant_id.in_(tenant_ids))
                    .order_by(fn.FIELD(KnowledgebaseService.model.tenant_id, *tenant_ids))
                    .dicts()
                )
            
            kb_list = list(kbs)
            return get_json_result(data=kb_list)


        # 获取当前二级用户id
        admin_id = req.get("user_id")
        
        # 1. 获取当前用户所在的组（假设 get_ids_by_created_by 返回的是列表）
        group_ids = GroupService.get_ids_by_created_by(admin_id)

        # 如果通过创建者没找到组，则降级查询该用户所属的组
        if not group_ids:
            user_groups = UserGroup.select(UserGroup.group_id).where(
                UserGroup.user_id == admin_id
            ).dicts()
            # 提取 group_id 组成列表
            group_ids = [ug['group_id'] for ug in user_groups]



        if not group_ids:
            return get_json_result(data=[]) # 没找到组直接返回空

        # 2. 获取组对应的公共租户ID配置
        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        group_id = group_ids[0]
        
        # 校验组ID是否在配置中，并获取对应的公共租户ID
        if group_id not in cfg_map or not cfg_map[group_id]:
            return get_json_result(data=[])# 没配置公共租户，返回空
            
        group_public_tenant_id = cfg_map[group_id]

        kbs = (KnowledgebaseService.model
                .select(
                    KnowledgebaseService.model,  # 1. 先声明要查主表的所有字段
                    User.nickname,               # 2. 再带上关联表的字段
                    User.email
                )
                .join(
                    User, 
                    JOIN.LEFT_OUTER,             
                    on=(KnowledgebaseService.model.tenant_id == User.id)
                )
                .switch(KnowledgebaseService.model)  
                .where(KnowledgebaseService.model.tenant_id == group_public_tenant_id)
                .dicts()
            )

        kb_list = list(kbs)
        print(kb_list[0])
        return get_json_result(data=kb_list)

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
        

        GroupService.model.delete().where(GroupService.model.group_id == group_id).execute()
        UserGroupService.remove_members_by_group_id(group_id)
        # 暂且断开1级别表的组号到"/"
        FileAdminService.delete_by_id(group_id)

        # 断开2级别表
        # 获取当前组的管理员
        # 1. 构建查询  群里没人可能查不到
        try:
            query = (AdminUser
                    .select()
                    .join(UserGroup, on=(AdminUser.user_id == UserGroup.user_id))  # 通过 user_id 进行连接
                    .where((UserGroup.group_id == group_id) & (AdminUser.role_level == 2)))  # 设置筛选条件

            # 2. 获取第一个结果
            group_user = query.first()
            group_user_id = group_user.user_id

            FileGroupService.delete_by_id(group_user_id)
        except:
            pass



        return get_json_result(data=True)
        
    except Exception as e:
        return server_error_response(e)
