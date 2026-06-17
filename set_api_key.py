# import requests
# import json
# import requests
# import sys
# import os

# # 将项目根目录加入环境变量
# sys.path.insert(0, '/home/zyb/rag-flow')
# from api.utils.crypt import decrypt,crypt2, crypt

# # ================= 1. 基础配置 =================
# BASE_URL = "http://localhost:9222/v1"  # 👈 你的后端基础地址

# # 设置模型所需的参数 (所有用户统一设置)
# LLM_FACTORY = "Tongyi-Qianwen"                 # 👈 替换为实际的 LLM 厂商名称
# API_KEY = "sk-07313e1059724edb81c1daa60584d454"            # 👈 替换为你的真实 API Key
# # BASE_MODEL_URL = ""                    # 👈 私有化部署或第三方代理的 base_url，无则留空


# # ================= 2. 核心功能函数 =================
# def login_user(phone):
#     """根据手机号模拟登录并获取 Token"""
#     login_url = f"{BASE_URL}/user/login"
#     payload = {
#         "email": phone,                # 👈 假设系统使用手机号作为 email 登录
#         "password": crypt("123456")    # 👈 确保 crypt() 函数已导入且密码正确
#     }
    
#     try:
#         resp = requests.post(login_url, json=payload)
#         if resp.status_code == 200:
#             token = resp.headers.get('Authorization')
#             return token
#     except Exception as e:
#         print(f"   ⚠️ 登录请求异常: {e}")
    
#     return None


# def set_api_key_for_user(token, phone):
#     """携带 Token 为用户设置 API Key"""
#     url = f"{BASE_URL}/llm/set_api_key"  # 👈 替换为你实际设置的接口路径，例如 /llm/set_api_key
#     headers = {"Authorization": token}
#     payload = {
#         "llm_factory": LLM_FACTORY,
#         "api_key": API_KEY,
        
#     }
    
#     try:
#         resp = requests.post(url, json=payload, headers=headers)
#         if resp.status_code == 200 and resp.json().get("code") == 0:
#             print(f"   ✅ [{phone}] API Key 设置成功！")
#         else:
#             print(f"   ❌ [{phone}] 设置失败: {resp.text}")
#     except Exception as e:
#         print(f"   ⚠️ [{phone}] 设置请求异常: {e}")


# # ================= 3. 主执行流程 =================
# if __name__ == "__main__":
#     json_path = 'zzz/people.json'
    
#     try:
#         with open(json_path, 'r', encoding='utf-8') as file:
#             data = json.load(file)
            
#         # 安全提取用户列表
#         result_list = data.get('rtnData', {}).get('result', [])
#         print(f"📊 成功读取到 {len(result_list)} 个用户，开始批量处理...\n")
        
#         for index, user in enumerate(result_list, start=1):
#             phone = user.get("phone")
#             # phone = '15765971225'
#             print(f"[{index}/{len(result_list)}] 正在处理手机号: {phone}")
            

#             if not phone:
#                 print("   ⚠️ 跳过：该条数据缺少 phone 字段\n")
#                 continue
                
#             # 步骤 A: 模拟登录
#             token = login_user(phone)
#             if not token:
#                 print(f"   ❌ [{phone}] 登录失败，跳过后续操作\n")
#                 continue
                
#             print(f"   🔑 登录成功，Token: {token[:15]}...")
            
#             # 步骤 B: 设置 API Key
#             set_api_key_for_user(token, phone)
#             print("-" * 40 + "\n")
#             # break
            
#     except FileNotFoundError:
#         print(f"❌ 错误: 找不到文件 {json_path}，请检查路径")
#     except json.JSONDecodeError:
#         print("❌ 错误: JSON 文件格式不正确")


import requests
import json
import sys
import time

# 👇 【重要】将项目根目录加入环境变量，以便导入 crypt 函数
sys.path.insert(0, '/home/zyb/rag-flow')
try:
    from api.utils.crypt import decrypt, crypt2, crypt
except ImportError:
    print("❌ 无法导入 crypt 模块，请确认 /home/zyb/rag-flow 路径是否正确！")
    sys.exit(1)

# ================= 1. 基础配置 =================
BASE_URL = "http://localhost:9222/v1"  

# 设置 API Key 所需的参数
LLM_FACTORY = "Tongyi-Qianwen"       # 👈 替换为实际的 LLM 厂商名称
API_KEY = "sk-07313e1059724edb81c1daa60584d454"          # 👈 替换为你的真实通义千问 API Key

# 设置 Tenant Info 所需的默认模型 ID (基于你提供的信息)
LLM_ID = "qwen3-32b@Tongyi-Qianwen"                 # 默认大语言模型
EMBD_ID = "text-embedding-v2@Tongyi-Qianwen"        # 默认 Embedding 模型
RERANK_ID = "gte-rerank@Tongyi-Qianwen"          # 默认 Rerank 重排模型
IMG2TXT_ID = "qwen-vl-plus@Tongyi-Qianwen"          # 默认图像转文字模型


# ================= 2. 核心功能函数 =================
def login_user(phone):
    """根据手机号模拟登录并获取 Token"""
    login_url = f"{BASE_URL}/user/login"
    payload = {
        "email": phone,                
        "password": crypt("123456")    # 👈 确保所有测试账号初始密码为 123456
    }
    
    try:
        resp = requests.post(login_url, json=payload)
        if resp.status_code == 200:
            token = resp.headers.get('Authorization')
            return token
    except Exception as e:
        print(f"   ⚠️ 登录请求异常: {e}")
    
    return None


def get_tenant_id(token):
    """通过 Token 获取当前用户的 tenant_id"""
    url = f"{BASE_URL}/user/info"      # 👈 假设获取用户信息的接口是 /user/info
    headers = {"Authorization": token}
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return data.get("id")
    except Exception as e:
        print(f"   ⚠️ 获取 tenant_id 异常: {e}")
    return None


def set_api_key_for_user(token, phone):
    """携带 Token 为用户设置 API Key"""
    url = f"{BASE_URL}/llm/set_api_key"  
    headers = {"Authorization": token}
    payload = {
        "llm_factory": LLM_FACTORY,
        "api_key": API_KEY,
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            print(f"   ✅ [{phone}] API Key 设置成功！")
            return True
        else:
            print(f"   ❌ [{phone}] API Key 设置失败: {resp.text}")
            return False
    except Exception as e:
        print(f"   ⚠️ [{phone}] API Key 请求异常: {e}")
        return False


def set_tenant_info(token, phone, tenant_id):
    """携带 Token 为用户配置租户级别的默认模型"""
    url = f"{BASE_URL}/user/set_tenant_info"  
    headers = {"Authorization": token}
    payload = {
        "tenant_id": tenant_id,         # 必须包含 tenant_id
        "llm_id": LLM_ID,               # 大语言模型
        "embd_id": EMBD_ID,             # Embedding 模型
        "asr_id": "",                   # ASR 语音识别 (如无则传空字符串)
        "img2txt_id": IMG2TXT_ID        # 图像转文字模型
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 200 and resp.json().get("code") == 0:
            print(f"   ✅ [{phone}] Tenant Info 设置成功！")
        else:
            print(f"   ❌ [{phone}] Tenant Info 设置失败: {resp.text}")
    except Exception as e:
        print(f"   ⚠️ [{phone}] Tenant Info 请求异常: {e}")


# ================= 3. 主执行流程 =================
if __name__ == "__main__":
    json_path = 'zzz/people.json'
    
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        result_list = data.get('rtnData', {}).get('result', [])
        print(f"📊 成功读取到 {len(result_list)} 个用户，开始批量处理...\n")
        
        # 从第 100 个元素开始截取（索引为99），并且让进度号从 100 开始显示
        for index, user in enumerate(result_list[99:], start=100):
            phone = user.get("phone")
            print(f"[{index}/{len(result_list)}] 正在处理手机号: {phone}")

            if not phone:
                print("   ⚠️ 跳过：该条数据缺少 phone 字段\n")
                continue
                
            # 步骤 A: 模拟登录
            token = login_user(phone)
            if not token:
                print(f"   ❌ [{phone}] 登录失败，跳过后续操作\n")
                continue
                
            print(f"   🔑 登录成功，Token: {token[:15]}...")
            
            # 步骤 B: 设置 API Key
            api_key_success = set_api_key_for_user(token, phone)
            
            # 步骤 C: 如果 API Key 设置成功，则继续设置 Tenant Info
            if api_key_success:
                tenant_id = get_tenant_id(token)
                if tenant_id:
                    set_tenant_info(token, phone, tenant_id)
                else:
                    print(f"   ❌ [{phone}] 未获取到 tenant_id，跳过 Tenant 配置")

            print("-" * 40 + "\n")
            # time.sleep(0.2)  # 每次请求间隔 0.2 秒，防止并发过高打挂服务器
            
    except FileNotFoundError:
        print(f"❌ 错误: 找不到文件 {json_path}，请检查路径")
    except json.JSONDecodeError:
        print("❌ 错误: JSON 文件格式不正确")