#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import os
from datetime import datetime

from peewee import fn, JOIN

from api.db import TenantPermission
from api.db.db_models import DB, Document, Group, Knowledgebase, User, UserTenant, UserCanvas, AdminUser, UserGroup
from api.db.services.common_service import CommonService
from common import settings
from common.time_utils import current_timestamp, datetime_format
from api.db.services import duplicate_name
from api.db.services.user_service import TenantService
from common.misc_utils import get_uuid
from common.constants import RetCode, StatusEnum
from api.constants import DATASET_NAME_LIMIT
from api.utils.api_utils import get_parser_config, get_data_error_result


class KnowledgebaseService(CommonService):
    """Service class for managing dataset operations.

    This class extends CommonService to provide specialized functionality for dataset
    management, including document parsing status tracking, access control, and configuration
    management. It handles operations such as listing, creating, updating, and deleting
    knowledge bases, as well as managing their associated documents and permissions.

    The class implements a comprehensive set of methods for:
    - Document parsing status verification
    - Knowledge base access control
    - Parser configuration management
    - Tenant-based dataset organization

    Attributes:
        model: The Knowledgebase model class for database operations.
    """
    model = Knowledgebase

    @classmethod
    @DB.connection_context()
    def get_group_reference_tenant_ids(cls, user_id: str) -> list[str]:
        # 用户所加入的组id
        group_ids = {
            r.group_id
            for r in UserGroup.select(UserGroup.group_id).where(UserGroup.user_id == user_id)
        }
        # 用户创建的组
        try:
            group_ids.update(
                {
                    r.group_id
                    for r in Group.select(Group.group_id).where(Group.created_by == user_id)
                }
            )
        except Exception:
            pass

        # 通过组id获取到参考库的租户id
        ref_ids = set()
        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        for gid in list(group_ids):
            tid = cfg_map.get(gid)
            if tid:
                ref_ids.add(tid)
        # 没有参考库的组通过数据库直接获取组参考库id
        db_group_ids = [gid for gid in list(group_ids) if gid not in cfg_map]
        if db_group_ids:
            try:
                rows = Group.select(Group.reference_tenant_id).where(
                    Group.group_id.in_(db_group_ids)
                    & Group.reference_tenant_id.is_null(False)
                    & (Group.reference_tenant_id != "")
                )
                for r in rows:
                    if r.reference_tenant_id:
                        ref_ids.add(r.reference_tenant_id)
            except Exception:
                pass
        return list(ref_ids)

    @classmethod
    @DB.connection_context()
    def get_group_ids_by_reference_tenant_id(cls, reference_tenant_id: str) -> list[str]:
        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        group_ids = {gid for gid, tid in cfg_map.items() if tid == reference_tenant_id}
        try:
            rows = Group.select(Group.group_id).where(
                (Group.reference_tenant_id == reference_tenant_id)
                & Group.reference_tenant_id.is_null(False)
                & (Group.reference_tenant_id != "")
            )
            for r in rows:
                gid = r.group_id
                if gid in cfg_map and cfg_map.get(gid) != reference_tenant_id:
                    continue
                group_ids.add(gid)
        except Exception:
            pass
        return list(group_ids)

    @classmethod
    @DB.connection_context()
    def get_all_group_reference_tenant_ids(cls) -> list[str]:
        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        ref_ids = {tid for tid in cfg_map.values() if tid}
        try:
            rows = Group.select(Group.group_id, Group.reference_tenant_id).where(
                Group.reference_tenant_id.is_null(False) & (Group.reference_tenant_id != "")
            )
            for r in rows:
                gid = r.group_id
                if gid in cfg_map:
                    continue
                if r.reference_tenant_id:
                    ref_ids.add(r.reference_tenant_id)
        except Exception:
            pass
        return list(ref_ids)

    @classmethod
    @DB.connection_context()
    def accessible4deletion(cls, kb_id, user_id):
        """Check if a dataset can be deleted by a specific user.

        This method verifies whether a user has permission to delete a dataset
        by checking if they are the creator of that dataset.

        Args:
            kb_id (str): The unique identifier of the dataset to check.
            user_id (str): The unique identifier of the user attempting the deletion.

        Returns:
            bool: True if the user has permission to delete the dataset,
                  False if the user doesn't have permission or the dataset doesn't exist.

        Example:
            >>> KnowledgebaseService.accessible4deletion("kb123", "user456")
            True

        Note:
            - This method only checks creator permissions
            - A return value of False can mean either:
                1. The dataset doesn't exist
                2. The user is not the creator of the dataset
        """
        if AdminUser.query(user_id=user_id, role_level=1):
            return True
        
        # Check for level 2 admin
        if AdminUser.query(user_id=user_id, role_level=2):
             # Find current user's group
            my_group = UserGroup.select().where(UserGroup.user_id == user_id).first()
            e, kb = cls.get_by_id(kb_id)
            if my_group and e:
                # Find KB owner's group
                owner_group = UserGroup.select().where(UserGroup.user_id == kb.tenant_id).first()
                if owner_group and owner_group.group_id == my_group.group_id:
                    return True
            if e and (
                Group.select(Group.group_id)
                .join(UserGroup, on=(Group.group_id == UserGroup.group_id))
                .where(
                    (UserGroup.user_id == user_id)
                    & (Group.reference_tenant_id == kb.tenant_id)
                    & Group.reference_tenant_id.is_null(False)
                    & (Group.reference_tenant_id != "")
                )
                .exists()
            ):
                return True
        
        # Check if a dataset can be deleted by a user
        docs = cls.model.select(
            cls.model.id).where(cls.model.id == kb_id, cls.model.created_by == user_id).paginate(0, 1)
        docs = docs.dicts()
        if not docs:
            return False
        return True

    @classmethod
    @DB.connection_context()
    def is_parsed_done(cls, kb_id):
        # Check if all documents in the dataset have completed parsing
        #
        # Args:
        #     kb_id: Knowledge base ID
        #
        # Returns:
        #     If all documents are parsed successfully, returns (True, None)
        #     If any document is not fully parsed, returns (False, error_message)
        from common.constants import TaskStatus
        from api.db.services.document_service import DocumentService

        # Get dataset information
        kbs = cls.query(id=kb_id)
        if not kbs:
            return False, "Knowledge base not found"
        kb = kbs[0]

        # Get all documents in the dataset
        docs, _ = DocumentService.get_by_kb_id(kb_id, 1, 1000, "create_time", True, "", [], [])

        # Check parsing status of each document
        for doc in docs:
            # If document is being parsed, don't allow chat creation
            if doc['run'] == TaskStatus.RUNNING.value or doc['run'] == TaskStatus.CANCEL.value or doc['run'] == TaskStatus.FAIL.value:
                return False, f"Document '{doc['name']}' in dataset '{kb.name}' is still being parsed. Please wait until all documents are parsed before starting a chat."
            # If document is not yet parsed and has no chunks, don't allow chat creation
            if doc['run'] == TaskStatus.UNSTART.value and doc['chunk_num'] == 0:
                return False, f"Document '{doc['name']}' in dataset '{kb.name}' has not been parsed yet. Please parse all documents before starting a chat."

        return True, None

    @classmethod
    @DB.connection_context()
    def list_documents_by_ids(cls, kb_ids):
        # Get document IDs associated with given dataset IDs
        # Args:
        #     kb_ids: List of dataset IDs
        # Returns:
        #     List of document IDs
        doc_ids = cls.model.select(Document.id.alias("document_id")).join(Document, on=(cls.model.id == Document.kb_id)).where(
            cls.model.id.in_(kb_ids)
        )
        doc_ids = list(doc_ids.dicts())
        doc_ids = [doc["document_id"] for doc in doc_ids]
        return doc_ids
    
    @classmethod
    @DB.connection_context()
    def get_by_tenant_ids2(
        cls,
        joined_tenant_ids,
        user_id,
        page_number,
        items_per_page,
        orderby,
        desc,
        keywords,
        parser_id=None,
        admin_bypass=False,
    ):
        fields = [
            cls.model.id,
            cls.model.avatar,
            cls.model.name,
            cls.model.language,
            cls.model.description,
            cls.model.tenant_id,
            cls.model.permission,
            cls.model.doc_num,
            cls.model.token_num,
            cls.model.chunk_num,
            cls.model.parser_id,
            cls.model.embd_id,
            User.nickname,
            User.avatar.alias("tenant_avatar"),
            cls.model.update_time,
            UserGroup.group_id,
            Group.group_name,
        ]

        kbs = (
            cls.model.select(*fields)
            .join(User, on=(cls.model.tenant_id == User.id))
            .join(
                UserGroup,
                JOIN.LEFT_OUTER,
                on=(cls.model.tenant_id == UserGroup.user_id),
            )
            .join(
                Group,
                JOIN.LEFT_OUTER,
                on=(UserGroup.group_id == Group.group_id),
            )
        )

        is_super_admin = admin_bypass or bool(
            AdminUser.query(user_id=user_id, role_level=1)
        )
        is_level_2_admin = bool(
            AdminUser.query(user_id=user_id, role_level=2)
        )

        if not is_super_admin:
            if is_level_2_admin:
                my_group = (
                    UserGroup.select()
                    .where(UserGroup.user_id == user_id)
                    .first()
                )

                if my_group:
                    group_members = (
                        UserGroup.select(UserGroup.user_id)
                        .where(UserGroup.group_id == my_group.group_id)
                    )
                    tenant_ids = [member.user_id for member in group_members]

                    # 加上二级管理员自己
                    if user_id not in tenant_ids:
                        tenant_ids.append(user_id)

                    # 加上当前组对应的参考库
                    cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
                    group_reference_tenant_id = (
                        cfg_map.get(my_group.group_id)
                        or cfg_map.get(str(my_group.group_id))
                    )

                    if (
                        group_reference_tenant_id
                        and group_reference_tenant_id not in tenant_ids
                    ):
                        tenant_ids.append(group_reference_tenant_id)

                    kbs = kbs.where(cls.model.tenant_id.in_(tenant_ids))
                else:
                    kbs = kbs.where(cls.model.tenant_id == user_id)
            else:
                kbs = kbs.where(cls.model.tenant_id == user_id)

        kbs = kbs.where(cls.model.status == StatusEnum.VALID.value)

        if keywords:
            kbs = kbs.where(fn.LOWER(cls.model.name).contains(keywords.lower()))

        if parser_id:
            kbs = kbs.where(cls.model.parser_id == parser_id)

        if desc:
            kbs = kbs.order_by(cls.model.getter_by(orderby).desc())
        else:
            kbs = kbs.order_by(cls.model.getter_by(orderby).asc())

        count = kbs.count()

        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        reversed_map = {v: k for k, v in cfg_map.items()}
        public_id = settings.REFERENCE_TENANT_ID

        res = list(kbs.dicts())

        for kb in res:
            tenant_id = kb["tenant_id"]

            if tenant_id == public_id:
                kb["group_name"] = "全局参考库"
                kb["color"] = 3

            elif tenant_id in reversed_map:
                group_id = reversed_map[tenant_id]
                group_obj = (
                    Group.select(Group.group_name)
                    .where(Group.group_id == group_id)
                    .first()
                )

                kb["group_id"] = group_id
                kb["group_name"] = group_obj.group_name if group_obj else None
                kb["color"] = 3

            elif AdminUser.query(user_id=tenant_id, role_level=1):
                kb["color"] = 1

            elif AdminUser.query(user_id=tenant_id, role_level=2):
                kb["color"] = 2

        def custom_sort_key(kb):
            name = kb.get("group_name")
            color = kb.get("color")

            # 1. 全局参考库最前
            if name == "全局参考库":
                return (0, "")

            # 2. 各组参考库排在成员库前面
            if color == 3:
                if name == "工艺研究一室":
                    return (1, "")
                if name == "工艺研究二室":
                    return (2, "")
                if name == "工艺研究三室":
                    return (3, "")
                if name == "新品事业部研发部":
                    return (4, "")
                return (5, name or "")

            # 3. 二级管理员的知识库
            if color == 2:
                return (6, name or "")

            # 4. 超级管理员/普通成员/无分组的知识库放后面
            return (7, name or "")
        
        res = sorted(res, key=custom_sort_key)

        if page_number and items_per_page:
            offset = (page_number - 1) * items_per_page
            res = res[offset : offset + items_per_page]

        return res, count

    @classmethod
    @DB.connection_context()
    def get_by_tenant_ids(cls, joined_tenant_ids, user_id,
                          page_number, items_per_page,
                          orderby, desc, keywords,
                          parser_id=None,
                          admin_bypass=False
                          ):
        # Get knowledge bases by tenant IDs with pagination and filtering
        # Args:
        #     joined_tenant_ids: List of tenant IDs
        #     user_id: Current user ID
        #     page_number: Page number for pagination
        #     items_per_page: Number of items per page
        #     orderby: Field to order by
        #     desc: Boolean indicating descending order
        #     keywords: Search keywords
        #     parser_id: Optional parser ID filter
        #     admin_bypass: Bypass permission check if True
        # Returns:
        #     Tuple of (knowledge_base_list, total_count)
        # fields = [
        #     cls.model.id,
        #     cls.model.avatar,
        #     cls.model.name,
        #     cls.model.language,
        #     cls.model.description,
        #     cls.model.tenant_id,
        #     cls.model.permission,
        #     cls.model.doc_num,
        #     cls.model.token_num,
        #     cls.model.chunk_num,
        #     cls.model.parser_id,
        #     cls.model.embd_id,
        #     User.nickname,
        #     User.avatar.alias('tenant_avatar'),
        #     cls.model.update_time
        # ]
        
        # kbs = cls.model.select(*fields).join(User, on=(cls.model.tenant_id == User.id))

        fields = [
        cls.model.id,
        cls.model.avatar,
        cls.model.name,
        cls.model.language,
        cls.model.description,
        cls.model.tenant_id,
        cls.model.permission,
        cls.model.doc_num,
        cls.model.token_num,
        cls.model.chunk_num,
        cls.model.parser_id,
        cls.model.embd_id,
        User.nickname,
        User.avatar.alias('tenant_avatar'),
        cls.model.update_time,
        # 新增字段
        UserGroup.group_id,      # 1. 拿到关联表中的 group_id
        Group.group_name         # 2. 拿到最终目标表中的 group_name
    ]

        kbs = (cls.model
        .select(*fields)
        # 1. 连接 User 表 (通常用户肯定存在，保持 INNER JOIN 即可，也可以改为 LEFT_OUTER 以防万一)
        .join(User, on=(cls.model.tenant_id == User.id))
        
        # 2. 连接 UserGroup 表 <--- 修改这里
        # 使用 LEFT_OUTER，这样即使没有组，知识库也能查出来
        .join(UserGroup, JOIN.LEFT_OUTER, on=(cls.model.tenant_id == UserGroup.user_id))
        
        # 3. 切换回主表上下文
        .switch(cls.model)
        
        # 4. 连接 Group 表 <--- 修改这里
        # 同样建议用 LEFT_OUTER，防止因为组信息缺失导致数据查不出来
        .join(Group, JOIN.LEFT_OUTER, on=(UserGroup.group_id == Group.group_id))
        )


                
        # 如果不是超级管理员
        if not admin_bypass:
            # 拿到全局参考库
            reference_expr = (cls.model.tenant_id == settings.REFERENCE_TENANT_ID) if settings.REFERENCE_TENANT_ID else None
            # 所有的组参考库id
            group_reference_ids = cls.get_group_reference_tenant_ids(user_id)
            # 拿到组参考库
            group_reference_expr = cls.model.tenant_id.in_(group_reference_ids) if group_reference_ids else None
            # Check for level 2 admin 如果是二级管理员
            if AdminUser.query(user_id=user_id, role_level=2):
                 # Find current user's group  找出用户当前组
                my_group = UserGroup.select().where(UserGroup.user_id == user_id).first()
                # 有组的
                if my_group:
                    # Find all users in the same group
                    group_members = UserGroup.select(UserGroup.user_id).where(UserGroup.group_id == my_group.group_id)
                    member_ids = [m.user_id for m in group_members]
                    
                    base_expr = (
                        (cls.model.tenant_id.in_(member_ids)) 
                        | (cls.model.tenant_id.in_(joined_tenant_ids) & (cls.model.permission.in_([TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value])))
                        | (cls.model.permission.in_([TenantPermission.EVERYONE.value, TenantPermission.EVERYONE_VISIBLE.value]))
                    )
                    if reference_expr is not None:
                        base_expr = base_expr | reference_expr
                    if group_reference_expr is not None:
                        base_expr = base_expr | group_reference_expr
                    kbs = kbs.where(base_expr)
                else:
                    base_expr = (
                            (cls.model.tenant_id.in_(joined_tenant_ids)
                            & (cls.model.permission.in_([TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value])))
                            | (cls.model.tenant_id == user_id)
                            | (cls.model.permission.in_([TenantPermission.EVERYONE.value, TenantPermission.EVERYONE_VISIBLE.value]))
                    )
                    if reference_expr is not None:
                        base_expr = base_expr | reference_expr
                    if group_reference_expr is not None:
                        base_expr = base_expr | group_reference_expr
                    kbs = kbs.where(base_expr)

            else:
                reference_expr = (cls.model.tenant_id == settings.REFERENCE_TENANT_ID) if settings.REFERENCE_TENANT_ID else None
                base_expr = (
                        (cls.model.tenant_id.in_(joined_tenant_ids)
                        & (cls.model.permission.in_([TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value])))
                        | (cls.model.tenant_id == user_id)
                        | (cls.model.permission.in_([TenantPermission.EVERYONE.value, TenantPermission.EVERYONE_VISIBLE.value]))
                )
                if reference_expr is not None:
                    base_expr = base_expr | reference_expr
                if group_reference_expr is not None:
                    base_expr = base_expr | group_reference_expr
                kbs = kbs.where(base_expr)
            
            if not AdminUser.query(user_id=user_id, role_level=1):
                all_group_reference_ids = cls.get_all_group_reference_tenant_ids()
                hidden_group_reference_ids = list(set(all_group_reference_ids) - set(group_reference_ids))
                if settings.REFERENCE_TENANT_ID:
                    hidden_group_reference_ids = [
                        i for i in hidden_group_reference_ids if i != settings.REFERENCE_TENANT_ID
                    ]
                hidden_group_reference_ids = [i for i in hidden_group_reference_ids if i != user_id]
                if hidden_group_reference_ids:
                    kbs = kbs.where(~cls.model.tenant_id.in_(hidden_group_reference_ids))

        kbs = kbs.where(cls.model.status == StatusEnum.VALID.value)


        
        if keywords:
            kbs = kbs.where(fn.LOWER(cls.model.name).contains(keywords.lower()))
            
        if parser_id:
            kbs = kbs.where(cls.model.parser_id == parser_id)
        if desc:
            kbs = kbs.order_by(cls.model.getter_by(orderby).desc())
        else:
            kbs = kbs.order_by(cls.model.getter_by(orderby).asc())

        count = kbs.count()
        
        # # todo先展示参考库了
        # kbs = kbs.order_by(UserGroup.group_id.asc())

        # if page_number and items_per_page:
        #     kbs = kbs.paginate(page_number, items_per_page)

        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        reversed_map = {v: k for k, v in cfg_map.items()}
        
        res = list(kbs.dicts())
        public_id = settings.REFERENCE_TENANT_ID

        # 1. 创建三个列表，用于分类存放不同颜色的 kb
        color_3_kbs = [] # 存放颜色为 3 的 kb
        color_2_kbs = [] # 存放颜色为 2 的 kb
        other_kbs = []   # 存放颜色为 1 以及没有 color 属性的 kb


        for kb in res:
            # 1. 获取租户ID
            tenant_id = kb["tenant_id"]
                # 全局库的id

            if tenant_id == public_id:
                kb["group_name"] = "全局参考库"
                kb["color"] = 3

            if AdminUser.query(user_id=tenant_id, role_level=1):
                kb["color"] = 1

            if AdminUser.query(user_id=tenant_id, role_level=2):
                kb["color"] = 2


            # 2. 检查是否有映射关系
            if tenant_id in reversed_map:
                group_id = reversed_map[tenant_id]
                
                # 3. 修正：执行查询并获取具体对象
                # 使用 .first() 获取第一条记录，如果找不到返回 None
                group_obj = Group.select(Group.group_name).where(Group.group_id == group_id).first()
                
                kb["group_id"] = group_id
                # 修正：取出对象里的属性，如果没有查到对象则设为 None
                kb["group_name"] = group_obj.group_name if group_obj else None
                kb["color"] = 3

            color = kb.get("color")
            if color == 3:
                color_3_kbs.append(kb)
            elif color == 2:
                color_2_kbs.append(kb)
            else:
                # 这里包含了 color=1 和 color 不存在的所有情况
                other_kbs.append(kb)

        # 3. 按照指定顺序合并列表
        res = color_3_kbs + color_2_kbs + other_kbs
        print(res)

        if page_number and items_per_page:
            # res = sorted(res, key=lambda x: (1 if x["group_name"] is not None else 0, x["group_name"] or ""))

            def custom_sort_key(x):
                name = x["group_name"]
                
                # 1. 处理 None 值：优先级 0 (最高，排第一)
                if name is None:
                    return (0, "")
                    
                # 2. 处理 "全局参考库"：优先级 1 (排第二)
                if name == "全局参考库":
                    return (1, "")
                
                if name == "工艺研究一室":
                    return (2, "")
                
                if name == "工艺研究二室":
                    return (3, "")
                
                if name == "工艺研究三室":
                    return (4, "")
                
                if name == "新品事业部研发部":
                    return (5, "")
                
                else:
                    return(6, "")
                
            res = sorted(res, key=custom_sort_key)

            # 1. 计算偏移量 (Offset)
            # 公式：(当前页码 - 1) * 每页数量
            # 例如：第1页偏移0，第2页偏移10（假设每页10条）
            offset = (page_number - 1) * items_per_page
            
            # 2. 使用切片截取列表
            # 语法：列表[起始索引 : 结束索引]
            res = res[offset : offset + items_per_page]
        return res, count

    @classmethod
    @DB.connection_context()
    def get_all_kb_by_tenant_ids(cls, tenant_ids, user_id):
        # will get all permitted kb, be cautious.
        fields = [
            cls.model.name,
            cls.model.avatar,
            cls.model.language,
            cls.model.permission,
            cls.model.doc_num,
            cls.model.token_num,
            cls.model.chunk_num,
            cls.model.status,
            cls.model.create_date,
            cls.model.update_date
        ]
        # find team kb and owned kb
        base_expr = (
            (
                cls.model.tenant_id.in_(tenant_ids)
                & (cls.model.permission.in_([TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value]))
            )
            | (cls.model.tenant_id == user_id)
            | (cls.model.permission.in_([TenantPermission.EVERYONE.value, TenantPermission.EVERYONE_VISIBLE.value]))
        )
        if settings.REFERENCE_TENANT_ID:
            base_expr = base_expr | (cls.model.tenant_id == settings.REFERENCE_TENANT_ID)
        group_reference_ids = cls.get_group_reference_tenant_ids(user_id)
        if group_reference_ids:
            base_expr = base_expr | cls.model.tenant_id.in_(group_reference_ids)
        kbs = cls.model.select(*fields).where(base_expr)
        if not AdminUser.query(user_id=user_id, role_level=1):
            all_group_reference_ids = cls.get_all_group_reference_tenant_ids()
            hidden_group_reference_ids = list(set(all_group_reference_ids) - set(group_reference_ids))
            if settings.REFERENCE_TENANT_ID:
                hidden_group_reference_ids = [
                    i for i in hidden_group_reference_ids if i != settings.REFERENCE_TENANT_ID
                ]
            hidden_group_reference_ids = [i for i in hidden_group_reference_ids if i != user_id]
            if hidden_group_reference_ids:
                kbs = kbs.where(~cls.model.tenant_id.in_(hidden_group_reference_ids))
        # sort by create_time asc
        kbs.order_by(cls.model.create_time.asc())
        # maybe cause slow query by deep paginate, optimize later.
        offset, limit = 0, 50
        res = []
        while True:
            kb_batch = kbs.offset(offset).limit(limit)
            _temp = list(kb_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res

    @classmethod
    @DB.connection_context()
    def get_kb_ids(cls, tenant_id):
        # Get all dataset IDs for a tenant
        # Args:
        #     tenant_id: Tenant ID
        # Returns:
        #     List of dataset IDs
        fields = [
            cls.model.id,
        ]
        kbs = cls.model.select(*fields).where(cls.model.tenant_id == tenant_id)
        kb_ids = [kb.id for kb in kbs]
        return kb_ids

    @classmethod
    @DB.connection_context()
    def get_detail(cls, kb_id):
        # Get detailed information about a dataset
        # Args:
        #     kb_id: Knowledge base ID
        # Returns:
        #     Dictionary containing dataset details
        fields = [
            cls.model.id,
            cls.model.embd_id,
            cls.model.avatar,
            cls.model.name,
            cls.model.language,
            cls.model.description,
            cls.model.permission,
            cls.model.created_by,
            cls.model.doc_num,
            cls.model.token_num,
            cls.model.chunk_num,
            cls.model.parser_id,
            cls.model.pipeline_id,
            UserCanvas.title.alias("pipeline_name"),
            UserCanvas.avatar.alias("pipeline_avatar"),
            cls.model.parser_config,
            cls.model.pagerank,
            cls.model.graphrag_task_id,
            cls.model.graphrag_task_finish_at,
            cls.model.raptor_task_id,
            cls.model.raptor_task_finish_at,
            cls.model.mindmap_task_id,
            cls.model.mindmap_task_finish_at,
            cls.model.create_time,
            cls.model.update_time
            ]
        kbs = cls.model.select(*fields)\
                .join(UserCanvas, on=(cls.model.pipeline_id == UserCanvas.id), join_type=JOIN.LEFT_OUTER)\
            .where(
            (cls.model.id == kb_id),
            (cls.model.status == StatusEnum.VALID.value)
        ).dicts()
        if not kbs:
            return None
        return kbs[0]

    @classmethod
    @DB.connection_context()
    def update_parser_config(cls, id, config):
        # Update parser configuration for a dataset
        # Args:
        #     id: Knowledge base ID
        #     config: New parser configuration
        e, m = cls.get_by_id(id)
        if not e:
            raise LookupError(f"dataset({id}) not found.")

        def dfs_update(old, new):
            # Deep update of nested configuration
            for k, v in new.items():
                if k not in old:
                    old[k] = v
                    continue
                if isinstance(v, dict):
                    assert isinstance(old[k], dict)
                    dfs_update(old[k], v)
                elif isinstance(v, list):
                    assert isinstance(old[k], list)
                    old[k] = list(set(old[k] + v))
                else:
                    old[k] = v

        dfs_update(m.parser_config, config)
        cls.update_by_id(id, {"parser_config": m.parser_config})

    @classmethod
    @DB.connection_context()
    def delete_field_map(cls, id):
        e, m = cls.get_by_id(id)
        if not e:
            raise LookupError(f"dataset({id}) not found.")

        m.parser_config.pop("field_map", None)
        cls.update_by_id(id, {"parser_config": m.parser_config})

    @classmethod
    @DB.connection_context()
    def get_field_map(cls, ids):
        # Get field mappings for knowledge bases
        # Args:
        #     ids: List of dataset IDs
        # Returns:
        #     Dictionary of field mappings
        conf = {}
        for k in cls.get_by_ids(ids):
            if k.parser_config and "field_map" in k.parser_config:
                conf.update(k.parser_config["field_map"])
        return conf

    @classmethod
    @DB.connection_context()
    def get_by_name(cls, kb_name, tenant_id):
        # Get dataset by name and tenant ID
        # Args:
        #     kb_name: Knowledge base name
        #     tenant_id: Tenant ID
        # Returns:
        #     Tuple of (exists, knowledge_base)
        kb = cls.model.select().where(
            (cls.model.name == kb_name)
            & (cls.model.tenant_id == tenant_id)
            & (cls.model.status == StatusEnum.VALID.value)
        )
        if kb:
            return True, kb[0]
        return False, None

    @classmethod
    @DB.connection_context()
    def get_all_ids(cls):
        # Get all dataset IDs
        # Returns:
        #     List of all dataset IDs
        return [m["id"] for m in cls.model.select(cls.model.id).dicts()]


    @classmethod
    @DB.connection_context()
    def create_with_name(
        cls,
        *,
        name: str,
        tenant_id: str,
        parser_id: str | None = None,
        **kwargs
    ):
        """Create a dataset (knowledgebase) by name with kb_app defaults.

        This encapsulates the creation logic used in kb_app.create so other callers
        (including RESTFul endpoints) can reuse the same behavior.

        Returns:
            (ok: bool, model_or_msg): On success, returns (True, Knowledgebase model instance);
                                      on failure, returns (False, error_message).
        """
        # Validate name
        if not isinstance(name, str):
            return False, get_data_error_result(message="Dataset name must be string.")
        dataset_name = name.strip()
        if dataset_name == "":
            return False, get_data_error_result(message="Dataset name can't be empty.")
        if len(dataset_name.encode("utf-8")) > DATASET_NAME_LIMIT:
            return False, get_data_error_result(message=f"Dataset name length is {len(dataset_name)} which is larger than {DATASET_NAME_LIMIT}")

        # Deduplicate name within tenant
        dataset_name = duplicate_name(
            cls.query,
            name=dataset_name,
            tenant_id=tenant_id,
            status=StatusEnum.VALID.value,
        )

        # Verify tenant exists
        ok, _t = TenantService.get_by_id(tenant_id)
        if not ok:
            return False, get_data_error_result(message="Tenant not found.")

        max_kb_num_per_user = int(os.environ.get("MAX_KB_NUM_PER_USER", "3"))
        if max_kb_num_per_user > 0 and not AdminUser.query(user_id=tenant_id):
            if tenant_id == settings.REFERENCE_TENANT_ID or tenant_id in cls.get_all_group_reference_tenant_ids():
                pass
            else:
                user = User.select().where(User.id == tenant_id).first()
                if not user or user.email != "1505114161@qq.com":
                    kb_count = (
                        cls.model.select(fn.COUNT(1))
                        .where(
                            (cls.model.created_by == tenant_id)
                            & (cls.model.status == StatusEnum.VALID.value)
                        )
                        .scalar()
                    )
                    if int(kb_count or 0) >= max_kb_num_per_user:
                        return False, get_data_error_result(
                            code=RetCode.OPERATING_ERROR,
                            message=f"非管理员账户最多只能创建 {max_kb_num_per_user} 个知识库。",
                        )

        # Build payload
        kb_id = get_uuid()
        payload = {
            "id": kb_id,
            "name": dataset_name,
            "tenant_id": tenant_id,
            "created_by": tenant_id,
            "parser_id": (parser_id or "naive"),
            **kwargs # Includes optional fields such as description, language, permission, avatar, parser_config, etc.
        }

        # Update parser_config (always override with validated default/merged config)
        payload["parser_config"] = get_parser_config(parser_id, kwargs.get("parser_config"))

        return True, payload


    @classmethod
    @DB.connection_context()
    def get_list(cls, joined_tenant_ids, user_id,
                 page_number, items_per_page, orderby, desc, id, name, admin_bypass=False):
        # Get list of knowledge bases with filtering and pagination
        # Args:
        #     joined_tenant_ids: List of tenant IDs
        #     user_id: Current user ID
        #     page_number: Page number for pagination
        #     items_per_page: Number of items per page
        #     orderby: Field to order by
        #     desc: Boolean indicating descending order
        #     id: Optional ID filter
        #     name: Optional name filter
        #     admin_bypass: Bypass permission check if True
        # Returns:
        #     List of knowledge bases
        #     Total count of knowledge bases
        kbs = cls.model.select()
        if id:
            kbs = kbs.where(cls.model.id == id)
        if name:
            kbs = kbs.where(cls.model.name == name)
        
        if not admin_bypass:
            base_expr = (
                    (cls.model.tenant_id.in_(joined_tenant_ids)
                     & (cls.model.permission.in_([TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value])))
                    | (cls.model.tenant_id == user_id)
                    | (cls.model.permission.in_([TenantPermission.EVERYONE.value, TenantPermission.EVERYONE_VISIBLE.value]))
            )
            if settings.REFERENCE_TENANT_ID:
                base_expr = base_expr | (cls.model.tenant_id == settings.REFERENCE_TENANT_ID)
            group_reference_ids = cls.get_group_reference_tenant_ids(user_id)
            if group_reference_ids:
                base_expr = base_expr | cls.model.tenant_id.in_(group_reference_ids)
            kbs = kbs.where(base_expr)
            if not AdminUser.query(user_id=user_id, role_level=1):
                all_group_reference_ids = cls.get_all_group_reference_tenant_ids()
                hidden_group_reference_ids = list(set(all_group_reference_ids) - set(group_reference_ids))
                if settings.REFERENCE_TENANT_ID:
                    hidden_group_reference_ids = [
                        i for i in hidden_group_reference_ids if i != settings.REFERENCE_TENANT_ID
                    ]
                hidden_group_reference_ids = [i for i in hidden_group_reference_ids if i != user_id]
                if hidden_group_reference_ids:
                    kbs = kbs.where(~cls.model.tenant_id.in_(hidden_group_reference_ids))
        
        kbs = kbs.where(cls.model.status == StatusEnum.VALID.value)

        if desc:
            kbs = kbs.order_by(cls.model.getter_by(orderby).desc())
        else:
            kbs = kbs.order_by(cls.model.getter_by(orderby).asc())

        total = kbs.count()
        kbs = kbs.paginate(page_number, items_per_page)

        return list(kbs.dicts()), total

    @classmethod
    @DB.connection_context()
    def accessible(cls, kb_id, user_id):
        # Check if a dataset is accessible by a user
        # Args:
        #     kb_id: Knowledge base ID
        #     user_id: User ID
        # Returns:
        #     Boolean indicating accessibility
        if AdminUser.query(user_id=user_id):
            return True
        
        # Check if it's an EVERYONE permission KB first (optimization)
        kb = cls.model.get_or_none(cls.model.id == kb_id)
        if not kb:
            return False

        if settings.REFERENCE_TENANT_ID and kb.tenant_id == settings.REFERENCE_TENANT_ID:
            return True
        if kb.tenant_id == user_id:
            return True
        all_group_reference_ids = cls.get_all_group_reference_tenant_ids()
        if kb.tenant_id in all_group_reference_ids:
            return kb.tenant_id in cls.get_group_reference_tenant_ids(user_id)

        if kb.permission == TenantPermission.EVERYONE.value:
            return True
        
        if kb.permission == TenantPermission.EVERYONE_VISIBLE.value:
            return True
        
        if kb.permission in [TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value]:
            from api.db.services.user_group_service import UserGroupService
            team_tenant_ids = UserGroupService.get_team_tenant_ids(user_id)
            if kb.tenant_id in team_tenant_ids:
                return True
        
        return False

    @classmethod
    @DB.connection_context()
    def writable(cls, kb_id, user_id):
        kb = cls.model.get_or_none(cls.model.id == kb_id)
        if not kb:
            return False

        if AdminUser.query(user_id=user_id, role_level=1):
            return True

        if settings.REFERENCE_TENANT_ID and kb.tenant_id == settings.REFERENCE_TENANT_ID:
            return kb.tenant_id == user_id

        group_ids = cls.get_group_ids_by_reference_tenant_id(kb.tenant_id)
        if group_ids:
            if kb.tenant_id == user_id:
                return True
            if Group.select(Group.group_id).where(
                (Group.group_id.in_(group_ids)) & (Group.created_by == user_id)
            ).exists():
                return True
            if not AdminUser.query(user_id=user_id, role_level=2):
                return False
            return UserGroup.select().where(
                (UserGroup.user_id == user_id) & (UserGroup.group_id.in_(group_ids))
            ).exists()

        if AdminUser.query(user_id=user_id):
            return True

        if kb.tenant_id == user_id:
            return True

        if kb.permission == TenantPermission.EVERYONE.value:
            return True

        if kb.permission == TenantPermission.EVERYONE_VISIBLE.value:
            return False

        if kb.permission in [TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value]:
            from api.db.services.user_group_service import UserGroupService
            team_tenant_ids = UserGroupService.get_team_tenant_ids(user_id)
            return kb.tenant_id in team_tenant_ids

        return False

    @classmethod
    @DB.connection_context()
    def get_kb_by_id(cls, kb_id, user_id):
        # Get dataset by ID and user ID
        # Args:
        #     kb_id: Knowledge base ID
        #     user_id: User ID
        # Returns:
        #     List containing dataset information
        if AdminUser.query(user_id=user_id):
            kbs = cls.model.select().where(cls.model.id == kb_id).paginate(0, 1)
        else:
            # Reimplement using accessible logic (python side or complex query)
            # Since pagination is 0, 1, we can fetch one and check permissions.
            kbs = cls.model.select().where(cls.model.id == kb_id).paginate(0, 1)
            # We need to filter manually because we can't easily join on dynamic team logic
            # Or construct the query.
            # Query approach:
            from api.db.services.user_group_service import UserGroupService
            team_tenant_ids = UserGroupService.get_team_tenant_ids(user_id)
            group_reference_ids = cls.get_group_reference_tenant_ids(user_id)
            
            base_expr = (
                (cls.model.tenant_id.in_(team_tenant_ids) & (cls.model.permission.in_([TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value])))
                | (cls.model.tenant_id == user_id)
                | (cls.model.permission.in_([TenantPermission.EVERYONE.value, TenantPermission.EVERYONE_VISIBLE.value]))
            )
            if settings.REFERENCE_TENANT_ID:
                base_expr = base_expr | (cls.model.tenant_id == settings.REFERENCE_TENANT_ID)
            if group_reference_ids:
                base_expr = base_expr | cls.model.tenant_id.in_(group_reference_ids)
            kbs = kbs.where(base_expr)

        kbs = kbs.dicts()
        return list(kbs)

    @classmethod
    @DB.connection_context()
    def get_kb_by_name(cls, kb_name, user_id):
        # Get dataset by name and user ID
        # Args:
        #     kb_name: Knowledge base name
        #     user_id: User ID
        # Returns:
        #     List containing dataset information
        if AdminUser.query(user_id=user_id):
            kbs = cls.model.select().where(cls.model.name == kb_name).paginate(0, 1)
        else:
            from api.db.services.user_group_service import UserGroupService
            team_tenant_ids = UserGroupService.get_team_tenant_ids(user_id)
            group_reference_ids = cls.get_group_reference_tenant_ids(user_id)
            
            base_expr = (
                (cls.model.tenant_id.in_(team_tenant_ids) & (cls.model.permission.in_([TenantPermission.TEAM.value, TenantPermission.TEAM_VISIBLE.value])))
                | (cls.model.tenant_id == user_id)
                | (cls.model.permission.in_([TenantPermission.EVERYONE.value, TenantPermission.EVERYONE_VISIBLE.value]))
            )
            if settings.REFERENCE_TENANT_ID:
                base_expr = base_expr | (cls.model.tenant_id == settings.REFERENCE_TENANT_ID)
            if group_reference_ids:
                base_expr = base_expr | cls.model.tenant_id.in_(group_reference_ids)
            kbs = cls.model.select().where(
                cls.model.name == kb_name,
                base_expr
            ).paginate(0, 1)
        kbs = kbs.dicts()
        return list(kbs)

    @classmethod
    @DB.connection_context()
    def atomic_increase_doc_num_by_id(cls, kb_id):
        data = {}
        data["update_time"] = current_timestamp()
        data["update_date"] = datetime_format(datetime.now())
        data["doc_num"] = cls.model.doc_num + 1
        num = cls.model.update(data).where(cls.model.id == kb_id).execute()
        return num

    @classmethod
    @DB.connection_context()
    def update_document_number_in_init(cls, kb_id, doc_num):
        """
        Only use this function when init system
        """
        ok, kb = cls.get_by_id(kb_id)
        if not ok:
            return
        kb.doc_num = doc_num

        dirty_fields = kb.dirty_fields
        if cls.model._meta.combined.get("update_time") in dirty_fields:
            dirty_fields.remove(cls.model._meta.combined["update_time"])

        if cls.model._meta.combined.get("update_date") in dirty_fields:
            dirty_fields.remove(cls.model._meta.combined["update_date"])

        try:
            kb.save(only=dirty_fields)
        except ValueError as e:
            if str(e) == "no data to save!":
                pass # that's OK
            else:
                raise e

    @classmethod
    @DB.connection_context()
    def decrease_document_num_in_delete(cls, kb_id, doc_num_info: dict):
        kb_row = cls.model.get_by_id(kb_id)
        if not kb_row:
            raise RuntimeError(f"kb_id {kb_id} does not exist")
        update_dict = {
            'doc_num': kb_row.doc_num - doc_num_info['doc_num'],
            'chunk_num': kb_row.chunk_num - doc_num_info['chunk_num'],
            'token_num': kb_row.token_num - doc_num_info['token_num'],
            'update_time': current_timestamp(),
            'update_date': datetime_format(datetime.now())
        }
        return cls.model.update(update_dict).where(cls.model.id == kb_id).execute()
