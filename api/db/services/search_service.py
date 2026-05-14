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
from datetime import datetime

from peewee import fn

from common.constants import StatusEnum
from api.db.db_models import DB, Search, User
from api.db.services.common_service import CommonService
from common.time_utils import current_timestamp, datetime_format
from api.db.db_models import AdminUser
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.apps import login_required, current_user


class SearchService(CommonService):
    model = Search

    @classmethod
    def save(cls, **kwargs):
        kwargs["create_time"] = current_timestamp()
        kwargs["create_date"] = datetime_format(datetime.now())
        kwargs["update_time"] = current_timestamp()
        kwargs["update_date"] = datetime_format(datetime.now())
        obj = cls.model.create(**kwargs)
        return obj

    @classmethod
    @DB.connection_context()
    def accessible4deletion(cls, search_id, user_id) -> bool:
        search = (
            cls.model.select(cls.model.id)
            .where(
                cls.model.id == search_id,
                cls.model.created_by == user_id,
                cls.model.status == StatusEnum.VALID.value,
            )
            .first()
        )
        return search is not None

    @classmethod
    @DB.connection_context()
    def get_detail(cls, search_id):
        fields = [
            cls.model.id,
            cls.model.avatar,
            cls.model.tenant_id,
            cls.model.name,
            cls.model.description,
            cls.model.created_by,
            cls.model.search_config,
            cls.model.update_time,
            User.nickname,
            User.avatar.alias("tenant_avatar"),
        ]
        search = (
            cls.model.select(*fields)
            .join(User, on=((User.id == cls.model.tenant_id) & (User.status == StatusEnum.VALID.value)))
            .where((cls.model.id == search_id) & (cls.model.status == StatusEnum.VALID.value))
            .first()
            .to_dict()
        )
        if not search:
            return {}
        
        # --- 新增的判断与修改逻辑开始 ---
        # 1. 获取 search_config，如果数据库里是空的，就初始化为一个空字典
        search_config = search.get('search_config') or {}
        
        # 2. 判断 kb_ids 是否为空列表，或者根本不存在 复给默认知识库
        if not search_config.get('kb_ids'): 
            # --- 执行自动查询逻辑 ---
            admin_bypass=False
            if AdminUser.query(user_id=current_user.id, role_level=1):
                admin_bypass=True
            kb_list, total_count = KnowledgebaseService.get_by_tenant_ids(
                joined_tenant_ids=[],
                user_id=current_user.id,
                page_number=1,
                items_per_page=1000,
                orderby="id",
                desc=False,
                keywords=None,
                admin_bypass=admin_bypass
            )
            kb_ids = [kb["id"] for kb in kb_list]
            search_config['kb_ids'] = kb_ids
        
        # 4. 将修改后的配置重新赋值给 search 字典
        search['search_config'] = search_config
        # --- 新增的判断与修改逻辑结束 ---

        return search

    @classmethod
    @DB.connection_context()
    def get_by_tenant_ids(cls, joined_tenant_ids, user_id, page_number, items_per_page, orderby, desc, keywords):
        fields = [
            cls.model.id,
            cls.model.avatar,
            cls.model.tenant_id,
            cls.model.name,
            cls.model.description,
            cls.model.created_by,
            cls.model.status,
            cls.model.update_time,
            cls.model.create_time,
            User.nickname,
            User.avatar.alias("tenant_avatar"),
        ]
        query = (
            cls.model.select(*fields)
            .join(User, on=(cls.model.tenant_id == User.id))
            .where(((cls.model.tenant_id.in_(joined_tenant_ids)) | (cls.model.tenant_id == user_id)) & (
                        cls.model.status == StatusEnum.VALID.value))
        )

        if keywords:
            query = query.where(fn.LOWER(cls.model.name).contains(keywords.lower()))
        if desc:
            query = query.order_by(cls.model.getter_by(orderby).desc())
        else:
            query = query.order_by(cls.model.getter_by(orderby).asc())

        count = query.count()

        if page_number and items_per_page:
            query = query.paginate(page_number, items_per_page)

        return list(query.dicts()), count

    @classmethod
    @DB.connection_context()
    def delete_by_tenant_id(cls, tenant_id):
        return cls.model.delete().where(cls.model.tenant_id == tenant_id).execute()
