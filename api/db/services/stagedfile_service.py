from datetime import datetime
from peewee import JOIN
from api.db.db_models import Knowledgebase,SyncPerson,User, Tenant,StagedFile,AdminUser,StagedFileTag,KnowledgeTagType,KnowledgeTagOption
from api.db.services.common_service import CommonService
from api.db.services.user_service import TenantService
from api.db.services.role_service import RoleService
from common import settings

class StagedFileService(CommonService):
    model = StagedFile

    @classmethod
    def get_cls_model_fields(cls):
        return [
            cls.model.id,
            cls.model.batch_id,
            cls.model.kb_id,
            cls.model.tenant_id,
            cls.model.user_id,
            cls.model.filename,
            cls.model.path,
            cls.model.size,
            cls.model.status,
            cls.model.doc_id,

            cls.model.approval_level_1,
            cls.model.approval_level_2,

            cls.model.created_at,
            cls.model.approved_at,
            cls.model.approved_by,
            cls.model.committed_at,
            cls.model.error_msg,
        ]

    @classmethod
    def datetime_format(cls, value):
        if not value:
            return None

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        return value

    @classmethod
    def is_admin(cls, current_user):
        """
        判断是否管理员。
        role_level = 1 认为是管理员。
        """

        is_admin_1 = AdminUser.query(
            user_id=current_user.id,
            role_level=1
        )

        if isinstance(is_admin_1, list):
            return len(is_admin_1) > 0

        if hasattr(is_admin_1, "exists"):
            return is_admin_1.exists()

        if hasattr(is_admin_1, "first"):
            return is_admin_1.first() is not None

        return bool(is_admin_1)

    @classmethod
    def build_user_map(cls, user_ids):
        """
        把 user_id 转成用户信息。

        只用于上传人展示。
        """

        user_ids = list(set([uid for uid in user_ids if uid]))

        if not user_ids:
            return {}

        users = (
            User
            .select(
                User.id,
                User.nickname,
                User.email,
                User.avatar
            )
            .where(User.id.in_(user_ids))
        )

        user_map = {}

        for user in users:
            user_map[user.id] = {
                "id": user.id,
                "nickname": user.nickname,
                "email": user.email,
                "avatar": user.avatar,
            }

        return user_map

    @classmethod
    def build_tags_map(cls, stage_ids):
        """
        构建暂存文件标签映射。

        支持多选标签：
        同一个 stage_id + type_code 下多个 option_code 会放进 options。
        """

        if not stage_ids:
            return {}

        tag_rows = (
            StagedFileTag
            .select(
                StagedFileTag.stage_id,
                StagedFileTag.type_code,
                StagedFileTag.option_code,

                KnowledgeTagType.type_name,
                KnowledgeTagType.multi_select,
                KnowledgeTagType.required,
                KnowledgeTagType.sort_order.alias("type_sort_order"),

                KnowledgeTagOption.option_name,
                KnowledgeTagOption.sort_order.alias("option_sort_order"),
            )
            .join(
                KnowledgeTagType,
                JOIN.LEFT_OUTER,
                on=(StagedFileTag.type_code == KnowledgeTagType.type_code)
            )
            .switch(StagedFileTag)
            .join(
                KnowledgeTagOption,
                JOIN.LEFT_OUTER,
                on=(
                    (StagedFileTag.type_code == KnowledgeTagOption.type_code) &
                    (StagedFileTag.option_code == KnowledgeTagOption.option_code)
                )
            )
            .where(StagedFileTag.stage_id.in_(stage_ids))
            .order_by(
                StagedFileTag.stage_id,
                KnowledgeTagType.sort_order,
                KnowledgeTagOption.sort_order
            )
            .dicts()
        )

        temp_map = {}

        for row in tag_rows:
            stage_id = row["stage_id"]
            type_code = row["type_code"]
            option_code = row["option_code"]

            if stage_id not in temp_map:
                temp_map[stage_id] = {}

            if type_code not in temp_map[stage_id]:
                temp_map[stage_id][type_code] = {
                    "type_code": type_code,
                    "type_name": row.get("type_name") or type_code,
                    "multi_select": row.get("multi_select"),
                    "required": row.get("required"),
                    "options": [],
                    "option_names": [],
                }

            option_name = row.get("option_name") or option_code

            temp_map[stage_id][type_code]["options"].append({
                "option_code": option_code,
                "option_name": option_name,
            })

            temp_map[stage_id][type_code]["option_names"].append(option_name)

        tag_map = {}

        for stage_id, type_dict in temp_map.items():
            tag_map[stage_id] = list(type_dict.values())

        return tag_map

    @classmethod
    def serialize(cls, staged_file, tags=None, user_map=None):
        """
        StagedFile 转 dict。

        只转换上传人名称：
            user_id -> user_name

        审批人 approved_by 不转换。
        """

        user_map = user_map or {}

        uploader = user_map.get(staged_file.user_id)

        return {
            "id": staged_file.id,
            "batch_id": staged_file.batch_id,
            "kb_id": staged_file.kb_id,
            "tenant_id": staged_file.tenant_id,

            "user_id": staged_file.user_id,
            "user_name": uploader["nickname"] if uploader else staged_file.user_id,
            "user_email": uploader["email"] if uploader else None,
            "user_avatar": uploader["avatar"] if uploader else None,

            "filename": staged_file.filename,
            "path": staged_file.path,
            "size": staged_file.size,

            "status": staged_file.status,
            "doc_id": staged_file.doc_id,

            "created_at": cls.datetime_format(staged_file.created_at),

            "approved_at": cls.datetime_format(staged_file.approved_at),
            "approved_by": staged_file.approved_by,

            "committed_at": cls.datetime_format(staged_file.committed_at),
            "error_msg": staged_file.error_msg,
            "approval_level_1": staged_file.approval_level_1 or [],
            "approval_level_2": staged_file.approval_level_2 or [],

            "tags": tags or [],
        }

    # 根据知识库 kb_id 获取知识库所属部门。
    @classmethod
    def get_department_by_kb_id(cls, kb_id):
        """
        根据知识库 kb_id 获取知识库所属部门。

        逻辑：
        1. 查知识库 tenant_id
        2. 如果 tenant_id 是部门参考库虚拟 tenant_id：
                从 DEPARTMENT_REFERENCE_TENANT_MAP 反查 department_id
        3. 如果不是参考库：
                tenant_id 当作用户 id
                User.email == SyncPerson.phone
                SyncPerson.organizationCode 是部门 id
        """

        kb = Knowledgebase.get_or_none(Knowledgebase.id == kb_id)

        if not kb:
            return None

        tenant_id = kb.tenant_id

        cfg_map = getattr(settings, "DEPARTMENT_REFERENCE_TENANT_MAP", None)

        if cfg_map is None:
            cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}

        # 原配置：
        # {
        #   "部门ID": "部门参考库虚拟tenant_id"
        # }
        #
        # 反转后：
        # {
        #   "部门参考库虚拟tenant_id": "部门ID"
        # }
        reversed_map = {
            str(v): str(k)
            for k, v in cfg_map.items()
        }
        reference_tenant_id = getattr(settings, "REFERENCE_TENANT_ID", None)

        if reference_tenant_id and str(tenant_id) == str(reference_tenant_id):
            company_department_id = "100010"

            return {
                "kb_id": kb_id,
                "tenant_id": tenant_id,
                "is_reference_kb": True,
                "is_global_reference_kb": True,
                "department_id": company_department_id,
                "department_name": "公司",
            }
        # 1. 部门参考库
        if str(tenant_id) in reversed_map:
            department_id = reversed_map[str(tenant_id)]

            person = (
                SyncPerson
                .select(
                    SyncPerson.organizationCode,
                    SyncPerson.organize,
                )
                .where(SyncPerson.organizationCode == department_id)
                .first()
            )

            return {
                "kb_id": kb_id,
                "tenant_id": tenant_id,
                "is_reference_kb": True,
                "department_id": department_id,
                "department_name": person.organize if person else None,
            }

        # 2. 普通用户知识库：tenant_id 就是 User.id
        owner = User.get_or_none(User.id == tenant_id)

        if not owner:
            return {
                "kb_id": kb_id,
                "tenant_id": tenant_id,
                "is_reference_kb": False,
                "owner_user_id": None,
                "owner_email": None,
                "department_id": None,
                "department_name": None,
            }

        # 你前面已有逻辑：User.email == SyncPerson.phone
        person = SyncPerson.get_or_none(SyncPerson.phone == owner.email)

        if not person:
            return {
                "kb_id": kb_id,
                "tenant_id": tenant_id,
                "is_reference_kb": False,
                "owner_user_id": owner.id,
                "owner_email": owner.email,
                "department_id": None,
                "department_name": None,
            }

        return {
            "kb_id": kb_id,
            "tenant_id": tenant_id,
            "is_reference_kb": False,
            "owner_user_id": owner.id,
            "owner_email": owner.email,
            "department_id": person.organizationCode,
            "department_name": person.organize,
        }
    
    # @classmethod
    # def get_kb_approvers(cls, kb_id):
    #     """
    #     根据知识库获取审批人员。

    #     规则：
    #     1. 全局参考库、部门参考库：
    #     只根据部门配置查询审批角色，不额外添加知识库所属人。

    #     2. 普通知识库：
    #     tenant_id 是知识库所属用户的 user_id。
    #     如果该用户不在一级或二级审批人员中，则自动加入一级审批人员。
    #     """

    #     dept_info = cls.get_department_by_kb_id(kb_id)

    #     if not dept_info:
    #         return {
    #             "department": None,
    #             "level_1": [],
    #             "level_2": [],
    #         }

    #     # 获取部门id
    #     department_id = dept_info.get("department_id")
        
    #     if not department_id:
    #         return {
    #             "department": {
    #                 "department_id": None,
    #                 "department_name": dept_info.get("department_name"),
    #                 "is_reference_kb": dept_info.get("is_reference_kb", False),
    #                 "is_global_reference_kb": dept_info.get(
    #                     "is_global_reference_kb",
    #                     False,
    #                 ),
    #                 "tenant_id": dept_info.get("tenant_id"),
    #             },
    #             "level_1": [],
    #             "level_2": [],
    #         }

    #     # 根据部门获取配置的一级、二级审批人员。
    #     approval_users = RoleService.get_approval_users_by_department(
    #         department_id
    #     )

    #     level_1 = list(approval_users.get("level_1", []))
    #     level_2 = list(approval_users.get("level_2", []))

    #     is_reference_kb = dept_info.get("is_reference_kb", False)

    #     # 参考库不追加 tenant_id 对应的人员。
    #     # 普通知识库才需要判断所属用户是否已经在审批人中。
    #     if not is_reference_kb:
    #         owner_user_id = dept_info.get("owner_user_id")

    #         # 兼容 get_department_by_kb_id 没有返回 owner_user_id 的情况。
    #         if not owner_user_id:
    #             owner_user_id = dept_info.get("tenant_id")

    #         if owner_user_id:
    #             approver_user_ids = {
    #                 item.get("user_id")
    #                 for item in level_1 + level_2
    #                 if item.get("user_id")
    #             }

    #             # 所属用户不在一级、二级审批人员中时，
    #             # 自动加入一级审批人员。
    #             if owner_user_id not in approver_user_ids:
    #                 owner = User.get_or_none(User.id == owner_user_id)

    #                 if owner:
    #                     owner_email = owner.email

    #                     sync_person = (
    #                         SyncPerson
    #                         .select(
    #                             SyncPerson.phone,
    #                             SyncPerson.mdmCode,
    #                             SyncPerson.mdmName,
    #                             SyncPerson.organizationCode,
    #                             SyncPerson.organize,
    #                         )
    #                         .where(SyncPerson.phone == owner_email)
    #                         .first()
    #                     )

    #                     level_1.insert(0, {
    #                         "user_id": owner.id,
    #                         "user_name": owner.nickname or owner.id,
    #                         "email": owner.email,
    #                         "avatar": owner.avatar,

    #                         "mdm_code": sync_person.mdmCode
    #                         if sync_person else None,
    #                         "mdm_name": sync_person.mdmName
    #                         if sync_person else None,
    #                         "department_id": sync_person.organizationCode
    #                         if sync_person else None,
    #                         "department_name": sync_person.organize
    #                         if sync_person else None,

    #                         "role_id": None,
    #                         "role_name": "知识库所属人",
    #                         "approval_order": 1,
    #                     })

    #     return {
    #         "department": {
    #             "department_id": department_id,
    #             "department_name": dept_info.get("department_name"),
    #             "is_reference_kb": is_reference_kb,
    #             "is_global_reference_kb": dept_info.get(
    #                 "is_global_reference_kb",
    #                 False,
    #             ),
    #             "tenant_id": dept_info.get("tenant_id"),
    #         },
    #         "level_1": level_1,
    #         "level_2": level_2,
    #     }

    @classmethod
    def get_kb_approvers(cls, kb_id):
        """
        根据知识库获取审批人员。

        规则：
        1. 全局参考库、部门参考库：
        只根据部门配置查询审批角色，不额外添加知识库所属人。

        2. 普通知识库：
        tenant_id 是知识库所属用户的 user_id。
        如果该用户不在审批人员中，则自动加入审批人员。

        3. 不再区分一级、二级审批。
        只要具备审批权限，就是审批人。
        """

        dept_info = cls.get_department_by_kb_id(kb_id)

        if not dept_info:
            return {
                "department": None,
                "approvers": [],
            }

        # 获取部门 id
        department_id = dept_info.get("department_id")

        if not department_id:
            return {
                "department": {
                    "department_id": None,
                    "department_name": dept_info.get("department_name"),
                    "is_reference_kb": dept_info.get("is_reference_kb", False),
                    "is_global_reference_kb": dept_info.get(
                        "is_global_reference_kb",
                        False,
                    ),
                    "tenant_id": dept_info.get("tenant_id"),
                },
                "approvers": [],
            }

        # 根据部门获取配置的审批人员。
        approval_users = RoleService.get_approval_users_by_department(
            department_id
        )

        approvers = list(approval_users.get("approvers", []))

        is_reference_kb = dept_info.get("is_reference_kb", False)

        # 参考库不追加 tenant_id 对应的人员。
        # 普通知识库才需要判断所属用户是否已经在审批人中。
        if not is_reference_kb:
            owner_user_id = dept_info.get("owner_user_id")

            # 兼容 get_department_by_kb_id 没有返回 owner_user_id 的情况。
            if not owner_user_id:
                owner_user_id = dept_info.get("tenant_id")

            if owner_user_id:
                approver_user_ids = {
                    str(item.get("user_id"))
                    for item in approvers
                    if item.get("user_id")
                }

                # 所属用户不在审批人员中时，自动加入审批人员。
                if str(owner_user_id) not in approver_user_ids:
                    owner = User.get_or_none(User.id == owner_user_id)

                    if owner:
                        owner_email = owner.email

                        sync_person = (
                            SyncPerson
                            .select(
                                SyncPerson.phone,
                                SyncPerson.mdmCode,
                                SyncPerson.mdmName,
                                SyncPerson.organizationCode,
                                SyncPerson.organize,
                            )
                            .where(SyncPerson.phone == owner_email)
                            .first()
                        )

                        approvers.insert(0, {
                            "user_id": owner.id,
                            "user_name": owner.nickname or owner.id,
                            "email": owner.email,
                            "avatar": owner.avatar,

                            "mdm_code": sync_person.mdmCode
                            if sync_person else None,
                            "mdm_name": sync_person.mdmName
                            if sync_person else None,
                            "department_id": sync_person.organizationCode
                            if sync_person else None,
                            "department_name": sync_person.organize
                            if sync_person else None,

                            "role_id": None,
                            "role_name": "知识库所属人",
                        })

        return {
            "department": {
                "department_id": department_id,
                "department_name": dept_info.get("department_name"),
                "is_reference_kb": is_reference_kb,
                "is_global_reference_kb": dept_info.get(
                    "is_global_reference_kb",
                    False,
                ),
                "tenant_id": dept_info.get("tenant_id"),
            },
            "approvers": approvers,
        }


    @classmethod
    def list_by_kb(
        cls,
        kb_id,
        tenant_id,
        current_user,
        status=None,
        page=1,
        page_size=20,
        include_deleted=False,
    ):
        """
        根据知识库查询暂存文件列表。

        管理员：
            看知识库下所有文件。

        普通用户：
            只能看自己上传的文件。

        同时返回该知识库所属部门的审批人员。
        """

        is_admin = cls.is_admin(current_user)

        conditions = [
            cls.model.kb_id == kb_id,
            # 如果你的 staged_file.tenant_id 数据完整，建议打开
            # cls.model.tenant_id == tenant_id,
        ]

        if not include_deleted:
            conditions.append(cls.model.status != "deleted")

        if status:
            conditions.append(cls.model.status == status)

        if not is_admin:
            conditions.append(cls.model.user_id == current_user.id)

        base_query = (
            cls.model
            .select(*cls.get_cls_model_fields())
            .where(*conditions)
        )

        total = base_query.count()

        staged_files = list(
            base_query
            .order_by(cls.model.created_at.desc())
            .paginate(page, page_size)
        )

        stage_ids = [item.id for item in staged_files]

        tag_map = cls.build_tags_map(stage_ids)

        user_ids = [item.user_id for item in staged_files if item.user_id]

        user_map = cls.build_user_map(user_ids)

        items = []

        for item in staged_files:
            items.append(
                cls.serialize(
                    item,
                    tags=tag_map.get(item.id, []),
                    user_map=user_map
                )
            )

        approvers = cls.get_kb_approvers(kb_id)

        return {
            "is_admin": is_admin,
            "total": total,
            "page": page,
            "page_size": page_size,
            "approvers": approvers,
            "items": items,
        }


    @classmethod
    def get_upload_approvers(cls, kb_id, uploader_user_id):
        """
        获取本次上传实际需要的审批人员。

        规则：
        1. 上传人属于二级审批人：
        - 跳过全部一级审批人
        - 从二级审批人中移除上传人自己

        2. 上传人属于一级审批人：
        - 从一级审批人中移除上传人自己
        - 二级审批人保持不变

        3. 上传人不属于审批人：
        - 保持知识库原有审批链。
        """
        # # 获取到所有审批人员
        # approver_config = cls.get_kb_approvers(kb_id)

        # level_1 = list(approver_config.get("level_1", []))
        # level_2 = list(approver_config.get("level_2", []))

        # uploader_user_id = str(uploader_user_id)

        # level_1_user_ids = {
        #     str(item.get("user_id"))
        #     for item in level_1
        #     if item.get("user_id")
        # }

        # level_2_user_ids = {
        #     str(item.get("user_id"))
        #     for item in level_2
        #     if item.get("user_id")
        # }

        # # 上传人是二级审批人：
        # # 跳过全部一级审批，二级也不需要自己审批自己。
        # if uploader_user_id in level_2_user_ids:
        #     level_1 = []
        #     level_2 = [
        #         item
        #         for item in level_2
        #         if str(item.get("user_id")) != uploader_user_id
        #     ]

        # # 上传人只是一级审批人：
        # # 一级不需要自己审批，保留二级审批。
        # elif uploader_user_id in level_1_user_ids:
        #     level_1 = [
        #         item
        #         for item in level_1
        #         if str(item.get("user_id")) != uploader_user_id
        #     ]

        # return {
        #     "department": approver_config.get("department"),
        #     "level_1": level_1,
        #     "level_2": level_2,
        # }

        approver_config = cls.get_kb_approvers(kb_id)

        approvers = list(approver_config.get("approvers", []))
        uploader_user_id = str(uploader_user_id)

        uploader_is_approver = any(
            str(item.get("user_id")) == uploader_user_id
            for item in approvers
        )

        if uploader_is_approver:
            approvers = []

        return {
            "department": approver_config.get("department"),
            "level_1": approvers,
            "level_2": [],
            "uploader_is_approver": uploader_is_approver,
        }

    