"""
1. 登录接口需要 login_user(user) 将用户信息写入了 Session 或上下文
2. @login_required 里判断current_user <--这通常来自 quart_login (或 flask_login) 库。你需要确保应用初始化时配置了 LoginManager。
3. current_user = LocalProxy(_load_user) 的意思是：每次你用到 current_user，系统就会立刻执行 _load_user() 这个函数。
4. _load_user() 函数内部会先去检查当前的 Session（或者 Cookie），看看里面有没有存 user_id。
5. 调用“用户加载器” (user_loader)
@login_manager.user_loader
def load_user(user_id):
    # 这里的代码才是真正干活的地方
    return User.query.get(user_id)

6.
"""

import requests
import sys
import os

# 将项目根目录加入环境变量
sys.path.insert(0, '/home/zyb/rag-flow')
from api.utils.crypt import decrypt,crypt2, crypt
"""
"ruid27024@gmail.com"
"test_a@qq.com"
"test_b@qq.com"
"test_c@qq.com"
"""


# 1. 发送登录请求
login_url = "http://localhost:9222/v1/user/login"
payload = {
    "email": "test_c@qq.com",
    "password": crypt("123456") # 假设这是明文或者已加密的密码
}

response = requests.post(login_url, json=payload)

# 2. 从响应头中获取 Token
# 注意：requests 库获取 header 时不区分大小写，但标准写法是 'Authorization'
auth_token = response.headers.get('Authorization')

if auth_token:
    print(f"✅ 获取到 Token: {auth_token}")
    
    # 3. 将 Token 放入后续请求的 Header 中
    # 通常格式是 "Bearer <token>"，但看你代码里直接存的是 uuid，
    # 如果接口校验失败，可以尝试去掉 "Bearer " 前缀，或者直接只用 token。
    headers = {
        "Authorization": auth_token 
    }
    
    # # 4. 测试调用另一个需要登录的接口 (例如获取用户信息)
    # # 假设有一个接口是 /v1/user/info
    # user_info_url = "http://localhost:9222/v1/user/info" 
    # user_response = requests.get(user_info_url, headers=headers)
    
    # print(f"用户信息接口返回: {user_response.json()}")
    url = "http://localhost:9222/v1/user_group/my_group/members/add"
    from api.db.services.user_service import UserService
    # TODO 找到工艺1组的人员进行添加
    import json
    with open('zzz/people.json', 'r', encoding='utf-8') as file:
    # 写入数据库
        data = json.load(file)
        print(data['rtnData']['result'][0])
        print(len(data['rtnData']['result']))

    for i in data['rtnData']['result']:
        if i['organize'] == "新品事业部研发部":
            phone = i.get("phone") # 使用 get 防止键不存在
            
            if not phone:
                print(f"⚠️ {i['organize']} 缺少 phone 字段")
                continue

            # 3. 安全查询用户
            lis = UserService.query_user_by_email(phone)
            
            if lis:
                user = lis[0]
                print(f"✅ 找到用户: {user.nickname} (ID: {user.id})")
                
                # 4. 构造请求
                payload = {
                    "user_id": user.id
                }
                
                # 5. 发送请求
                try:
                    resp = requests.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        print(f"   -> 添加成功: {resp.json()}")
                    else:
                        print(f"   -> 添加失败: {resp.status_code} - {resp.text}")
                except Exception as e:
                    print(f"   -> 请求异常: {e}")
            else:
                print(f"❌ 未找到手机号为 {phone} 的用户")
    
else:
    print("❌ 登录失败，未找到 Authorization 头")
    print(f"响应内容: {response.json()}")