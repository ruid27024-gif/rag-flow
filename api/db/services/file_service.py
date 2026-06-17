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
import asyncio
import base64
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Union

from peewee import fn

from api.db import KNOWLEDGEBASE_FOLDER_NAME, FileType
from api.db.db_models import DB, AdminUser, User, Document, File, File2Document, Knowledgebase, Task
from api.db.services import duplicate_name
from api.db.services.common_service import CommonService
from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.group_service import GroupService
from api.db.services.user_group_service import UserGroupService
from common.misc_utils import get_uuid
from common.constants import StatusEnum, TaskStatus, FileSource, ParserType
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.task_service import TaskService
from api.utils.file_utils import filename_type, read_potential_broken_pdf, thumbnail_img, sanitize_path
from rag.llm.cv_model import GptV4
from common import settings
from api.db.services.file_admin_service import FileAdminService
from api.db.services.file_group_service import FileGroupService


class FileService(CommonService):
    # Service class for managing file operations and storage
    model = File

    @classmethod
    @DB.connection_context()
    def get_tenant_id_by_parent_id(cls, parent_id):
        """
        通过父文件夹ID获取租户ID (tenant_id)
        Args:
            parent_id (str): 父文件夹的UUID
        Returns:
            str or None: 返回 tenant_id，如果未找到则返回 None
        """
        try:
            # 1. 尝试从数据库中获取该记录，只选择 tenant_id 字段以提高效率
            obj = cls.model.select(cls.model.tenant_id).where(
                cls.model.id == parent_id
            ).first()

            # 2. 如果找到了对象，返回 tenant_id，否则返回 None
            if obj:
                return obj.tenant_id
            return None

        except Exception as e:
            print(f"Error getting tenant_id by parent_id: {e}")
            return None


    @classmethod
    @DB.connection_context()
    def get_all_root_id(cls):
        files = cls.model.select().where(FileService.model.parent_id == FileService.model.id).execute()
        return [file.id for file in files]

    @classmethod
    @DB.connection_context()
    def get_team_root_id(cls, user_ids):
        """
        通过用户 ID 列表获取团队根目录 ID 列表
        Args:
            user_ids: 用户 ID 列表 (例如: ['uuid_1', 'uuid_2'])
        Returns:
            list: ID 列表
        """
        try:
            if isinstance(user_ids, str):
                user_ids = [user_ids]

            query = cls.model.select().where(
                (cls.model.parent_id == cls.model.id) &  # 根目录条件
                (cls.model.tenant_id.in_(user_ids))  # 用户ID在列表中
            )

            return [file.id for file in query]

        except Exception as e:
            print(f"Error fetching team root ids: {e}")
            return []
    
    @classmethod
    @DB.connection_context()
    def get_root_self(cls, tenant_id, pf_id, page_number, items_per_page, orderby, desc, keywords):
        if keywords:
            files = cls.model.select().where(
                (cls.model.tenant_id == tenant_id),
                (cls.model.id == pf_id),
                (fn.LOWER(cls.model.name).contains(keywords.lower()))
            )
        else:
            files = cls.model.select().where(
                (cls.model.tenant_id == tenant_id),
                (cls.model.id == pf_id)
            )

        count = files.count()

        if desc in [True, "true", "True", "1", 1]:
            files = files.order_by(cls.model.getter_by(orderby).desc())
        else:
            files = files.order_by(cls.model.getter_by(orderby).asc())

        files = files.paginate(page_number, items_per_page)

        res_files = list(files.dicts())

        for file in res_files:
            if file["type"] == FileType.FOLDER.value:
                file["size"] = cls.get_folder_size(file["id"])
                file["kbs_info"] = []

                children = list(
                    cls.model.select()
                    .where(
                        (cls.model.parent_id == file["id"]),
                        ~(cls.model.id == file["id"]),
                    )
                    .dicts()
                )

                file["has_child_folder"] = any(
                    value["type"] == FileType.FOLDER.value for value in children
                )
                continue

            kbs_info = cls.get_kb_id_by_file_id(file["id"])
            file["kbs_info"] = kbs_info

        return res_files, count

    # TODO 新增的
    @classmethod
    @DB.connection_context()
    def get_by_pf_id_new(cls, tenant_id, pf_id, page_number, items_per_page, orderby, desc, keywords):
        # 获取parent_id 是根目录下的行 (根目录下的目录/虚拟文件) 让前端进行渲染
        # 如果有关键字, 排除 / 本身 ，上一级
        if keywords:
            files = cls.model.select().where((cls.model.parent_id == pf_id),
                                             (fn.LOWER(cls.model.name).contains(keywords.lower())),
                                             ~(cls.model.id == pf_id))

        else:
            files = cls.model.select().where((cls.model.parent_id == pf_id), ~(cls.model.id == pf_id))
        count = files.count()

        if desc:
            files = files.order_by(cls.model.getter_by(orderby).desc())

        else:
            files = files.order_by(cls.model.getter_by(orderby).asc())

        # 默认按照时间的降序进行排
        files = files.order_by(cls.model.getter_by("create_time").desc())

        files = files.paginate(page_number, items_per_page)

        res_files = list(files.dicts())

        from .user_service import UserService
        from api.apps import login_required, current_user

        nickname = None
        # 开始解析每一行
        for file in res_files:

            # 获取文件夹/文件 的前缀(组 + nickname)
            # 获取用户
            file_owner = UserService.filter_by_id(file["tenant_id"])

            # 参考库的情况
            if file_owner and file_owner.id != current_user.id and file["parent_id"] in FileService.get_all_root_id():
                file_owner_id = file_owner.id

                global_tenant_id = settings.REFERENCE_TENANT_ID
                cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
                cfg_map_ids = cfg_map.values()

                # 如果是全局参考库
                if file_owner_id == global_tenant_id:
                    nickname = "全局文献参考库"
                elif file_owner_id in cfg_map_ids:
                    nickname = "组内文献 + 报告参考库"
                else:
                    nickname = ""

            print(nickname)
            # 如果是文件夹
            if file["type"] == FileType.FOLDER.value:
                if nickname:
                    if file["name"] == '.knowledgebase' :
                        file["name"] = nickname

                    # 自建的文件夹
                    else:
                        file["name"] = file.name
                        

                # 计算大小
                file["size"] = cls.get_folder_size(file["id"])
                file["kbs_info"] = []
                # 检查是否有子文件夹：又查了一次数据库（children = ...），只是为了看里面有没有文件夹，用来决定前端是否显示那个“小箭头”图标。
                children = list(
                    cls.model.select()
                    .where(
                        (cls.model.parent_id == file["id"]),
                        ~(cls.model.id == file["id"]),
                    )
                    .dicts()
                )

                file["has_child_folder"] = any(value["type"] == FileType.FOLDER.value for value in children)
                continue

            # 如果是文件
            kbs_info = cls.get_kb_id_by_file_id(file["id"])
            file["kbs_info"] = kbs_info

        return res_files, count

    @classmethod
    @DB.connection_context()
    def get_by_pf_id(cls, tenant_id, pf_id, page_number, items_per_page, orderby, desc, keywords):
        # Get files by parent folder ID with pagination and filtering
        # Args:
        #     tenant_id: ID of the tenant
        #     pf_id: Parent folder ID
        #     page_number: Page number for pagination
        #     items_per_page: Number of items per page
        #     orderby: Field to order by
        #     desc: Boolean indicating descending order
        #     keywords: Search keywords
        # Returns:
        #     Tuple of (file_list, total_count)
        if keywords:
            files = cls.model.select().where((cls.model.parent_id == pf_id), (fn.LOWER(cls.model.name).contains(keywords.lower())), ~(cls.model.id == pf_id))
        else:
            files = cls.model.select().where((cls.model.parent_id == pf_id), ~(cls.model.id == pf_id))
            # (cls.model.tenant_id == tenant_id), 
        count = files.count()
        if desc:
            files = files.order_by(cls.model.getter_by(orderby).desc())
        else:
            files = files.order_by(cls.model.getter_by(orderby).asc())

        files = files.paginate(page_number, items_per_page)

        res_files = list(files.dicts())

        for file in res_files:
            if file["type"] == FileType.FOLDER.value:
                file["size"] = cls.get_folder_size(file["id"])
                file["kbs_info"] = []
                children = list(
                    cls.model.select()
                    .where(
                        # (cls.model.tenant_id == tenant_id),
                        (cls.model.parent_id == file["id"]),
                        ~(cls.model.id == file["id"]),
                    )
                    .dicts()
                )
                file["has_child_folder"] = any(value["type"] == FileType.FOLDER.value for value in children)
                continue
            kbs_info = cls.get_kb_id_by_file_id(file["id"])
            file["kbs_info"] = kbs_info

        return res_files, count

    @classmethod
    @DB.connection_context()
    def get_kb_id_by_file_id(cls, file_id):
        # Get dataset IDs associated with a file
        # Args:
        #     file_id: File ID
        # Returns:
        #     List of dictionaries containing dataset IDs and names
        kbs = (
            cls.model.select(*[Knowledgebase.id, Knowledgebase.name])
            .join(File2Document, on=(File2Document.file_id == file_id))
            .join(Document, on=(File2Document.document_id == Document.id))
            .join(Knowledgebase, on=(Knowledgebase.id == Document.kb_id))
            .where(cls.model.id == file_id)
        )

        if not kbs:
            return []
        kbs_info_list = []
        for kb in list(kbs.dicts()):
            kbs_info_list.append({"kb_id": kb["id"], "kb_name": kb["name"]})
        return kbs_info_list

    @classmethod
    @DB.connection_context()
    def get_kb_id_by_file_id_new(cls, file_id, pre):
        # Get dataset IDs associated with a file
        # Args:
        #     file_id: File ID
        # Returns:
        #     List of dictionaries containing dataset IDs and names
        kbs = (
            cls.model.select(*[Knowledgebase.id, Knowledgebase.name])
            .join(File2Document, on=(File2Document.file_id == file_id))
            .join(Document, on=(File2Document.document_id == Document.id))
            .join(Knowledgebase, on=(Knowledgebase.id == Document.kb_id))
            .where(cls.model.id == file_id)
        )

        if not kbs:
            return []
        kbs_info_list = []

        for kb in list(kbs.dicts()):
            kbs_info_list.append({"kb_id": kb["id"], "kb_name": kb["name"]})
        return kbs_info_list

    @classmethod
    @DB.connection_context()
    def get_by_pf_id_name(cls, id, name):
        # Get file by parent folder ID and name
        # Args:
        #     id: Parent folder ID
        #     name: File name
        # Returns:
        #     File object or None if not found
        file = cls.model.select().where((cls.model.parent_id == id) & (cls.model.name == name))
        if file.count():
            e, file = cls.get_by_id(file[0].id)
            if not e:
                raise RuntimeError("Database error (File retrieval)!")
            return file
        return None

    @classmethod
    @DB.connection_context()
    def get_id_list_by_id(cls, id, name, count, res):
        # Recursively get list of file IDs by traversing folder structure
        # Args:
        #     id: Starting folder ID
        #     name: List of folder names to traverse
        #     count: Current depth in traversal
        #     res: List to store results
        # Returns:
        #     List of file IDs
        if count < len(name):
            file = cls.get_by_pf_id_name(id, name[count])
            if file:
                res.append(file.id)
                return cls.get_id_list_by_id(file.id, name, count + 1, res)
            else:
                return res
        else:
            return res

    @classmethod
    @DB.connection_context()
    def get_all_innermost_file_ids(cls, folder_id, result_ids):
        # Get IDs of all files in the deepest level of folders
        # Args:
        #     folder_id: Starting folder ID
        #     result_ids: List to store results
        # Returns:
        #     List of file IDs
        subfolders = cls.model.select().where(cls.model.parent_id == folder_id)
        if subfolders.exists():
            for subfolder in subfolders:
                cls.get_all_innermost_file_ids(subfolder.id, result_ids)
        else:
            result_ids.append(folder_id)
        return result_ids

    @classmethod
    @DB.connection_context()
    def get_all_file_ids_by_tenant_id(cls, tenant_id):
        fields = [cls.model.id]
        files = cls.model.select(*fields).where(cls.model.tenant_id == tenant_id)
        files.order_by(cls.model.create_time.asc())
        offset, limit = 0, 100
        res = []
        while True:
            file_batch = files.offset(offset).limit(limit)
            _temp = list(file_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res

    @classmethod
    @DB.connection_context()
    def create_folder(cls, file, parent_id, name, count):
        from api.apps import current_user
        # Recursively create folder structure
        # Args:
        #     file: Current file object
        #     parent_id: Parent folder ID
        #     name: List of folder names to create
        #     count: Current depth in creation
        # Returns:
        #     Created file object
        if count > len(name) - 2:
            return file
        else:
            file = cls.insert(
                {"id": get_uuid(), "parent_id": parent_id, "tenant_id": current_user.id, "created_by": current_user.id, "name": name[count], "location": "", "size": 0, "type": FileType.FOLDER.value}
            )
            try:
                if AdminUser.query(user_id=current_user.id, role_level=1):
                    FileAdminService.insert(
                {"id": get_uuid(), "parent_id": parent_id, "tenant_id": current_user.id, "created_by": current_user.id, "name": name[count], "location": "", "size": 0, "type": FileType.FOLDER.value}
            )
                else:
                    FileGroupService.insert(
                {"id": get_uuid(), "parent_id": parent_id, "tenant_id": current_user.id, "created_by": current_user.id, "name": name[count], "location": "", "size": 0, "type": FileType.FOLDER.value}
            )
                    FileAdminService.insert(
                {"id": get_uuid(), "parent_id": parent_id, "tenant_id": current_user.id, "created_by": current_user.id, "name": name[count], "location": "", "size": 0, "type": FileType.FOLDER.value}
            )
            except Exception as e:
                print("1、2级表知识库未能挂到.knowladge")

            return cls.create_folder(file, file.id, name, count + 1)

    @classmethod
    @DB.connection_context()
    def is_parent_folder_exist(cls, parent_id):
        # Check if parent folder exists
        # Args:
        #     parent_id: Parent folder ID
        # Returns:
        #     Boolean indicating if folder exists
        parent_files = cls.model.select().where(cls.model.id == parent_id)
        if parent_files.count():
            return True
        cls.delete_folder_by_pf_id(parent_id)
        return False
    
    @classmethod
    @DB.connection_context()
    def is_root_node(cls, file_id):
        # 判断指定 ID 是否为根节点
        # Args:
        #     file_id: 文件/文件夹 ID
        # Returns:
        #     Boolean: True 表示是根节点，False 表示不是
        
        e, file = cls.get_by_id(file_id)
        # 如果文件不存在，直接返回 False
        if not e:
            return False
        
        # 核心判断逻辑：父级 ID 等于自身 ID，即为根节点
        return file.parent_id == file.id

    @classmethod
    @DB.connection_context()
    def get_root_folder(cls, tenant_id):
        # Get or create root folder for tenant
        # Args:
        #     tenant_id: Tenant ID
        # Returns:
        #     Root folder dictionary
        for file in cls.model.select().where((cls.model.tenant_id == tenant_id), (cls.model.parent_id == cls.model.id)):
            return file.to_dict()

        file_id = get_uuid()
        file = {
            "id": file_id,
            "parent_id": file_id,
            "tenant_id": tenant_id,
            "created_by": tenant_id,
            "name": "/",
            "type": FileType.FOLDER.value,
            "size": 0,
            "location": "",
        }
        cls.save(**file)
        try:
            if AdminUser.query(user_id=tenant_id, role_level=1):
                FileAdminService.save(**file)
            else:
                FileGroupService.save(**file)
                FileAdminService.save(**file)
        except Exception as e:
            print("1、2级表知识库写入根路径失败")
        return file

    @classmethod
    @DB.connection_context()
    def get_kb_folder(cls, tenant_id):
        # Get dataset folder for tenant
        # Args:
        #     tenant_id: Tenant ID
        # Returns:
        #     Knowledge base folder dictionary
        root_folder = cls.get_root_folder(tenant_id)
        root_id = root_folder["id"]
        kb_folder = cls.model.select().where((cls.model.tenant_id == tenant_id), (cls.model.parent_id == root_id), (cls.model.name == KNOWLEDGEBASE_FOLDER_NAME)).first()
        if not kb_folder:
            # 没有和就创建一个 .knowladge
            kb_folder = cls.new_a_file_from_kb(tenant_id, KNOWLEDGEBASE_FOLDER_NAME, root_id)

            try:
                # 管理员只放1级表
                if AdminUser.query(user_id=tenant_id, role_level=1):
                    knowladge_id = kb_folder.id
                    file = {
                        "id": knowladge_id,
                        "parent_id": root_id,
                        "tenant_id": tenant_id,
                        "created_by": tenant_id,
                        "name": KNOWLEDGEBASE_FOLDER_NAME,
                        "type": kb_folder.type,
                        "size": kb_folder.size,
                        "location": kb_folder.location,
                        "source_type": FileSource.KNOWLEDGEBASE,
                    }
                    FileAdminService.save(**file)
                # 二级管理员创建后挂接到自己的pf_id上
                if AdminUser.query(user_id=tenant_id, role_level=2):
                    knowladge_id = kb_folder.id
                    file = {
                        "id": knowladge_id,
                        "parent_id": root_id,
                        "tenant_id": tenant_id,
                        "created_by": tenant_id,
                        "name": KNOWLEDGEBASE_FOLDER_NAME,
                        "type": kb_folder["type"],
                        "size": kb_folder["size"],
                        "location": kb_folder["location"],
                        "source_type": FileSource.KNOWLEDGEBASE,
                    }
                    FileAdminService.save(**file)
                    FileGroupService.save(**file)
                # 普通用户
                else:
                    knowladge_id = kb_folder.id
                    file = {
                        "id": knowladge_id,
                        "parent_id": root_id,
                        "tenant_id": tenant_id,
                        "created_by": tenant_id,
                        "name": KNOWLEDGEBASE_FOLDER_NAME,
                        "type": kb_folder.type,
                        "size": kb_folder.size,
                        "location": kb_folder["location"],
                        "source_type": FileSource.KNOWLEDGEBASE,
                    }
                    FileGroupService.save(**file)
                    FileAdminService.save(**file)
            except Exception as e:
                    print(f"错误详情: {e}")
            return kb_folder
        return kb_folder.to_dict()

    @classmethod
    @DB.connection_context()
    def new_a_file_from_kb(cls, tenant_id, name, parent_id, ty=FileType.FOLDER.value, size=0, location=""):
        # Create a new file from dataset
        # Args:
        #     tenant_id: Tenant ID
        #     name: File name
        #     parent_id: Parent folder ID
        #     ty: File type
        #     size: File size
        #     location: File location
        # Returns:
        #     Created file dictionary
        for file in cls.query(tenant_id=tenant_id, parent_id=parent_id, name=name):
            return file.to_dict()
        file = {
            "id": get_uuid(),
            "parent_id": parent_id,
            "tenant_id": tenant_id,
            "created_by": tenant_id,
            "name": name,
            "type": ty,
            "size": size,
            "location": location,
            "source_type": FileSource.KNOWLEDGEBASE,
        }
        cls.save(**file)
        # 知识库挂到1级、2级表
        try:
            if AdminUser.query(user_id=tenant_id, role_level=1):
                FileAdminService.save(**file)
            else:
                FileGroupService.save(**file)
                FileAdminService.save(**file)
        except Exception as e:
            print("1、2级表知识库未能挂到.knowladge")
        return file

    @classmethod
    @DB.connection_context()
    def init_knowledgebase_docs(cls, root_id, tenant_id):
        # Initialize dataset documents
        # Args:
        #     root_id: Root folder ID
        #     tenant_id: Tenant ID
        for _ in cls.model.select().where((cls.model.name == KNOWLEDGEBASE_FOLDER_NAME) & (cls.model.parent_id == root_id)):
            return
        
        # 创建.knowladge
        folder = cls.new_a_file_from_kb(tenant_id, KNOWLEDGEBASE_FOLDER_NAME, root_id)
        # 获取所有的知识库
        for kb in Knowledgebase.select(*[Knowledgebase.id, Knowledgebase.name]).where(Knowledgebase.tenant_id == tenant_id):
            # 为每个知识库创建一个文件夹
            kb_folder = cls.new_a_file_from_kb(tenant_id, kb.name, folder["id"])
            # 遍历文档将文档关联到文件服务
            for doc in DocumentService.query(kb_id=kb.id):
                FileService.add_file_from_kb(doc.to_dict(), kb_folder["id"], tenant_id)


    @classmethod
    @DB.connection_context()
    def get_parent_folder(cls, file_id):
        # Get parent folder of a file
        # Args:
        #     file_id: File ID
        # Returns:
        #     Parent folder object
        file = cls.model.select().where(cls.model.id == file_id)
        if file.count():
            e, file = cls.get_by_id(file[0].parent_id)
        
            print("------------------------------------------------------")
            if not e:
                raise RuntimeError("Database error (File retrieval)!")
        else:
            raise RuntimeError("Database error (File doesn't exist)!")
        return file

    # @classmethod
    # @DB.connection_context()
    # def get_all_parent_folders(cls, start_id):
    #     # Get all parent folders in path
    #     # Args:
    #     #     start_id: Starting file ID
    #     # Returns:
    #     #     List of parent folder objects
    #     parent_folders = []
    #     current_id = start_id
        
    #     while current_id:
    #         e, file = cls.get_by_id(current_id)
    #         # 如果不是根目录
    #         if e and file.parent_id != file.id:
                
    #             from .user_service import UserService
    #             from api.apps import login_required, current_user
                
    #             # 获取文件的拥有者（参考库、组参考库、自己）
    #             file_owner = UserService.filter_by_id(file.tenant_id)

    #             # 参考库的情况
    #             if file_owner and file_owner.id != current_user.id and file.parent_id in FileService.get_all_root_id():
    #                 # 文件拥有人
    #                 file_owner_id = file_owner.id

    #                 global_tenant_id = settings.REFERENCE_TENANT_ID

    #                 cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
    #                 cfg_map_ids = cfg_map.values()

    #                 # 如果是全局参考库
    #                 if file_owner_id == global_tenant_id:
    #                     nickname = "全局文献参考库"
    #                 elif file_owner_id in cfg_map_ids:
    #                     nickname = "组内文献 + 报告参考库"
    #                 else:
    #                     nickname = ""

                    

    #             # 如果是文件夹
    #             if file.type == FileType.FOLDER.value:
    #                 if nickname:
    #                     if file.name == '.knowledgebase' :
    #                         file.name = nickname

    #                     # 自建的文件夹
    #                     else:
    #                         file.name = file.name



    #             # 递归一层一层向上获取
    #             parent_folders.append(file)

    #             current_id = file.parent_id
    #         else:
    #             global_tenant_id = settings.REFERENCE_TENANT_ID
    #             parent_folders.append(file)
    #             # group_id = UserGroupService.get_group_id_by_id(current_user.id)
    #             # cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
    #             # # 当前在全局参考库下
    #             # if file.id == global_tenant_id:
    #             #     # 找到用户属于的组 获取到组id
                    
    #             #     if group_id and group_id in cfg_map and cfg_map[group_id]:
    #             #         group_public_tenant_id = cfg_map[group_id]
    #             #         flie_group = cls.model.select().where((cls.model.tenant_id==group_public_tenant_id )and (file.parent_id == file.id))
    #             #         file.name = "组内文献 + 报告参考库"
    #             #         parent_folders.append(flie_group)

    #             #         # 获取自己的根目录下
    #             #         file_owner = cls.model.select().where((cls.model.tenant_id==current_user.id)and (file.parent_id == file.id))

    #             #     # 当前在全局参考库下
    #             #     elif file.id in cfg_map:

    #             #         # 获取参考库的根 + 自己的

    #             #     else :

    #             #         # 获取参考库 + 组参考库的

                    


    #             break

    #     print("all--------------------------------------------")
    #     print(parent_folders)
    #     return parent_folders

    @classmethod
    @DB.connection_context()
    def get_all_parent_folders(cls, start_id):
        # Get all parent folders in path
        # Args:
        #     start_id: Starting file ID
        # Returns:
        #     List of parent folder objects
        # 1. 初始化一个空列表，用来装所有的父文件夹
        parent_folders = []
        # 2. 从传入的 start_id 开始（比如一个很深层级的文件 ID）
        current_id = start_id
        # 3. 开启循环，一直往上找，直到找不到为止
        while current_id:
            # 根据 ID 去数据库查这一条记录
            e, file = cls.get_by_id(current_id)
            # 如果存在且不是根
            if e and file.parent_id != file.id:
                # 把 current_id 更新为它的父级 ID，准备下一轮循环
                parent_folders.append(file)
                current_id = file.parent_id
            else:
                parent_folders.append(file)
                break
        return parent_folders

    @classmethod
    @DB.connection_context()
    def insert(cls, file):
        # Insert a new file record
        # Args:
        #     file: File data dictionary
        # Returns:
        #     Created file object
        if not cls.save(**file):
            raise RuntimeError("Database error (File)!")
        
        from api.apps import login_required, current_user
        try:

            FileGroupService.save(**file)
            FileAdminService.save(**file)
        except Exception as e:
            print("1、2级表文件名称未能挂载到知识库")

        return File(**file)
    
    """
        try:
            if AdminUser.query(user_id=tenant_id, role_level=1):
                FileAdminService.save(**file)
            else:
                FileGroupService.save(**file)
                FileAdminService.save(**file)
        except Exception as e:
            print("1、2级表文件名称未能挂载到知识库")
    """

    @classmethod
    @DB.connection_context()
    def delete(cls, file):
        # try:

        FileGroupService.delete_by_id(file.id)
        FileAdminService.delete_by_id(file.id)

        # except Exception as e:
        #     print("1、2级表删除文件失败")
        
        return cls.delete_by_id(file.id)

    @classmethod
    @DB.connection_context()
    def delete_by_pf_id(cls, folder_id):
        from api.apps import login_required, current_user
        try:
            if AdminUser.query(user_id=current_user.id, role_level=1):
                FileAdminService.model.delete().where(cls.model.parent_id == folder_id).execute()
            else:
                FileGroupService.model.delete().where(cls.model.parent_id == folder_id).execute()
                FileAdminService.model.delete().where(cls.model.parent_id == folder_id).execute()
        except Exception as e:
            print("删除失败")
        return cls.model.delete().where(cls.model.parent_id == folder_id).execute()

    @classmethod
    @DB.connection_context()
    def delete_folder_by_pf_id(cls, user_id, folder_id):
        try:
            files = cls.model.select().where((cls.model.tenant_id == user_id) & (cls.model.parent_id == folder_id))
            for file in files:
                cls.delete_folder_by_pf_id(user_id, file.id)
                from api.apps import login_required, current_user
                try:
                    if AdminUser.query(user_id=current_user.id, role_level=1):
                        FileAdminService.delete_folder_by_pf_id(user_id, file.id)
                    else:
                        FileGroupService.delete_folder_by_pf_id(user_id, file.id)
                        FileAdminService.delete_folder_by_pf_id(user_id, file.id)
                except Exception as e:
                    print("删除失败")

            return (cls.model.delete().where((cls.model.tenant_id == user_id) & (cls.model.id == folder_id)).execute(),)
        except Exception:
            logging.exception("delete_folder_by_pf_id")
            raise RuntimeError("Database error (File retrieval)!")

    @classmethod
    @DB.connection_context()
    def get_file_count(cls, tenant_id):
        files = cls.model.select(cls.model.id).where(cls.model.tenant_id == tenant_id)
        return len(files)

    @classmethod
    @DB.connection_context()
    def get_folder_size(cls, folder_id):
        size = 0

        def dfs(parent_id):
            nonlocal size
            for f in cls.model.select(*[cls.model.id, cls.model.size, cls.model.type]).where(cls.model.parent_id == parent_id, cls.model.id != parent_id):
                size += f.size
                if f.type == FileType.FOLDER.value:
                    dfs(f.id)

        dfs(folder_id)
        return size

    @classmethod
    @DB.connection_context()
    def add_file_from_kb(cls, doc, kb_folder_id, tenant_id):
        # 没找到这个单个文件就执行下面的操作
        for _ in File2DocumentService.get_by_document_id(doc["id"]):
            return
        
        # kb_folder_id 库名对应的id
        file = {
            "id": get_uuid(),
            "parent_id": kb_folder_id,
            "tenant_id": tenant_id,
            "created_by": tenant_id,
            "name": doc["name"],
            "type": doc["type"],
            "size": doc["size"],
            "location": doc["location"],
            "source_type": FileSource.KNOWLEDGEBASE,
        }

        print(file)
        cls.save(**file)
        try:
            if AdminUser.query(user_id=tenant_id, role_level=1):
                FileAdminService.save(**file)
            else:
                FileGroupService.save(**file)
                FileAdminService.save(**file)
        except Exception as e:
            print("1、2级表文件名称未能挂载到知识库")

        File2DocumentService.save(**{"id": get_uuid(), "file_id": file["id"], "document_id": doc["id"]})

    @classmethod
    @DB.connection_context()
    def move_file(cls, file_ids, folder_id):
        try:
            cls.filter_update((cls.model.id << file_ids,), {"parent_id": folder_id})
            from api.apps import login_required, current_user
            try:
                if AdminUser.query(user_id=current_user.id, role_level=1):
                    FileAdminService.filter_update((cls.model.id << file_ids,), {"parent_id": folder_id})
                else:
                    FileGroupService.filter_update((cls.model.id << file_ids,), {"parent_id": folder_id})
                    FileAdminService.filter_update((cls.model.id << file_ids,), {"parent_id": folder_id})
            except Exception as e:
                print("1、2级表文件移动后路径变更失败")
            
        except Exception:
            logging.exception("move_file")
            raise RuntimeError("Database error (File move)!")


    @classmethod
    @DB.connection_context()
    def upload_document(self, kb, file_objs, user_id, src="local", parent_path: str | None = None):
        
        # 获取知识库的tenant_id
        kb_tenant_id = kb.tenant_id
        user_id = kb_tenant_id
        # 获取当前用户的根
        root_folder = self.get_root_folder(user_id)
        pf_id = root_folder["id"]
        # 已经存在的，知识库全部挂载到.knowladge ; 文件挂载到库名
        self.init_knowledgebase_docs(pf_id, user_id)

        # 未存在的，新增的 .knowladge
        kb_root_folder = self.get_kb_folder(user_id)
        # 库名称号 --> .knowladge
        kb_folder = self.new_a_file_from_kb(kb.tenant_id, kb.name, kb_root_folder["id"])

        safe_parent_path = sanitize_path(parent_path)

        max_doc_num_per_kb = int(os.environ.get("MAX_DOC_NUM_PER_KB", "100"))
        if max_doc_num_per_kb > 0 and not AdminUser.query(user_id=user_id):
            if user_id == settings.REFERENCE_TENANT_ID or user_id in KnowledgebaseService.get_all_group_reference_tenant_ids():
                pass
            else:
                user = User.select().where(User.id == user_id).first()
                if not user or user.email != "1505114161@qq.com":
                    current_doc_count = (
                        Document.select(fn.COUNT(1))
                        .where(
                            (Document.kb_id == kb.id) & (Document.status == StatusEnum.VALID.value)
                        )
                        .scalar()
                    )
                    incoming_count = len(file_objs) if hasattr(file_objs, "__len__") else 1
                    if int(current_doc_count or 0) + int(incoming_count or 0) > max_doc_num_per_kb:
                        return [f"QUOTA: 非管理员账户每个知识库最多只能上传 {max_doc_num_per_kb} 篇文件。"], []

        err, files = [], []
        for file in file_objs:
            try:
                DocumentService.check_doc_health(kb.tenant_id, file.filename)
                from urllib.parse import unquote
                from urllib.parse import unquote

                filename = duplicate_name(DocumentService.query, name=file.filename, kb_id=kb.id)

                filetype = filename_type(filename)
                if filetype == FileType.OTHER.value:
                    raise RuntimeError("This type of file has not been supported yet!")
                # 存储到Minio的位置
                location = filename if not safe_parent_path else f"{safe_parent_path}/{filename}"
                while settings.STORAGE_IMPL.obj_exist(kb.id, location):
                    location += "_"

                blob = file.read()
                if filetype == FileType.PDF.value:
                    blob = read_potential_broken_pdf(blob)
                settings.STORAGE_IMPL.put(kb.id, location, blob)

                doc_id = get_uuid()

                img = thumbnail_img(filename, blob)
                thumbnail_location = ""
                if img is not None:
                    thumbnail_location = f"thumbnail_{doc_id}.png"
                    settings.STORAGE_IMPL.put(kb.id, thumbnail_location, img)

                doc = {
                    "id": doc_id,
                    "kb_id": kb.id,
                    "parser_id": self.get_parser(filetype, filename, kb.parser_id),
                    "pipeline_id": kb.pipeline_id,
                    "parser_config": kb.parser_config,
                    "created_by": user_id,
                    "type": filetype,
                    "name": filename,
                    "source_type": src,
                    "suffix": Path(filename).suffix.lstrip("."),
                    "location": location,
                    "size": len(blob),
                    "thumbnail": thumbnail_location,
                }
                DocumentService.insert(doc)
                # 将doc的情况复制一份到file表 位置
                FileService.add_file_from_kb(doc, kb_folder["id"], kb.tenant_id)
                files.append((doc, blob))
            except Exception as e:
                err.append(file.filename + ": " + str(e))

        return err, files

    @classmethod
    @DB.connection_context()
    def list_all_files_by_parent_id(cls, parent_id):
        try:
            files = cls.model.select().where((cls.model.parent_id == parent_id) & (cls.model.id != parent_id))
            return list(files)
        except Exception:
            logging.exception("list_by_parent_id failed")
            raise RuntimeError("Database error (list_by_parent_id)!")

    @staticmethod
    def parse_docs(file_objs, user_id):
        exe = ThreadPoolExecutor(max_workers=12)
        threads = []
        for file in file_objs:
            threads.append(exe.submit(FileService.parse, file.filename, file.read(), False))

        res = []
        for th in threads:
            res.append(th.result())

        return "\n\n".join(res)

    @staticmethod
    def parse(filename, blob, img_base64=True, tenant_id=None):
        from rag.app import audio, email, naive, picture, presentation
        from api.apps import current_user

        def dummy(prog=None, msg=""):
            pass

        FACTORY = {ParserType.PRESENTATION.value: presentation, ParserType.PICTURE.value: picture, ParserType.AUDIO.value: audio, ParserType.EMAIL.value: email}
        parser_config = {"chunk_token_num": 16096, "delimiter": "\n!?;。；！？", "layout_recognize": "Plain Text"}
        kwargs = {"lang": "English", "callback": dummy, "parser_config": parser_config, "from_page": 0, "to_page": 100000, "tenant_id": current_user.id if current_user else tenant_id}
        file_type = filename_type(filename)
        if img_base64 and file_type == FileType.VISUAL.value:
            return GptV4.image2base64(blob)
        cks = FACTORY.get(FileService.get_parser(filename_type(filename), filename, ""), naive).chunk(filename, blob, **kwargs)
        return f"\n -----------------\nFile: {filename}\nContent as following: \n" + "\n".join([ck["content_with_weight"] for ck in cks])

    @staticmethod
    def get_parser(doc_type, filename, default):
        if doc_type == FileType.VISUAL:
            return ParserType.PICTURE.value
        if doc_type == FileType.AURAL:
            return ParserType.AUDIO.value
        if re.search(r"\.(ppt|pptx|pages)$", filename):
            return ParserType.PRESENTATION.value
        if re.search(r"\.(msg|eml)$", filename):
            return ParserType.EMAIL.value
        return default

    @staticmethod
    def get_blob(user_id, location):
        bname = f"{user_id}-downloads"
        return settings.STORAGE_IMPL.get(bname, location)

    @staticmethod
    def put_blob(user_id, location, blob):
        bname = f"{user_id}-downloads"
        return settings.STORAGE_IMPL.put(bname, location, blob)

    @classmethod
    @DB.connection_context()
    def delete_docs(cls, doc_ids, tenant_id):
        root_folder = FileService.get_root_folder(tenant_id)
        pf_id = root_folder["id"]
        FileService.init_knowledgebase_docs(pf_id, tenant_id)
        errors = ""
        kb_table_num_map = {}
        for doc_id in doc_ids:
            try:
                e, doc = DocumentService.get_by_id(doc_id)
                if not e:
                    raise Exception("Document not found!")
                tenant_id = DocumentService.get_tenant_id(doc_id)
                if not tenant_id:
                    raise Exception("Tenant not found!")

                b, n = File2DocumentService.get_storage_address(doc_id=doc_id)

                TaskService.filter_delete([Task.doc_id == doc_id])
                if not DocumentService.remove_document(doc, tenant_id):
                    raise Exception("Database error (Document removal)!")

                f2d = File2DocumentService.get_by_document_id(doc_id)
                deleted_file_count = 0
                if f2d:
                    deleted_file_count = FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])

                    try:
                        if AdminUser.query(user_id=tenant_id, role_level=1):
                            FileAdminService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
                        else:
                            FileGroupService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
                            FileAdminService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
                    except Exception as e:
                        print("1、2级表文件名称未能挂载到知识库")
                File2DocumentService.delete_by_document_id(doc_id)
                if deleted_file_count > 0:
                    settings.STORAGE_IMPL.rm(b, n)

                doc_parser = doc.parser_id
                if doc_parser == ParserType.TABLE:
                    kb_id = doc.kb_id
                    if kb_id not in kb_table_num_map:
                        counts = DocumentService.count_by_kb_id(kb_id=kb_id, keywords="", run_status=[TaskStatus.DONE], types=[])
                        kb_table_num_map[kb_id] = counts
                    kb_table_num_map[kb_id] -= 1
                    if kb_table_num_map[kb_id] <= 0:
                        KnowledgebaseService.delete_field_map(kb_id)
            except Exception as e:
                errors += str(e)

        return errors

    @staticmethod
    def upload_info(user_id, file, url: str|None=None):
        def structured(filename, filetype, blob, content_type):
            nonlocal user_id
            if filetype == FileType.PDF.value:
                blob = read_potential_broken_pdf(blob)

            location = get_uuid()
            FileService.put_blob(user_id, location, blob)
            try:
                if AdminUser.query(user_id=user_id, role_level=1):
                    FileAdminService.put_blob(user_id, location, blob)
                else:
                    FileGroupService.put_blob(user_id, location, blob)
                    FileAdminService.put_blob(user_id, location, blob)
            except Exception as e:
                print("1、2级表put_blob失败啦")

            return {
                "id": location,
                "name": filename,
                "size": sys.getsizeof(blob),
                "extension": filename.split(".")[-1].lower(),
                "mime_type": content_type,
                "created_by": user_id,
                "created_at": time.time(),
                "preview_url": None
            }

        if url:
            from crawl4ai import (
                AsyncWebCrawler,
                BrowserConfig,
                CrawlerRunConfig,
                DefaultMarkdownGenerator,
                PruningContentFilter,
                CrawlResult
            )
            filename = re.sub(r"\?.*", "", url.split("/")[-1])
            async def adownload():
                browser_config = BrowserConfig(
                    headless=True,
                    verbose=False,
                )
                async with AsyncWebCrawler(config=browser_config) as crawler:
                    crawler_config = CrawlerRunConfig(
                        markdown_generator=DefaultMarkdownGenerator(
                            content_filter=PruningContentFilter()
                        ),
                        pdf=True,
                        screenshot=False
                    )
                    result: CrawlResult = await crawler.arun(
                        url=url,
                        config=crawler_config
                    )
                    return result
            page = asyncio.run(adownload())
            if page.pdf:
                if filename.split(".")[-1].lower() != "pdf":
                    filename += ".pdf"
                return structured(filename, "pdf", page.pdf, page.response_headers["content-type"])

            return structured(filename, "html", str(page.markdown).encode("utf-8"), page.response_headers["content-type"], user_id)

        DocumentService.check_doc_health(user_id, file.filename)
        return structured(file.filename, filename_type(file.filename), file.read(), file.content_type)

    @staticmethod
    def get_files(files: Union[None, list[dict]]) -> list[str]:
        if not files:
            return  []
        def image_to_base64(file):
            return "data:{};base64,{}".format(file["mime_type"],
                                        base64.b64encode(FileService.get_blob(file["created_by"], file["id"])).decode("utf-8"))
        exe = ThreadPoolExecutor(max_workers=5)
        threads = []
        for file in files:
            if file["mime_type"].find("image") >=0:
                threads.append(exe.submit(image_to_base64, file))
                continue
            threads.append(exe.submit(FileService.parse, file["name"], FileService.get_blob(file["created_by"], file["id"]), True, file["created_by"]))
        return [th.result() for th in threads]
