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

from quart import request
from api.db.services import duplicate_name
from api.db.services.dialog_service import DialogService
from common.constants import StatusEnum
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_service import TenantService, UserTenantService
from api.db.db_models import AdminUser
from api.utils.api_utils import get_data_error_result, get_json_result, get_request_json, server_error_response, validate_request
from common.misc_utils import get_uuid
from common.constants import RetCode
from api.apps import login_required, current_user
import os
import json
from common.file_utils import get_project_base_directory

def check_admin(user):
    admin_user = AdminUser.query(user_id=user.id, role_level=1)
    if not admin_user:
        return get_json_result(
            data=False, message='Only admin users can perform this action.', code=RetCode.OPERATING_ERROR
        )
    return None

@manager.route('/admin/config/get', methods=['GET'])  # noqa: F821
@login_required
def get_dialog_config():
    error_response = check_admin(current_user)
    if error_response:
        return error_response
        
    try:
        base_dir = get_project_base_directory()
        conf_path = os.path.join(base_dir, 'conf', 'dialog_config.json')
        
        if not os.path.exists(conf_path):
            return get_json_result(data={})
            
        with open(conf_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return get_json_result(data=config)
    except Exception as e:
        return server_error_response(e)

@manager.route('/admin/config/set', methods=['POST'])  # noqa: F821
@login_required
async def set_dialog_config():
    error_response = check_admin(current_user)
    if error_response:
        return error_response

    try:
        req = await get_request_json()
        base_dir = get_project_base_directory()
        conf_dir = os.path.join(base_dir, 'conf')
        conf_path = os.path.join(conf_dir, 'dialog_config.json')
        
        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir)
            
        with open(conf_path, 'w', encoding='utf-8') as f:
            json.dump(req, f, ensure_ascii=False, indent=4)
            
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

@manager.route('/set', methods=['POST'])  # noqa: F821
@validate_request("prompt_config")
@login_required
async def set_dialog():
    req = await get_request_json()
    # 👇 在这里添加打印
    print("======================================")
    print("🚀 前端发来的请求数据 (req):", req)
    print("======================================")
    dialog_id = req.get("dialog_id", "")
    is_create = not dialog_id
    name = req.get("name", "New Dialog")
    if not isinstance(name, str):
        return get_data_error_result(message="Dialog name must be string.")
    if name.strip() == "":
        return get_data_error_result(message="Dialog name can't be empty.")
    if len(name.encode("utf-8")) > 255:
        return get_data_error_result(message=f"Dialog name length is {len(name)} which is larger than 255")

    if is_create and DialogService.query(tenant_id=current_user.id, name=name.strip()):
        name = name.strip()
        name = duplicate_name(
            DialogService.query,
            name=name,
            tenant_id=current_user.id,
            status=StatusEnum.VALID.value)

    description = req.get("description", "A helpful dialog")
    icon = req.get("icon", "")
    top_n = req.get("top_n", 6)
    top_k = req.get("top_k", 1024)
    rerank_id = req.get("rerank_id", "")
    if not rerank_id:
        req["rerank_id"] = ""
    similarity_threshold = req.get("similarity_threshold", 0.1)
    vector_similarity_weight = req.get("vector_similarity_weight", 0.3)
    llm_setting = req.get("llm_setting", {})
    meta_data_filter = req.get("meta_data_filter", {})
    prompt_config = req["prompt_config"]

    if not is_create:
        if not req.get("kb_ids", []) and not prompt_config.get("tavily_api_key") and "{knowledge}" in prompt_config['system']:
            # return get_data_error_result(message="请先在左上方选择您的知识库再进行问答")
            pass

        for p in prompt_config["parameters"]:
            if p["optional"]:
                continue
            if prompt_config["system"].find("{%s}" % p["key"]) < 0:
                return get_data_error_result(
                    message="Parameter '{}' is not used".format(p["key"]))

    try:
        e, tenant = TenantService.get_by_id(current_user.id)
        if not e:
            return get_data_error_result(message="Tenant not found!")
        kbs = KnowledgebaseService.get_by_ids(req.get("kb_ids", []))
        embd_ids = [TenantLLMService.split_model_name_and_factory(kb.embd_id)[0] for kb in kbs]  # remove vendor suffix for comparison
        embd_count = len(set(embd_ids))
        if embd_count > 1:
            return get_data_error_result(message=f'Datasets use different embedding models: {[kb.embd_id for kb in kbs]}"')

        llm_id = req.get("llm_id", tenant.llm_id)
        if not dialog_id:
            dia = {
                "id": get_uuid(),
                "tenant_id": current_user.id,
                "name": name,
                "kb_ids": req.get("kb_ids", []),
                "description": description,
                "llm_id": llm_id,
                "llm_setting": llm_setting,
                "prompt_config": prompt_config,
                "meta_data_filter": meta_data_filter,
                "top_n": top_n,
                "top_k": top_k,
                "rerank_id": rerank_id,
                "similarity_threshold": similarity_threshold,
                "vector_similarity_weight": vector_similarity_weight,
                "icon": icon
            }
            if not DialogService.save(**dia):
                return get_data_error_result(message="Fail to new a dialog!")
            return get_json_result(data=dia)
        else:
            del req["dialog_id"]
            if "kb_names" in req:
                del req["kb_names"]
            if not DialogService.update_by_id(dialog_id, req):
                return get_data_error_result(message="Dialog not found!")
            e, dia = DialogService.get_by_id(dialog_id)
            if not e:
                return get_data_error_result(message="Fail to update a dialog!")
            dia = dia.to_dict()
            dia.update(req)
            dia["kb_ids"], dia["kb_names"] = get_kb_names(dia["kb_ids"])
            return get_json_result(data=dia)
    except Exception as e:
        return server_error_response(e)
    

# 前端只能更改知识库版本
@manager.route('/set_by_config', methods=['POST'])  # noqa: F821
# @validate_request("prompt_config")
@login_required
async def set_dialog_by_config():
    req = await get_request_json()
    # 👇 在这里添加打印
    print("======================================")
    print("hello")
    print("🚀 前端发来的请求数据 (req):", req)
    print("======================================")
    dialog_id = req.get("dialog_id", "")
    is_create = not dialog_id
    name = req.get("name", "New Dialog")

    if not isinstance(name, str):
        return get_data_error_result(message="Dialog name must be string.")
    if name.strip() == "":
        return get_data_error_result(message="Dialog name can't be empty.")
    if len(name.encode("utf-8")) > 255:
        return get_data_error_result(message=f"Dialog name length is {len(name)} which is larger than 255")

    # 重名了
    if is_create and DialogService.query(tenant_id=current_user.id, name=name.strip()):
        name = name.strip()
        # 生成一个不重复的名字
        name = duplicate_name(
            DialogService.query,
            name=name,
            tenant_id=current_user.id,
            status=StatusEnum.VALID.value)

    CONFIG_FILE_PATH = '/home/zyb/rag-flow/api/apps/dialog_3.json'
    # 忽略req直接从配置文件加载相关参数
    from quart import request, jsonify
    import json
    import os
    if not os.path.exists(CONFIG_FILE_PATH):
        return jsonify({"msg": "Config file not found", "retcode": 404}), 404

    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    description = req.get("description", "")
    icon = req.get("icon", config_data.get("icon", ""))

    top_n = config_data.get("top_n", 6)
    top_k = config_data.get("top_k", 1024)
    rerank_id = req.get("rerank_id", config_data.get("rerank_id", ""))

    # if not rerank_id:
    #     req["rerank_id"] = ""

    similarity_threshold = config_data.get("similarity_threshold", 0.1)
    vector_similarity_weight = config_data.get("vector_similarity_weight", 0.3)
    llm_setting = config_data.get("llm_setting", {})

    meta_data_filter = config_data.get("meta_data_filter", {})
    prompt_config = config_data.get("prompt_config", {})

    prompt_config["prologue"] = req.get("prompt_config", {}).get("prologue", prompt_config.get("prologue", ""))
    prompt_config["empty_response"] = req.get("prompt_config", {}).get("empty_response", prompt_config.get("empty_response", ""))

    # 如果不是新建
    if not is_create:
        # 检查“知识”来源是否已配置
        if not req.get("kb_ids", []) and not prompt_config.get("tavily_api_key") and "{knowledge}" in prompt_config['system']:
            # return get_data_error_result(message="Please remove `{knowledge}` in system prompt since no dataset / Tavily used here.")
            pass

        # 确认一边必填参数
        for p in prompt_config["parameters"]:
            if p["optional"]:
                continue
            if prompt_config["system"].find("{%s}" % p["key"]) < 0:
                return get_data_error_result(
                    message="Parameter '{}' is not used".format(p["key"]))

    try:
        e, tenant = TenantService.get_by_id(current_user.id)
        if not e:
            return get_data_error_result(message="Tenant not found!")


        kbs = KnowledgebaseService.get_by_ids(req.get("kb_ids", []))

        # // 判断embedding模型
        embd_ids = [TenantLLMService.split_model_name_and_factory(kb.embd_id)[0] for kb in kbs]  # remove vendor suffix for comparison
        embd_count = len(set(embd_ids))
        if embd_count > 1:
            return get_data_error_result(message=f'Datasets use different embedding models: {[kb.embd_id for kb in kbs]}"')

        # llm_id = config_data.get("llm_id", tenant.llm_id)
        llm_id = req.get("llm_id", "")

        if not dialog_id:
            dia = {
                "id": get_uuid(),
                "tenant_id": current_user.id,
                "name": name,
                "kb_ids": req.get("kb_ids", []), # 允许用户选择知识库
                "description": description,
                "llm_id": llm_id,
                "llm_setting": llm_setting,
                "prompt_config": prompt_config,
                "meta_data_filter": meta_data_filter,
                "top_n": top_n,
                "top_k": top_k,
                "rerank_id": rerank_id,
                "similarity_threshold": similarity_threshold,
                "vector_similarity_weight": vector_similarity_weight,
                "icon": icon,
                "language": config_data.get("language", "Chinese"),
                "do_refer": config_data.get("do_refer", "1"),
                "prompt_type": config_data.get("prompt_type", "simple"),
            }
            if not DialogService.save(**dia):
                return get_data_error_result(message="Fail to new a dialog!")
            return get_json_result(data=dia)

        else:
            del req["dialog_id"]
            if "kb_names" in req:
                del req["kb_names"]

            update_data = {
                "name": name,
                "kb_ids": req.get("kb_ids", []),  # 只使用前端传来的知识库ID
                "description": description,
                "llm_id": llm_id, 
                "llm_setting": llm_setting,  # 从配置文件
                "prompt_config": prompt_config,  # 从配置文件
                "meta_data_filter": meta_data_filter,  # 从配置文件
                "top_n": top_n,  # 从配置文件
                "top_k": top_k,  # 从配置文件
                "rerank_id": rerank_id,  # 从配置文件
                "similarity_threshold": similarity_threshold,  # 从配置文件
                "vector_similarity_weight": vector_similarity_weight,  # 从配置文件
                "icon": icon,  # 从配置文件
                "language": config_data.get("language", "Chinese"),  # 从配置文件
                "do_refer": config_data.get("do_refer", "1"),  # 从配置文件
                "prompt_type": config_data.get("prompt_type", "simple"),  # 从配置文件
            }

            if not DialogService.update_by_id(dialog_id, update_data):
                return get_data_error_result(message="Dialog not found!")

            e, dia = DialogService.get_by_id(dialog_id)
            if not e:
                return get_data_error_result(message="Fail to update a dialog!")

            # 原始的配置
            dia = dia.to_dict()
            print("----------------------------------")
            print(dia)
            # 只更新kb_ids
            kb_ids_req = req.get("kb_ids", [])

            # 【关键修复】确保 kb_ids 是列表
            if isinstance(kb_ids_req, str):
                try:
                    # 如果是字符串，尝试解析 JSON
                    import json
                    kb_ids_req = json.loads(kb_ids_req)
                except:
                    # 解析失败则设为空列表
                    kb_ids_req = []

            if isinstance(dia.get("llm_setting"), str):
                try:
                    dia["llm_setting"] = json.loads(dia["llm_setting"])
                except json.JSONDecodeError:
                    dia["llm_setting"] = {}

            if isinstance(dia.get("meta_data_filter"), str):
                try:
                    dia["meta_data_filter"] = json.loads(dia["meta_data_filter"])
                except:
                    # 根据你的 defaultValues，默认应该是 { method: DatasetMetadata.Disabled, manual: [] }
                    # 或者简单的空字典/空列表，视你的前端逻辑而定
                    dia["meta_data_filter"] = {"method": "disabled", "manual": []}

            dia["description"] = description
            # 赋值
            dia["kb_ids"] = kb_ids_req

            dia["kb_ids"], dia["kb_names"] = get_kb_names(dia["kb_ids"])

            print(f"返回结果：{dia}")
            return get_json_result(data=dia)
    except Exception as e:
        return server_error_response(e)


@manager.route('/get', methods=['GET'])  # noqa: F821
@login_required
def get():
    dialog_id = request.args["dialog_id"]
    try:
        e, dia = DialogService.get_by_id(dialog_id)
        if not e:
            return get_data_error_result(message="Dialog not found!")
        dia = dia.to_dict()
        dia["kb_ids"], dia["kb_names"] = get_kb_names(dia["kb_ids"])
        return get_json_result(data=dia)
    except Exception as e:
        return server_error_response(e)


def get_kb_names(kb_ids):
    ids, nms = [], []
    for kid in kb_ids:
        e, kb = KnowledgebaseService.get_by_id(kid)
        if not e or kb.status != StatusEnum.VALID.value:
            continue
        ids.append(kid)
        nms.append(kb.name)
    return ids, nms


@manager.route('/list', methods=['GET'])  # noqa: F821
@login_required
def list_dialogs():
    try:
        conversations = DialogService.query(
            tenant_id=current_user.id,
            status=StatusEnum.VALID.value,
            reverse=True,
            order_by=DialogService.model.create_time)
        conversations = [d.to_dict() for d in conversations]
        for conversation in conversations:
            conversation["kb_ids"], conversation["kb_names"] = get_kb_names(conversation["kb_ids"])
        return get_json_result(data=conversations)
    except Exception as e:
        return server_error_response(e)


@manager.route('/next', methods=['POST'])  # noqa: F821
@login_required
async def list_dialogs_next():
    args = request.args
    keywords = args.get("keywords", "")
    page_number = int(args.get("page", 0))
    items_per_page = int(args.get("page_size", 0))
    parser_id = args.get("parser_id")
    orderby = args.get("orderby", "create_time")
    if args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True

    req = await get_request_json()
    owner_ids = req.get("owner_ids", [])
    try:
        if not owner_ids:
            # tenants = TenantService.get_joined_tenants_by_user_id(current_user.id)
            # tenants = [tenant["tenant_id"] for tenant in tenants]
            tenants = [] # keep it here
            dialogs, total = DialogService.get_by_tenant_ids(
                tenants, current_user.id, page_number,
                items_per_page, orderby, desc, keywords, parser_id)
        else:
            tenants = owner_ids
            dialogs, total = DialogService.get_by_tenant_ids(
                tenants, current_user.id, 0,
                0, orderby, desc, keywords, parser_id)
            dialogs = [dialog for dialog in dialogs if dialog["tenant_id"] in tenants]
            total = len(dialogs)
            if page_number and items_per_page:
                dialogs = dialogs[(page_number-1)*items_per_page:page_number*items_per_page]
        return get_json_result(data={"dialogs": dialogs, "total": total})
    except Exception as e:
        return server_error_response(e)


@manager.route('/rm', methods=['POST'])  # noqa: F821
@login_required
@validate_request("dialog_ids")
async def rm():
    req = await get_request_json()
    dialog_list=[]
    tenants = UserTenantService.query(user_id=current_user.id)
    try:
        for id in req["dialog_ids"]:
            for tenant in tenants:
                if DialogService.query(tenant_id=tenant.tenant_id, id=id):
                    break
            else:
                return get_json_result(
                    data=False, message='Only owner of dialog authorized for this operation.',
                    code=RetCode.OPERATING_ERROR)
            dialog_list.append({"id": id,"status":StatusEnum.INVALID.value})
        DialogService.update_many_by_id(dialog_list)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)
