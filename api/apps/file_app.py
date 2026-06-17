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
#  limitations under the License
#
import logging
import asyncio
import os
import pathlib
import re
from quart import request, make_response
from api.apps import login_required, current_user

from api.common.check_team_permission import check_file_team_permission, check_file_team_write_permission
from api.db.db_models import AdminUser
from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.group_service import GroupService
from api.db.services.user_group_service import UserGroupService
from api.utils.api_utils import server_error_response, get_data_error_result, validate_request
from common.misc_utils import get_uuid
from common.constants import RetCode, FileSource
from api.db import FileType
from api.db.services import duplicate_name
from api.db.services.file_service import FileService
from api.utils.api_utils import get_json_result, get_request_json
from api.utils.file_utils import filename_type
from api.utils.web_utils import CONTENT_TYPE_MAP
from common import settings

def allow(pf_id):
    # 1级别管理直接可以执行
    is_admin_1 = AdminUser.query(user_id=current_user.id, role_level =1)
    is_admin_2 = AdminUser.query(user_id=current_user.id, role_level =2)

    is_admin = bool(is_admin_1 or is_admin_2)
    print(f"当前是否为管理员：{is_admin}")

    # 获取当前pf_id所属的 tenant  判断是不是当前文件的所有者
    try:
        folder_tenant_id = FileService.get_tenant_id_by_parent_id(pf_id)
        is_tenant = (current_user.id == folder_tenant_id)
    except Exception as e:
        return get_data_error_result(message="Error checking folder ownership")
    
    # 组管理库tennat_id
    cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
    cfg_map_id = cfg_map.values

    # 全局库的id
    public_id = settings.REFERENCE_TENANT_ID

    if not is_admin and not is_tenant:
        return False
    
    if AdminUser.query(user_id=current_user.id, role_level = 2) and folder_tenant_id == public_id:
        return False

    return True

# 文件的上传
@manager.route('/upload', methods=['POST'])  # noqa: F821
@login_required
# @validate_request("parent_id")
async def upload():
    form = await request.form
    pf_id = form.get("parent_id")

    # 如果没有传入根接点
    if not pf_id:
        # 获取根id
        root_folder = FileService.get_root_folder(current_user.id)
        pf_id = root_folder["id"]


    # 上传权限
    if not allow(pf_id):
        return get_data_error_result(message="Error checking folder ownership")
    
    # 获取上传的文件
    files = await request.files
    if 'file' not in files:
        return get_json_result(
            data=False, message='No file part!', code=RetCode.ARGUMENT_ERROR)
    file_objs = files.getlist('file')

    for file_obj in file_objs:
        if file_obj.filename == '':
            return get_json_result(
                data=False, message='No file selected!', code=RetCode.ARGUMENT_ERROR)
    file_res = []

    try:
        e, pf_folder = FileService.get_by_id(pf_id)
        if not e:
            return get_data_error_result( message="Can't find this folder!")

        # 上传单个文件的file_obj
        async def _handle_single_file(file_obj):
            # 最大上传数量
            MAX_FILE_NUM_PER_USER: int = int(os.environ.get('MAX_FILE_NUM_PER_USER', 0))

            # 超过最大上传数量
            if 0 < MAX_FILE_NUM_PER_USER <= await asyncio.to_thread(DocumentService.get_doc_count, current_user.id):
                return get_data_error_result( message="Exceed the maximum file number of a free user!")

            # split file name path
            if not file_obj.filename:
                file_obj_names = [pf_folder.name, file_obj.filename]

            # /data/report.txt
            else:
                full_path = '/' + file_obj.filename
                file_obj_names = full_path.split('/')

            # 保证了列表长度至少为 2，逻辑更统一。
            file_len = len(file_obj_names)

            # ['', 'folderA', 'folderB', 'file.txt'] --> 目标路径。函数会拿着这个列表去数据库里一个个比对。
            # get folder 
            file_id_list = await asyncio.to_thread(FileService.get_id_list_by_id, pf_id, file_obj_names, 1, [pf_id])
            
            # 期望的路径长度 与实际存在的长度
            len_id_list = len(file_id_list)

            # create folder
            if file_len != len_id_list:
                # 1. 获取“最后一个已存在的文件夹”作为父级
                e, file = await asyncio.to_thread(FileService.get_by_id, file_id_list[len_id_list - 1])
                if not e:
                    return get_data_error_result(message="Folder not found!")
                # 以 b 为父级，创建下一个缺失的文件夹（比如 c） 递归创建
                last_folder = await asyncio.to_thread(FileService.create_folder, file, file_id_list[len_id_list - 1], file_obj_names,
                                                        len_id_list)
            # 取 -2 可能是因为 file_obj_names 的最后一项是文件名而不是文件夹，所以要把“文件的父目录”作为操作对象。    
            else:
                e, file = await asyncio.to_thread(FileService.get_by_id, file_id_list[len_id_list - 2])
                if not e:
                    return get_data_error_result(message="Folder not found!")

                last_folder = await asyncio.to_thread(FileService.create_folder, file, file_id_list[len_id_list - 2], file_obj_names,
                                                        len_id_list)

            # file type 获取文件类型
            filetype = filename_type(file_obj_names[file_len - 1])
            # 生成存储路径
            location = file_obj_names[file_len - 1]
            while await asyncio.to_thread(settings.STORAGE_IMPL.obj_exist, last_folder.id, location):
                location += "_"
            # 读取文件内容
            blob = await asyncio.to_thread(file_obj.read)
            # 处理数据库的重复命名
            filename = await asyncio.to_thread(
                duplicate_name,
                FileService.query,
                name=file_obj_names[file_len - 1],
                parent_id=last_folder.id)
            # 保存到Minio
            await asyncio.to_thread(settings.STORAGE_IMPL.put, last_folder.id, location, blob)

            file_data = {
                "id": get_uuid(),
                "parent_id": last_folder.id,
                "tenant_id": current_user.id,
                "created_by": current_user.id,
                "type": filetype,
                "name": filename,
                "location": location,
                "size": len(blob),
            }
            inserted = await asyncio.to_thread(FileService.insert, file_data)
            return inserted.to_json()

        for file_obj in file_objs:
            res = await _handle_single_file(file_obj)
            file_res.append(res)

        return get_json_result(data=file_res)
    except Exception as e:
        return server_error_response(e)

# # 通过组名称上传到对应的组内（公共组）
# @manager.route('/upload/report', methods=['POST'])
# @validate_request("dept_id", "user_id") 
# async def upload_report():
#     form = await request.form
#     dept_id = form.get("dept_id")
#     user_id = form.get("user_id")

#     # 上传 + 解析 + 入库

#     # 人员编码  + 部门编码 + pf_id

#     # name = ""
#     dept = "" + "报告"
#     # TODO: 获取这个部门的pf_id  通过组 -> 组号 -> tenant -> pf_id
#     pf_id = ""

#     # 获取上传的文件
#     files = await request.files
#     if 'file' not in files:
#         return get_json_result(
#             data=False, message='No file part!', code=RetCode.ARGUMENT_ERROR)
#     file_objs = files.getlist('file')

#     for file_obj in file_objs:
#         if file_obj.filename == '':
#             return get_json_result(
#                 data=False, message='No file selected!', code=RetCode.ARGUMENT_ERROR)
#     file_res = []

#     try:
        
#         # 上传单个文件的file_obj
#         async def _handle_single_file(file_obj):
          
#             # # split file name path
#             # if not file_obj.filename:
#             #     file_obj_names = [pf_folder.name, file_obj.filename]

#             # full_path = '/' + file_obj.filename
#             full_path = '/' + dept  + "/" + file_obj.filename
#             file_obj_names = full_path.split('/')
#             file_len = len(file_obj_names)

#             # get folder 
#             file_id_list = await asyncio.to_thread(FileService.get_id_list_by_id, pf_id, file_obj_names, 1, [pf_id])
#             len_id_list = len(file_id_list)

#             # create folder
#             if file_len != len_id_list:
#                 e, file = await asyncio.to_thread(FileService.get_by_id, file_id_list[len_id_list - 1])
#                 if not e:
#                     return get_data_error_result(message="Folder not found!")
#                 last_folder = await asyncio.to_thread(FileService.create_folder, file, file_id_list[len_id_list - 1], file_obj_names,
#                                                         len_id_list)
#             else:
#                 e, file = await asyncio.to_thread(FileService.get_by_id, file_id_list[len_id_list - 2])
#                 if not e:
#                     return get_data_error_result(message="Folder not found!")
#                 # 递归创建文件夹
#                 last_folder = await asyncio.to_thread(FileService.create_folder, file, file_id_list[len_id_list - 2], file_obj_names,
#                                                         len_id_list)

#             # file type 获取文件类型
#             filetype = filename_type(file_obj_names[file_len - 1])
#             # 生成存储路径
#             location = file_obj_names[file_len - 1]
#             while await asyncio.to_thread(settings.STORAGE_IMPL.obj_exist, last_folder.id, location):
#                 location += "_"
#             # 读取文件内容
#             blob = await asyncio.to_thread(file_obj.read)
#             # 处理数据库的重复命名
#             filename = await asyncio.to_thread(
#                 duplicate_name,
#                 FileService.query,
#                 name=file_obj_names[file_len - 1],
#                 parent_id=last_folder.id)
#             # 保存到Minio
#             await asyncio.to_thread(settings.STORAGE_IMPL.put, last_folder.id, location, blob)

#             file_data = {
#                 "id": get_uuid(),
#                 "parent_id": last_folder.id,
#                 "tenant_id": current_user.id,
#                 "created_by": current_user.id,
#                 "type": filetype,
#                 "name": filename,
#                 "location": location,
#                 "size": len(blob),
#             }
#             inserted = await asyncio.to_thread(FileService.insert, file_data)
#             return inserted.to_json()

#         for file_obj in file_objs:
#             res = await _handle_single_file(file_obj)
#             file_res.append(res)

#         return get_json_result(data=file_res)
#     except Exception as e:
#         return server_error_response(e)



@manager.route('/create', methods=['POST'])  # noqa: F821
@login_required
@validate_request("name")
async def create():
    req = await get_request_json()
    pf_id = req.get("parent_id")
    input_file_type = req.get("type")
    if not pf_id:
        root_folder = FileService.get_root_folder(current_user.id)
        pf_id = root_folder["id"]

    # 上传权限
    if not allow(pf_id):
        return get_data_error_result(message="Error checking folder ownership")

    try:
        if not FileService.is_parent_folder_exist(pf_id):
            return get_json_result(
                data=False, message="Parent Folder Doesn't Exist!", code=RetCode.OPERATING_ERROR)
        if FileService.query(name=req["name"], parent_id=pf_id):
            return get_data_error_result(
                message="Duplicated folder name in the same folder.")

        if input_file_type == FileType.FOLDER.value:
            file_type = FileType.FOLDER.value
        else:
            file_type = FileType.VIRTUAL.value

        file = FileService.insert({
            "id": get_uuid(),
            "parent_id": pf_id,
            "tenant_id": current_user.id,
            "created_by": current_user.id,
            "name": req["name"],
            "location": "",
            "size": 0,
            "type": file_type
        })

        print("---------------------------------------------------------")
        print(file.id)
        return get_json_result(data=file.to_json())
    except Exception as e:
        return server_error_response(e)


# # 文件列表查询
# @manager.route('/list', methods=['GET'])  # noqa: F821
# @login_required
# def list_files():
#     # 你想看哪个文件夹的内容
#     pf_id = request.args.get("parent_id")
#     # 是不是搜索文件
#     keywords = request.args.get("keywords", "")

#     # 页码
#     page_number = int(request.args.get("page", 1))
#     items_per_page = int(request.args.get("page_size", 15))
#     orderby = request.args.get("orderby", "create_time")
#     desc = request.args.get("desc", True)

#     # 如果用户没有指定查看哪个文件夹
#     if not pf_id:
#         # 系统默认指定当前目录的根目录
#         # todo 目前是获取当前用户的 --> 1级管理员获取所有； 二级管理员获取组内所有 --> 普通用户获取参考库 + 自己
#         print("现在开始查看文件啦啦")
#         # 如果是超级管理员 获取全部根id
#         if AdminUser.query(user_id=current_user.id, role_level=1):
#             print("当前用户是管理员，正在执行管理员逻辑...")
#             # 管理员：查询所有根目录
#             root_id_current = FileService.get_all_root_id()

#         # 如果是组管理员
#         elif AdminUser.query(user_id=current_user.id, role_level=2):
#             print("当前用户是组管理员，正在执行管理员逻辑...")
#             # 组管理员：获取自己的 + 组员的 + 组公共库的 + 全局公共库的

#             # 获取管理员创建的组
#             group_ids = GroupService.get_ids_by_created_by(current_user.id)
#             # 获取组员id
#             lis = []
#             # 组号到组公共tenant区域的映射
#             cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
#             for group_id in group_ids:
#                 print(group_id)
#                 # 获取 组的公共区域 id
#                 if group_id and group_id in cfg_map and cfg_map[group_id]:
#                     group_public_id = cfg_map[group_id]
#                     lis.append(group_public_id)
#                 ids = UserGroupService.get_member_ids_by_group_id(group_id=group_id)
#                 lis.extend(ids)
#             if settings.REFERENCE_TENANT_ID:
#                 public_id = settings.REFERENCE_TENANT_ID
#                 lis.append(public_id)

#             lis.append(current_user.id)
#             print(lis)
#             lis = list(set(lis))

#             # 获取二级管理员的根目录
#             root_id_current = FileService.get_team_root_id(lis)

        # else:
        #     lis = []
        #     # 获取组id下的公共tenant_id
        #     group_id = UserGroupService.get_group_id_by_id(current_user.id)
        #     cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        #     if group_id and group_id in cfg_map and cfg_map[group_id]:
        #         group_public_tenant_id = cfg_map[group_id]
        #         lis.append(group_public_tenant_id)

        #     if settings.REFERENCE_TENANT_ID:
        #         public_tenant_id = settings.REFERENCE_TENANT_ID
        #         lis.append(public_tenant_id)

        #     lis.append(current_user.id)
            
        #     lis = list(set(lis))  # 可以看到的租户id

        #     # 获取二级管理员的根目录
        #     root_id_current = FileService.get_team_root_id(lis)

        # # 处理每一个根id 获取下面的目录/文件
        # all_files = []
        # total = 0

        # for r_id in root_id_current:
        #     try:

        #         # 2. 获取该目录下的文件
        #         files, count = FileService.get_by_pf_id_admin(
        #             current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
        #         )

        #         # 3. 累加结果
        #         all_files.extend(files)
        #         total += count

        #     except Exception as e:
        #         # 某个用户的目录查错了不要中断整体
        #         print(f"Error fetching folder {r_id}: {e}")
        #         continue

        # print(all_files)
        # # 4. 返回汇总结果
        # root_folder = FileService.get_root_folder(current_user.id)
        # pf_id = root_folder["id"]
        # parent_folder = FileService.get_parent_folder(pf_id)
        # return get_json_result(data={"total": total, "files": all_files, "parent_folder": parent_folder.to_json()})

#     try:
#         # 先检查这个文件夹是否存在
#         e, file = FileService.get_by_id(pf_id)
#         if not e:
#             return get_data_error_result(message="Folder not found!")

#         # 核心查询 （即使你通过某种手段猜到了别人的文件夹 ID，因为这行代码的存在，数据库也会发现“这个文件夹不属于当前用户）
#         # 看某个文件夹内的内容
#         # 1级别管理直接可以执行
#         # is_admin_1 = AdminUser.query(user_id=current_user.id, role_level =1)
#         # is_admin_2 = AdminUser.query(user_id=current_user.id, role_level =2)

#         # is_admin = bool(is_admin_1 or is_admin_2)
#         # if is_admin and pf_id in FileService.get_all_root_id():
#         #     files, total = FileService.get_by_pf_id_admin(
#         #         current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

#         if AdminUser.query(user_id=current_user.id, role_level=1) and pf_id in FileService.get_all_root_id():
#             print("当前用户是管理员，正在执行管理员逻辑...")
#             # 管理员：查询所有根目录
#             root_id_current = FileService.get_all_root_id()

#             # 处理每一个根id 获取下面的目录/文件
#             all_files = []
#             total = 0

#             for r_id in root_id_current:
#                 try:

#                     # 2. 获取该目录下的文件
#                     files, count = FileService.get_by_pf_id_admin(
#                         current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
#                     )

#                     # 3. 累加结果
#                     all_files.extend(files)
#                     total += count


#                 except Exception as e:
#                     # 某个用户的目录查错了不要中断整体
#                     print(f"Error fetching folder {r_id}: {e}")

#             files = all_files

#         # 如果是组管理员
#         elif AdminUser.query(user_id=current_user.id, role_level=2) and pf_id in FileService.get_all_root_id():
#             print("当前用户是组管理员，正在执行管理员逻辑...")
#             # 组管理员：获取自己的 + 组员的 + 组公共库的 + 全局公共库的

#             # 获取管理员创建的组
#             group_ids = GroupService.get_ids_by_created_by(current_user.id)
#             # 获取组员id
#             lis = []
#             # 组号到组公共tenant区域的映射
#             cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
#             for group_id in group_ids:
#                 print(group_id)
#                 # 获取 组的公共区域 id
#                 if group_id and group_id in cfg_map and cfg_map[group_id]:
#                     group_public_id = cfg_map[group_id]
#                     lis.append(group_public_id)
#                 ids = UserGroupService.get_member_ids_by_group_id(group_id=group_id)
#                 lis.extend(ids)
#             if settings.REFERENCE_TENANT_ID:
#                 public_id = settings.REFERENCE_TENANT_ID
#                 lis.append(public_id)

#             lis.append(current_user.id)
#             print(lis)
#             lis = list(set(lis))

#             # 获取二级管理员的根目录
#             root_id_current = FileService.get_team_root_id(lis)

#             # 处理每一个根id 获取下面的目录/文件
#             all_files = []
#             total = 0

#             for r_id in root_id_current:
#                 try:

#                     # 2. 获取该目录下的文件
#                     files, count = FileService.get_by_pf_id_admin(
#                         current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
#                     )

#                     # 3. 累加结果
#                     all_files.extend(files)
#                     total += count


#                 except Exception as e:
#                     # 某个用户的目录查错了不要中断整体
#                     print(f"Error fetching folder {r_id}: {e}")

#             files = all_files



#         else:
#             files, total = FileService.get_by_pf_id(
#                 current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

#         # 获取父级信息（我的网盘 / 工作资料 / ...），让你知道自己当前在哪一层。）
#         parent_folder = FileService.get_parent_folder(pf_id)
#         if not parent_folder:
#             return get_json_result(message="File not found!")
#         print(files)

#         return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})
#     except Exception as e:
#         return server_error_response(e)

from api.db.services.file_admin_service import FileAdminService
from api.db.services.file_group_service import FileGroupService

@manager.route('/list', methods=['GET'])  # noqa: F821
@login_required
def list_files():
    pf_id = request.args.get("parent_id")

    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 1))
    items_per_page = int(request.args.get("page_size", 15))
    orderby = request.args.get("orderby", "create_time")
    desc = request.args.get("desc", True)
    # 如果没有传入pid 获取根目录的id(再通过这个id 子id) 来获取谁挂在上面
    if not pf_id:
        # 获取根的这条数据
        # 如果是超级管理员 获取全部根id
        if AdminUser.query(user_id=current_user.id, role_level=1):
            print("当前用户是管理员，正在执行管理员逻辑...")
            # 管理员：查根目录
            root_folder = FileAdminService.get_root_folder(current_user.id)
            # 根id的子id还是本身
            pf_id = root_folder["id"]
            print(f"parent_id为 {pf_id}")
            FileService.init_knowledgebase_docs(pf_id, current_user.id)



        elif AdminUser.query(user_id=current_user.id, role_level=2):
            # 管理员：查询所有根目录
            root_folder = FileGroupService.get_root_folder(current_user.id)
            # 根id的子id还是本身
            pf_id = root_folder["id"]
            print(f"parent_id为 {pf_id}")
            FileService.init_knowledgebase_docs(pf_id, current_user.id)

        else:
            lis = []
            # 获取组id下的公共tenant_id
            group_id = UserGroupService.get_group_id_by_id(current_user.id)
            cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
            if group_id and group_id in cfg_map and cfg_map[group_id]:
                group_public_tenant_id = cfg_map[group_id]
                lis.append(group_public_tenant_id)

            if settings.REFERENCE_TENANT_ID:
                public_tenant_id = settings.REFERENCE_TENANT_ID
                lis.append(public_tenant_id)

            lis.append(current_user.id)
            
            lis = list(set(lis))  # 可以看到的租户id

            # 获取二级管理员的根目录
            root_id_current = FileService.get_team_root_id(lis)

            # 处理每一个根id 获取下面的目录/文件
            all_files = []
            total = 0

            for r_id in root_id_current:
                try:

                    # 2. 获取该目录下的文件
                    files, count = FileService.get_by_pf_id_new(
                        current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
                    )

                    # 3. 累加结果
                    all_files.extend(files)
                    total += count

                except Exception as e:
                    # 某个用户的目录查错了不要中断整体
                    print(f"Error fetching folder {r_id}: {e}")
                    continue

            print(all_files)
            # 4. 返回汇总结果
            root_folder = FileService.get_root_folder(current_user.id)
            pf_id = root_folder["id"]
            parent_folder = FileService.get_parent_folder(pf_id)
            return get_json_result(data={"total": total, "files": all_files, "parent_folder": parent_folder.to_json()})

    try:
        if AdminUser.query(user_id=current_user.id, role_level=1):
            print("当前用户是管理员，正在执行管理员逻辑2...")
            
            # 获取id下面的子文件
            files, total = FileAdminService.get_by_pf_id(
                current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

            parent_folder = FileAdminService.get_parent_folder(pf_id)
            if not parent_folder:
                return get_json_result(message="File not found!")

            return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})

        elif AdminUser.query(user_id=current_user.id, role_level=2):
            print("当前用户组的管理员，正在执行管理员逻辑*******...")
            print(f"id : {pf_id}")
            # e, file = FileGroupService.get_by_id(pf_id)
            # if not e:
            #     return get_data_error_result(message="Folder not found!")
            # FileService.init_knowledgebase_docs(pf_id, current_user.id)
            files, total = FileGroupService.get_by_pf_id(
                current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

            parent_folder = FileGroupService.get_parent_folder(pf_id)
            if not parent_folder:
                return get_json_result(message="File not found!")

            return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})
        else:
            # e, file = FileService.get_by_id(pf_id)
            # if not e:
            #     return get_data_error_result(message="Folder not found!")
            # 判断是不是根pf_id

            is_root_folder = FileService.is_root_node(pf_id)
            if is_root_folder:
                lis = []
                # 获取组id下的公共tenant_id
                group_id = UserGroupService.get_group_id_by_id(current_user.id)
                cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
                if group_id and group_id in cfg_map and cfg_map[group_id]:
                    group_public_tenant_id = cfg_map[group_id]
                    lis.append(group_public_tenant_id)

                if settings.REFERENCE_TENANT_ID:
                    public_tenant_id = settings.REFERENCE_TENANT_ID
                    lis.append(public_tenant_id)

                lis.append(current_user.id)
                
                lis = list(set(lis))  # 可以看到的租户id

                # 获取二级管理员的根目录
                root_id_current = FileService.get_team_root_id(lis)

                # 处理每一个根id 获取下面的目录/文件
                all_files = []
                total = 0

                for r_id in root_id_current:
                    try:

                        # 2. 获取该目录下的文件
                        files, count = FileService.get_by_pf_id_new(
                            current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
                        )

                        # 3. 累加结果
                        all_files.extend(files)
                        total += count

                    except Exception as e:
                        # 某个用户的目录查错了不要中断整体
                        print(f"Error fetching folder {r_id}: {e}")
                        continue

                print(all_files)
                # 4. 返回汇总结果
                root_folder = FileService.get_root_folder(current_user.id)
                pf_id = root_folder["id"]
                parent_folder = FileService.get_parent_folder(pf_id)
                return get_json_result(data={"total": total, "files": all_files, "parent_folder": parent_folder.to_json()})

            else:
                files, total = FileService.get_by_pf_id_new(
                    current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

                parent_folder = FileService.get_parent_folder(pf_id)
                if not parent_folder:
                    return get_json_result(message="File not found!")

                return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})
    except Exception as e:
        return server_error_response(e)
    

@manager.route('/listp', methods=['GET'])  # noqa: F821
@login_required
def list_filesq():
    pf_id = request.args.get("parent_id")

    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 1))
    items_per_page = int(request.args.get("page_size", 15))
    orderby = request.args.get("orderby", "create_time")
    desc = request.args.get("desc", True)
    # 如果没有传入pid 获取根目录的id(再通过这个id 子id) 来获取谁挂在上面
    if not pf_id:
        # 获取根的这条数据
        # 如果是超级管理员 获取全部根id
        if AdminUser.query(user_id=current_user.id, role_level=1):
            print("当前用户是管理员，正在执行管理员逻辑...")
            # 管理员：查根目录
            root_folder = FileAdminService.get_root_folder(current_user.id)
            # 根id的子id还是本身
            pf_id = root_folder["id"]
            print(f"parent_id为 {pf_id}")
            FileService.init_knowledgebase_docs(pf_id, current_user.id)



        elif AdminUser.query(user_id=current_user.id, role_level=2):
            # 管理员：查询所有根目录
            root_folder = FileGroupService.get_root_folder(current_user.id)
            # 根id的子id还是本身
            pf_id = root_folder["id"]
            print(f"parent_id为 {pf_id}")
            FileService.init_knowledgebase_docs(pf_id, current_user.id)

        else:
            lis = []
            # 获取组id下的公共tenant_id
            group_id = UserGroupService.get_group_id_by_id(current_user.id)
            cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
            if group_id and group_id in cfg_map and cfg_map[group_id]:
                group_public_tenant_id = cfg_map[group_id]
                lis.append(group_public_tenant_id)

            if settings.REFERENCE_TENANT_ID:
                public_tenant_id = settings.REFERENCE_TENANT_ID
                lis.append(public_tenant_id)

            lis.append(current_user.id)
            
            lis = list(set(lis))  # 可以看到的租户id

            # 获取二级管理员的根目录
            root_id_current = FileService.get_team_root_id(lis)

            # 处理每一个根id 获取下面的目录/文件
            all_files = []
            total = 0

            for r_id in root_id_current:
                try:

                    # 2. 获取该目录下的文件
                    files, count = FileService.get_by_pf_id_new(
                        current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
                    )

                    # 3. 累加结果
                    all_files.extend(files)
                    total += count

                except Exception as e:
                    # 某个用户的目录查错了不要中断整体
                    print(f"Error fetching folder {r_id}: {e}")
                    continue

            print(all_files)
            # 4. 返回汇总结果
            root_folder = FileService.get_root_folder(current_user.id)
            pf_id = root_folder["id"]
            parent_folder = FileService.get_parent_folder(pf_id)
            return get_json_result(data={"total": total, "files": all_files, "parent_folder": parent_folder.to_json()})

    try:
        if AdminUser.query(user_id=current_user.id, role_level=1):
            print("当前用户是管理员，正在执行管理员逻辑2...")
            
            # 获取id下面的子文件
            files, total = FileAdminService.get_by_pf_id2(
                current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

            parent_folder = FileAdminService.get_parent_folder(pf_id)
            if not parent_folder:
                return get_json_result(message="File not found!")

            return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})

        elif AdminUser.query(user_id=current_user.id, role_level=2):
            print("当前用户组的管理员，正在执行管理员逻辑*******...")
            print(f"id : {pf_id}")
            # e, file = FileGroupService.get_by_id(pf_id)
            # if not e:
            #     return get_data_error_result(message="Folder not found!")
            # FileService.init_knowledgebase_docs(pf_id, current_user.id)
            files, total = FileGroupService.get_by_pf_id2(
                current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

            parent_folder = FileGroupService.get_parent_folder(pf_id)
            if not parent_folder:
                return get_json_result(message="File not found!")

            return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})
        else:
            # e, file = FileService.get_by_id(pf_id)
            # if not e:
            #     return get_data_error_result(message="Folder not found!")
            # 判断是不是根pf_id

            is_root_folder = FileService.is_root_node(pf_id)
            if is_root_folder:
                lis = []
                # 获取组id下的公共tenant_id
                group_id = UserGroupService.get_group_id_by_id(current_user.id)
                cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
                if group_id and group_id in cfg_map and cfg_map[group_id]:
                    group_public_tenant_id = cfg_map[group_id]
                    lis.append(group_public_tenant_id)

                if settings.REFERENCE_TENANT_ID:
                    public_tenant_id = settings.REFERENCE_TENANT_ID
                    lis.append(public_tenant_id)

                lis.append(current_user.id)
                
                lis = list(set(lis))  # 可以看到的租户id

                # 获取二级管理员的根目录
                root_id_current = FileService.get_team_root_id(lis)

                # 处理每一个根id 获取下面的目录/文件
                all_files = []
                total = 0

                for r_id in root_id_current:
                    try:

                        # 2. 获取该目录下的文件
                        files, count = FileService.get_by_pf_id_new(
                            current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
                        )

                        # 3. 累加结果
                        all_files.extend(files)
                        total += count

                    except Exception as e:
                        # 某个用户的目录查错了不要中断整体
                        print(f"Error fetching folder {r_id}: {e}")
                        continue

                print(all_files)
                # 4. 返回汇总结果
                root_folder = FileService.get_root_folder(current_user.id)
                pf_id = root_folder["id"]
                parent_folder = FileService.get_parent_folder(pf_id)
                return get_json_result(data={"total": total, "files": all_files, "parent_folder": parent_folder.to_json()})

            else:
                files, total = FileService.get_by_pf_id_new(
                    current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

                parent_folder = FileService.get_parent_folder(pf_id)
                if not parent_folder:
                    return get_json_result(message="File not found!")

                return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})
    except Exception as e:
        return server_error_response(e)
    

@manager.route('/listup', methods=['GET'])  # noqa: F821
@login_required
def list_filesUP():
    pf_id = request.args.get("parent_id")

    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 1))
    items_per_page = int(request.args.get("page_size", 15))
    orderby = request.args.get("orderby", "create_time")
    desc = request.args.get("desc", True)
    # 如果没有传入pid 获取根目录的id(再通过这个id 子id) 来获取谁挂在上面
    if not pf_id:
        # 获取根的这条数据
        # 如果是超级管理员 获取全部根id
        if AdminUser.query(user_id=current_user.id, role_level=1):
            print("当前用户是管理员，正在执行管理员逻辑...")
            # 管理员：查根目录
            root_folder = FileAdminService.get_root_folder(current_user.id)
            # 根id的子id还是本身
            pf_id = root_folder["id"]
            print(f"parent_id为 {pf_id}")
            FileService.init_knowledgebase_docs(pf_id, current_user.id)



        elif AdminUser.query(user_id=current_user.id, role_level=2):
            # 管理员：查询所有根目录
            root_folder = FileGroupService.get_root_folder(current_user.id)
            # 根id的子id还是本身
            pf_id = root_folder["id"]
            print(f"parent_id为 {pf_id}")
            FileService.init_knowledgebase_docs(pf_id, current_user.id)

        else:
            lis = []
            # 获取组id下的公共tenant_id
            group_id = UserGroupService.get_group_id_by_id(current_user.id)
            cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
            if group_id and group_id in cfg_map and cfg_map[group_id]:
                group_public_tenant_id = cfg_map[group_id]
                lis.append(group_public_tenant_id)

            if settings.REFERENCE_TENANT_ID:
                public_tenant_id = settings.REFERENCE_TENANT_ID
                lis.append(public_tenant_id)

            lis.append(current_user.id)
            
            lis = list(set(lis))  # 可以看到的租户id

            # 获取二级管理员的根目录
            root_id_current = FileService.get_team_root_id(lis)

            # 处理每一个根id 获取下面的目录/文件
            all_files = []
            total = 0

            for r_id in root_id_current:
                try:

                    # 2. 获取该目录下的文件
                    files, count = FileService.get_by_pf_id_new(
                        current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
                    )

                    # 3. 累加结果
                    all_files.extend(files)
                    total += count

                except Exception as e:
                    # 某个用户的目录查错了不要中断整体
                    print(f"Error fetching folder {r_id}: {e}")
                    continue

            print(all_files)
            # 4. 返回汇总结果
            root_folder = FileService.get_root_folder(current_user.id)
            pf_id = root_folder["id"]
            parent_folder = FileService.get_parent_folder(pf_id)
            return get_json_result(data={"total": total, "files": all_files, "parent_folder": parent_folder.to_json()})

    try:
        if AdminUser.query(user_id=current_user.id, role_level=1):
            print("当前用户是管理员，正在执行管理员逻辑2...")
            
            # 1. 获取传入文件的父ID（使用新变量名 parent_id，避免覆盖入参）
            parent_id = FileAdminService.get_parent_id(pf_id)
            
            # 2. 优雅判空：如果拿不到父ID，直接返回友好提示，避免程序崩溃
            if not parent_id:
                return get_json_result(message="文件不存在或无父级目录！")
            
            # 3. 获取父ID下面的子文件（传入 parent_id，并补全缺失的分页参数）
            files, total = FileAdminService.get_by_pf_id(
                current_user.id, parent_id, page_number, items_per_page, orderby, desc, keywords)

            # 4. 获取父文件夹的完整对象（传入 parent_id）
            parent_folder = FileAdminService.get_parent_folder(parent_id)
            if not parent_folder:
                return get_json_result(message="父文件夹不存在！")

            return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})


        elif AdminUser.query(user_id=current_user.id, role_level=2):
            print("当前用户组的管理员，正在执行管理员逻辑*******...")
            print(f"id : {pf_id}")

            # 1. 获取当前文件的父ID（使用新的变量名 parent_id，避免覆盖传入的 pf_id）
            parent_id = FileGroupService.get_parent_id(pf_id)
            
            # 2. 如果拿不到父ID，说明文件不存在或已在根目录，直接返回友好的提示信息
            if not parent_id:
                return get_json_result(message="文件不存在或无父级目录！")

            # 3. 获取父ID下面的子文件列表（注意：这里必须传入 parent_id）
            # ⚠️ 提醒：你原代码这里传的是 pf_id，且漏传了 orderby, desc, keywords 等分页参数，记得补全
            files, total = FileGroupService.get_by_pf_id(
                current_user.id, parent_id, page_number, items_per_page, orderby, desc, keywords)

            # 4. 获取父文件夹的完整对象（同样传入 parent_id）
            parent_folder = FileGroupService.get_parent_folder(parent_id)
            
            # 5. 防御性判断：如果父文件夹对象不存在，返回提示
            if not parent_folder:
                return get_json_result(message="父文件夹不存在！")

            return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})
        
        else:
            # e, file = FileService.get_by_id(pf_id)
            # if not e:
            #     return get_data_error_result(message="Folder not found!")
            # 判断是不是根pf_id
            parent_id = FileAdminService.get_parent_id(pf_id)
            if not parent_id:
                return get_json_result(message="文件不存在或无父级目录！")
            
            pf_id = parent_id

            is_root_folder = FileService.is_root_node(pf_id)
            if is_root_folder:
                lis = []
                # 获取组id下的公共tenant_id
                group_id = UserGroupService.get_group_id_by_id(current_user.id)
                cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
                if group_id and group_id in cfg_map and cfg_map[group_id]:
                    group_public_tenant_id = cfg_map[group_id]
                    lis.append(group_public_tenant_id)

                if settings.REFERENCE_TENANT_ID:
                    public_tenant_id = settings.REFERENCE_TENANT_ID
                    lis.append(public_tenant_id)

                lis.append(current_user.id)
                
                lis = list(set(lis))  # 可以看到的租户id

                # 获取二级管理员的根目录
                root_id_current = FileService.get_team_root_id(lis)

                # 处理每一个根id 获取下面的目录/文件
                all_files = []
                total = 0

                for r_id in root_id_current:
                    try:

                        # 2. 获取该目录下的文件
                        files, count = FileService.get_by_pf_id_new(
                            current_user.id, r_id, page_number, items_per_page, orderby, desc, keywords
                        )

                        # 3. 累加结果
                        all_files.extend(files)
                        total += count

                    except Exception as e:
                        # 某个用户的目录查错了不要中断整体
                        print(f"Error fetching folder {r_id}: {e}")
                        continue

                print(all_files)
                # 4. 返回汇总结果
                root_folder = FileService.get_root_folder(current_user.id)
                pf_id = root_folder["id"]
                parent_folder = FileService.get_parent_folder(pf_id)
                return get_json_result(data={"total": total, "files": all_files, "parent_folder": parent_folder.to_json()})

            else:
                files, total = FileService.get_by_pf_id_new(
                    current_user.id, pf_id, page_number, items_per_page, orderby, desc, keywords)

                parent_folder = FileService.get_parent_folder(pf_id)
                if not parent_folder:
                    return get_json_result(message="File not found!")

                return get_json_result(data={"total": total, "files": files, "parent_folder": parent_folder.to_json()})
    except Exception as e:
        return server_error_response(e)

@manager.route('/listroot', methods=['GET'])  # noqa: F821
@login_required
def list_files_root():
    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 1))
    items_per_page = int(request.args.get("page_size", 15))
    orderby = request.args.get("orderby", "create_time")
    desc = request.args.get("desc", True)
    print("开始查询根目录")

    try:
        if AdminUser.query(user_id=current_user.id, role_level=1):
            root_folder = FileAdminService.get_root_folder(current_user.id)
            pf_id = root_folder["id"]

            files, total = FileAdminService.get_root_self(
                current_user.id,
                pf_id,
                page_number,
                items_per_page,
                orderby,
                desc,
                keywords
            )

            parent_folder = FileAdminService.get_parent_folder(pf_id)
            if not parent_folder:
                return get_json_result(message="根目录不存在！")

            return get_json_result(data={
                "total": total,
                "files": files,
                "parent_folder": parent_folder.to_json()
            })

        elif AdminUser.query(user_id=current_user.id, role_level=2):
            root_folder = FileGroupService.get_root_folder(current_user.id)
            pf_id = root_folder["id"]

            files, total = FileGroupService.get_root_self(
                current_user.id,
                pf_id,
                page_number,
                items_per_page,
                orderby,
                desc,
                keywords
            )

            parent_folder = FileGroupService.get_parent_folder(pf_id)
            if not parent_folder:
                return get_json_result(message="根目录不存在！")

            return get_json_result(data={
                "total": total,
                "files": files,
                "parent_folder": parent_folder.to_json()
            })

        else:
            root_folder = FileService.get_root_folder(current_user.id)
            pf_id = root_folder["id"]

            files, total = FileService.get_root_self(
                current_user.id,
                pf_id,
                page_number,
                items_per_page,
                orderby,
                desc,
                keywords
            )

            parent_folder = FileService.get_parent_folder(pf_id)
            if not parent_folder:
                return get_json_result(message="根目录不存在！")

            return get_json_result(data={
                "total": total,
                "files": files,
                "parent_folder": parent_folder.to_json()
            })

    except Exception as e:
        return server_error_response(e)

@manager.route('/root_folder', methods=['GET'])  # noqa: F821
@login_required
def get_root_folder():
    try:
        root_folder = FileService.get_root_folder(current_user.id)
        return get_json_result(data={"root_folder": root_folder})
    except Exception as e:
        return server_error_response(e)


@manager.route('/parent_folder', methods=['GET'])  # noqa: F821
@login_required
def get_parent_folder():
    file_id = request.args.get("file_id")
    try:
        e, file = FileService.get_by_id(file_id)
        if not e:
            return get_data_error_result(message="Folder not found!")

        parent_folder = FileService.get_parent_folder(file_id)
        return get_json_result(data={"parent_folder": parent_folder.to_json()})
    except Exception as e:
        return server_error_response(e)

# todo 修改返回的文件名
@manager.route('/all_parent_folder', methods=['GET'])  # noqa: F821
@login_required
def get_all_parent_folders():
    file_id = request.args.get("file_id")

    try:
        # e, file = FileService.get_by_id(file_id)
        # if not e:
        #     return get_data_error_result(message="Folder not found!")

        parent_folders = FileService.get_all_parent_folders(file_id)

        if AdminUser.query(user_id=current_user.id, role_level=1):
            parent_folders = FileAdminService.get_all_parent_folders(file_id)
        if AdminUser.query(user_id=current_user.id, role_level=2):
            parent_folders = FileGroupService.get_all_parent_folders(file_id)

        parent_folders_res = []
        for parent_folder in parent_folders:
            parent_folders_res.append(parent_folder.to_json())
        return get_json_result(data={"parent_folders": parent_folders_res})
    except Exception as e:
        return server_error_response(e)

# 删除
@manager.route("/rm", methods=["POST"])  # noqa: F821
@login_required
@validate_request("file_ids")
async def rm():
    req = await get_request_json()
    file_ids = req["file_ids"]

    pf_id = file_ids[0]
    # 权限
    if not allow(pf_id):
        return get_data_error_result(message="暂无删除权限")

    try:
        def _delete_single_file(file):
            try:
                if file.location:
                    settings.STORAGE_IMPL.rm(file.parent_id, file.location)
            except Exception as e:
                logging.exception(f"Fail to remove object: {file.parent_id}/{file.location}, error: {e}")

            informs = File2DocumentService.get_by_file_id(file.id)
            for inform in informs:
                doc_id = inform.document_id
                e, doc = DocumentService.get_by_id(doc_id)
                if e and doc:
                    tenant_id = DocumentService.get_tenant_id(doc_id)
                    if tenant_id:
                        DocumentService.remove_document(doc, tenant_id)
                File2DocumentService.delete_by_file_id(file.id)
            print("开始删除------------------------------------------------------------")
            FileService.delete(file)
            
        def _delete_folder_recursive(folder, tenant_id):
            print("开始删除------------------------------------------------------------")
            sub_files = FileService.list_all_files_by_parent_id(folder.id)
            for sub_file in sub_files:
                if sub_file.type == FileType.FOLDER.value:
                    _delete_folder_recursive(sub_file, tenant_id)
                else:
                    _delete_single_file(sub_file)

            FileService.delete(folder)
            print(folder.id)
            try:
                # if AdminUser.query(user_id=tenant_id, role_level=1):
                #     FileAdminService.delete(folder)
                # else:
                FileGroupService.delete(folder)
                FileAdminService.delete(folder)
            except Exception as e:
                print("1、2级表知识库删除路径失败")

        def _rm_sync():
            for file_id in file_ids:
                print(file_id)
                # e, file = FileService.get_by_id(file_id)

                if AdminUser.query(user_id=current_user.id, role_level=1):
                    e, file = FileService.get_by_id(file_id)
                elif AdminUser.query(user_id=current_user.id, role_level=2):
                    e, file = FileService.get_by_id(file_id)
                else:
                    e, file = FileService.get_by_id(file_id)
                if not e or not file:
                    return get_data_error_result(message="File or Folder not found!")
                if not file.tenant_id:
                    return get_data_error_result(message="Tenant not found!")
                if not check_file_team_write_permission(file, current_user.id):
                    return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

                # if file.source_type == FileSource.KNOWLEDGEBASE:
                #     continue

                if file.type == FileType.FOLDER.value:
                    _delete_folder_recursive(file, current_user.id)
                    continue

                _delete_single_file(file)

            return get_json_result(data=True)

        return await asyncio.to_thread(_rm_sync)

    except Exception as e:
        return server_error_response(e)


@manager.route('/rename', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id", "name")
async def rename():
    req = await get_request_json()

    # 权限
    if not allow(req["file_id"]):
        return get_data_error_result(message="暂无重命名权限")
    
    try:
        # e, file = FileService.get_by_id(req["file_id"])

        if AdminUser.query(user_id=current_user.id, role_level=1):
            e, file = FileService.get_by_id(req["file_id"])
        elif AdminUser.query(user_id=current_user.id, role_level=2):
            e, file = FileService.get_by_id(req["file_id"])
        else:
            e, file = FileService.get_by_id(req["file_id"])
        if not e:
            return get_data_error_result(message="File not found!")
        if not check_file_team_write_permission(file, current_user.id):
            return get_json_result(data=False, message='No authorization.', code=RetCode.AUTHENTICATION_ERROR)
        if file.type != FileType.FOLDER.value \
            and pathlib.Path(req["name"].lower()).suffix != pathlib.Path(
                file.name.lower()).suffix:
            return get_json_result(
                data=False,
                message="The extension of file can't be changed",
                code=RetCode.ARGUMENT_ERROR)
        for file in FileService.query(name=req["name"], pf_id=file.parent_id):
            if file.name == req["name"]:
                return get_data_error_result(
                    message="Duplicated file name in the same folder.")
        
        if not FileService.update_by_id(
                req["file_id"], {"name": req["name"]}):
            return get_data_error_result(
                message="Database error (File rename)!")
        
        FileAdminService.update_by_id(
                req["file_id"], {"name": req["name"]})
        
        FileGroupService.update_by_id(
                req["file_id"], {"name": req["name"]})

        informs = File2DocumentService.get_by_file_id(req["file_id"])
        if informs:
            print("------------------------------------")
            print(informs)
            if not DocumentService.update_by_id(
                    informs[0].document_id, {"name": req["name"]}):
                return get_data_error_result(
                    message="Database error (Document rename)!")

        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route('/get/<file_id>', methods=['GET'])  # noqa: F821
@login_required
async def get(file_id):


    try:
        e, file = FileService.get_by_id(file_id)

        if not e:
            return get_data_error_result(message="Document not found!")
        if not check_file_team_permission(file, current_user.id):
            print("hello")
            return get_json_result(data=False, message='No authorization.', code=RetCode.AUTHENTICATION_ERROR)

        print(file.parent_id)
        print(file.location)
        blob = await asyncio.to_thread(settings.STORAGE_IMPL.get, file.parent_id, file.location)
        if not blob:
            b, n = File2DocumentService.get_storage_address(file_id=file_id)
            blob = await asyncio.to_thread(settings.STORAGE_IMPL.get, b, n)

        response = await make_response(blob)
        ext = re.search(r"\.([^.]+)$", file.name.lower())
        ext = ext.group(1) if ext else None
        if ext:
            if file.type == FileType.VISUAL.value:
                content_type = CONTENT_TYPE_MAP.get(ext, f"image/{ext}")
            else:
                content_type = CONTENT_TYPE_MAP.get(ext, f"application/{ext}")
            response.headers.set("Content-Type", content_type)
        return response
    except Exception as e:
        return server_error_response(e)


@manager.route("/mv", methods=["POST"])  # noqa: F821
@login_required
@validate_request("src_file_ids", "dest_file_id")
async def move():
    req = await get_request_json()
    try:
        file_ids = req["src_file_ids"]
        dest_parent_id = req["dest_file_id"]

        if not allow(dest_parent_id) or not allow(file_ids[0]):
            return get_data_error_result(message="暂无移动当前文件的权限")

        
        if AdminUser.query(user_id=current_user.id, role_level=1):
            ok, dest_folder = FileAdminService.get_by_id(dest_parent_id)
        elif AdminUser.query(user_id=current_user.id, role_level=2):
            ok, dest_folder = FileGroupService.get_by_id(dest_parent_id)
        else:
            ok, dest_folder = FileService.get_by_id(dest_parent_id)

        if not ok or not dest_folder:
            return get_data_error_result(message="Parent folder not found!")


        if AdminUser.query(user_id=current_user.id, role_level=1):
            files = FileAdminService.get_by_ids(file_ids)
        elif AdminUser.query(user_id=current_user.id, role_level=2):
            files = FileGroupService.get_by_ids(file_ids)
        else:
            files = FileService.get_by_ids(file_ids)

        if not files:
            return get_data_error_result(message="Source files not found!")

        # 将查询到的文件列表转换成字典 {文件ID: 文件对象}，方便后续通过 ID 快速查找
        files_dict = {f.id: f for f in files}

        for file_id in file_ids:
            file = files_dict.get(file_id)
            if not file:
                return get_data_error_result(message="File or folder not found!")
            if not file.tenant_id:
                return get_data_error_result(message="Tenant not found!")
            if not check_file_team_write_permission(file, current_user.id):
                return get_json_result(
                    data=False,
                    message="No authorization.",
                    code=RetCode.AUTHENTICATION_ERROR,
                )

        def _move_entry_recursive(source_file_entry, dest_folder):
            # 如果当前要移动的是一个文件夹
            if source_file_entry.type == FileType.FOLDER.value:
                # 在目标目录下，查找是否已经存在同名的文件夹
                existing_folder = FileService.query(name=source_file_entry.name, parent_id=dest_folder.id)
                if existing_folder:
                    new_folder = existing_folder[0]
                else:
                    # 不存在则在目标目录下新建一个同名文件夹（只插入数据库记录）
                    new_folder = FileService.insert(
                        {
                            "id": get_uuid(),
                            "parent_id": dest_folder.id, # 挂载到了全局参考库的根目录下了？
                            "tenant_id": source_file_entry.tenant_id,
                            "created_by": current_user.id,
                            "name": source_file_entry.name,
                            "location": "",
                            "size": 0,
                            "type": FileType.FOLDER.value,
                        }
                    )
                   
                # 查出当前文件夹下的所有子文件/子文件夹
                sub_files = FileService.list_all_files_by_parent_id(source_file_entry.id)

                # 递归调用自身，把子文件一个个搬运到新建立的文件夹里
                for sub_file in sub_files:
                    _move_entry_recursive(sub_file, new_folder)

                FileService.delete_by_id(source_file_entry.id)

                try:
                    if AdminUser.query(user_id=source_file_entry.tenant_id, role_level=1):
                        FileAdminService.delete_by_id(source_file_entry.id)
                    else:
                        FileGroupService.delete_by_id(source_file_entry.id)
                        FileAdminService.delete_by_id(source_file_entry.id)
                except Exception as e:
                    print("1、2级表知识库move复制失败")
                return

            # 如果不是文件夹，就是普通文件，开始执行物理移动
            old_parent_id = source_file_entry.parent_id # 记录文件原来的父目录ID
            old_location = source_file_entry.location   # 记录文件原来的存储路径
            filename = source_file_entry.name           # 获取文件名


            # 防重名处理：如果目标目录下已经有同名文件，就在文件名后不断加 "_" 直到不重名
            new_location = filename
            while settings.STORAGE_IMPL.obj_exist(dest_folder.id, new_location):
                new_location += "_"

            # 调用底层的存储实现（如 MinIO, OSS, 本地磁盘等），真正地把文件从旧位置剪切到新位置
            try:
                settings.STORAGE_IMPL.move(old_parent_id, old_location, dest_folder.id, new_location)
            except Exception as storage_err:
                raise RuntimeError(f"Move file failed at storage layer: {str(storage_err)}")

            # 物理移动成功后，更新主文件表（FileService）的数据库记录（更新父ID和新路径）
            FileService.update_by_id(
                source_file_entry.id,
                {
                    "parent_id": dest_folder.id,
                    "location": new_location,
                },
            )
            try:
                # 如果是1级管理员私有的内部移动 source_file_entry.id dest_folder.id 
                # 
            #     if AdminUser.query(user_id=current_user.id, role_level=1) and source_file_entry.id==dest_folder.id :
            #         FileAdminService.update_by_id(
            #     source_file_entry.id,
            #     {
            #         "parent_id": dest_folder.id,
            #         "location": new_location,
            #     },
            # )   
            #     # 如果不是管理员内部移动且和二级有关
            #     else:
                    print('hello')
                    FileGroupService.update_by_id(
                source_file_entry.id,
                {
                    "parent_id": dest_folder.id,
                    "location": new_location,
                },
            )
                    FileAdminService.update_by_id(
                source_file_entry.id,
                {
                    "parent_id": dest_folder.id,
                    "location": new_location,
                },
            )
            except Exception as e:
                    print("1、2级表更新失败")

        def _move_sync():
            for file in files:
                _move_entry_recursive(file, dest_folder)
            return get_json_result(data=True)

        return await asyncio.to_thread(_move_sync)

    except Exception as e:
        return server_error_response(e)
