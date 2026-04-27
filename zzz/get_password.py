import requests
import sys
import os

# 将项目根目录加入环境变量
sys.path.insert(0, '/home/zyb/rag-flow')
from api.db.services.user_service import UserService
lis = UserService.query_user_by_email("test_a@qq.com")
user =lis[0]
password = user.password
print(password)

from api.utils.crypt import decrypt,crypt2, crypt
import requests

# 1. 接口地址
url = "http://localhost:9222/v1/user/forget/reset-password"

# 2. 准备数据
# 这里填入刚才生成的加密密码
encrypted_password_string = crypt("123456")
UserService.update_user_password(user.id, decrypt(encrypted_password_string))
# payload = {
#     "email": "test_a@qq.com",
#     "new_password": encrypted_password_string,
#     "confirm_new_password": encrypted_password_string # 两次密码必须一致
# }

# # 3. 请求头 (必须带上 Token，否则可能被拦截)
# headers = {
#     "Content-Type": "application/json",
#     # 如果你有管理员 Token，填在这里
#     # "Authorization": "Bearer <YOUR_ADMIN_TOKEN>" 
# }

# # 4. 发送请求
# print(f"正在重置 {payload['email']} 的密码...")
# response = requests.post(url, json=payload, headers=headers)

# # 5. 处理结果
# if response.status_code == 200:
#     res_data = response.json()
#     if res_data.get('code') == 0: # 假设 0 是成功
#         print("✅ 密码重置成功！")
#         print(f"ℹ️ 返回信息: {res_data.get('message')}")
#         # 如果成功，这里会返回新的 Token
#         # print(f"新 Token: {res_data.get('data').get('token')}")
#     else:
#         print(f"❌ 业务错误: {res_data.get('message')}")
#         # 如果提示 "email not verified"，说明 Redis 校验没过
# else:
#     print(f"❌ 系统错误: {response.status_code} - {response.text}")

