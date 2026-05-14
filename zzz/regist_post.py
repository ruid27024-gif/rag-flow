import requests
import json

# 配置 API 地址
BASE_URL = "http://localhost:9222/v1/user"
REGISTER_ENDPOINT = f"{BASE_URL}/register"


def register_user(nickname, email, password):
    """
    发送注册请求
    """
    # 准备请求头，声明内容类型为 JSON
    headers = {
        "Content-Type": "application/json"
    }

    # 准备请求体数据
    payload = {
        "nickname": nickname,
        "email": email,
        "password": password
    }

    print(f"正在向 {REGISTER_ENDPOINT} 发送注册请求...")
    print(f"数据: {json.dumps(payload)}")

    try:
        # 发送 POST 请求
        response = requests.post(REGISTER_ENDPOINT, json=payload, headers=headers)

        # 打印响应结果
        print(f"\n状态码: {response.status_code}")
        print(f"响应内容: {response.json()}")

        if response.status_code == 200:
            print("\n✅ 注册成功！")
        else:
            print("\n❌ 注册失败，请检查错误信息。")

    except Exception as e:
        print(f"发生异常: {e}")


if __name__ == "__main__":
    import sys
    import os

    # 将项目根目录加入环境变量
    sys.path.insert(0, '/home/hengyue/rag-flow')
    from api.utils.crypt import decrypt,crypt2, crypt
        # 在这里修改你要注册的账号信息
    # user_data = {
    #     "nickname": "TestUser",
    #     "email": "13844210569",
    #     "password": crypt("123456")
    # }

    with open('zzz/people.json', 'r', encoding='utf-8') as file:
        # 写入数据库
        data = json.load(file)
        print(data['rtnData']['result'][0])
        print(len(data['rtnData']['result']))

    for i in data['rtnData']['result']:
        user_data = {
            "nickname": i["mdmName"],
            "email": i["phone"],
            "password": crypt("123456")
        }

        register_user(**user_data)

