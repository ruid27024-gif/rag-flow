from quart import request, jsonify
import json
import os
from api.db.services.dialog_service import DialogService
from api.db.services.user_service import UserTenantService
from api.db import UserTenantRole
from api.apps import current_user, login_required
from common.misc_utils import get_uuid

# debug_app = Blueprint('debug_app', __name__, url_prefix='/debug')

# CONFIG_FILE_PATH = '/home/hit802/RAG1/dialog_3ad8d622f11511f0ad4410ffe02ab235.json'
# CONFIG_FILE_PATH = r'C:\Users\28023\Desktop\rag-flow\api\apps\dialog_3.json'
CONFIG_FILE_PATH = 'conf/dialog_3ad8d622f11511f0ad4410ffe02ab235.json'

@manager.route('/config', methods=['GET'])  # noqa: F821
async def get_config():
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            return jsonify({"error": "Config file not found"}), 404
        
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({"data": data, "retcode": 0, "msg": "success"})
    except Exception as e:
        return jsonify({"error": str(e), "retcode": 500}), 500

@manager.route('/config', methods=['POST'])  # noqa: F821
async def update_config():
    try:
        data = await request.get_json()
        
        # Ensure directory exists (though file should exist based on task)
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return jsonify({"retcode": 0, "msg": "success"})
    except Exception as e:
        return jsonify({"error": str(e), "retcode": 500}), 500

@manager.route('/create_dialog_from_config', methods=['POST'])  # noqa: F821
@login_required
async def create_dialog_from_config():
    try:
        from api.db.services.dialog_service import DialogService
        from api.db.services.user_service import UserTenantService
        from api.db import UserTenantRole
        from api.apps import current_user
        from common.misc_utils import get_uuid
        from common.constants import StatusEnum

        # CONFIG_FILE_PATH = '/home/zyb/rag-flow/api/apps/dialog_3.json'
        # 1. Read config file
        if not os.path.exists(CONFIG_FILE_PATH):
            return jsonify({"msg": "Config file not found", "retcode": 404}), 404
        
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # 2. Find tenant_id for current_user where role is owner
        # Ensure current_user.id is available
        if not current_user or not current_user.id:
             return jsonify({"msg": "User not authenticated", "retcode": 401}), 401

        user_tenants = UserTenantService.query(user_id=current_user.id, role=UserTenantRole.OWNER)
        if not user_tenants:
            return jsonify({"msg": "No tenant found for the current user with owner role", "retcode": 404}), 404
        
        # Assuming the first one is the target tenant
        tenant_id = user_tenants[0].tenant_id

        # 3. Parse and Construct Dialog data (moved before check)
        keys_to_parse = ['kb_ids', 'prompt_config', 'llm_setting', 'meta_data_filter']
        for key in keys_to_parse:
            if key in config_data and isinstance(config_data[key], str):
                try:
                    config_data[key] = json.loads(config_data[key])
                except Exception as e:
                    print(f"Error parsing {key}: {e}")
                    pass

        new_dialog_data = {
            "tenant_id": tenant_id,
            "name": config_data.get("name", "New Configured Dialog"),
            "description": config_data.get("description", ""),
            "icon": config_data.get("icon", ""),
            "language": config_data.get("language", "Chinese"),
            "llm_id": config_data.get("llm_id", ""),
            "llm_setting": config_data.get("llm_setting", {}),
            "prompt_config": config_data.get("prompt_config", {}),
            "kb_ids": config_data.get("kb_ids", []),
            "meta_data_filter": config_data.get("meta_data_filter", {}),
            "top_n": config_data.get("top_n", 6),
            "top_k": config_data.get("top_k", 1024),
            "rerank_id": config_data.get("rerank_id", ""),
            "similarity_threshold": config_data.get("similarity_threshold", 0.1),
            "vector_similarity_weight": config_data.get("vector_similarity_weight", 0.3),
            "do_refer": config_data.get("do_refer", "1"),
            "prompt_type": config_data.get("prompt_type", "simple"),
            "status": "1"
        }

        print(new_dialog_data)

        # 2.5 Check if dialog with same name exists
        existing_dialogs = DialogService.query(tenant_id=tenant_id, name=new_dialog_data["name"], status=StatusEnum.VALID.value)
        if existing_dialogs:
            dialog = existing_dialogs[0]
            
            # Prepare update data
            update_data = new_dialog_data.copy()
            # Exclude fields that should not be overwritten
            update_data.pop("kb_ids", None)
            update_data.pop("status", None)
            update_data.pop("tenant_id", None)
            
            # Check for changes
            needs_update = False
            for key, value in update_data.items():
                current_value = getattr(dialog, key)
                if current_value != value:
                    needs_update = True
                    break
            
            if needs_update:
                DialogService.update_by_id(dialog.id, update_data)
                return jsonify({
                    "retcode": 0, 
                    "msg": f"对话 '{new_dialog_data['name']}' 已存在，配置已更新 (KB保留)", 
                    "data": {"id": dialog.id}
                })
            else:
                return jsonify({
                    "retcode": 0, 
                    "msg": f"对话 '{new_dialog_data['name']}' 已存在，配置无变化", 
                    "data": {"id": dialog.id}
                })

        # 4. Save to DB (Create new)
        new_dialog_data["id"] = get_uuid()
        DialogService.save(**new_dialog_data)

        return jsonify({"retcode": 0, "msg": "success", "data": {"id": new_dialog_data["id"]}})

    except Exception as e:
        import traceback
        traceback.print_exc() # Print to server logs
        return jsonify({"msg": f"Server Error: {str(e)}", "retcode": 500}), 500
