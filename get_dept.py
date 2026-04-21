import requests
import json

# 1. 定义请求地址 (从截图中获取)
url = "http://10.1.2.100:9000/hf/mdm/organizeQuery/M0012"

# 2. 定义请求头 (Headers)
# 包含了你截图中的自定义字段 reqTime 和 regFrom
headers = {
    "Content-Type": "application/json",  # 因为是发送 raw JSON 数据，必须包含这个
    "Authorization": "Basic T0E6aGZvYUAxMjM=",
    "reqTime": "2025-12-0100:00:00",     # 截图中的自定义头
    "regFrom": "ERP" ,                    # 截图中的自定义头
    "reqld": "test_p_20251201"
}

# 3. 定义请求体 (Body)
# 对应截图中的 JSON 数据
payload = {
    "formId": "61837cb06ee63d1cd2a0e816",
    "apiManageId": "244107895900241920",
    "page": "1",
    "pageSize": "500"
}

# 4. 发送 POST 请求
try:
    response = requests.post(url, headers=headers, json=payload)

    # 5. 处理响应
    # 检查状态码是否为 200
    if response.status_code == 200:
        print("✅ 请求成功！")
        # 尝试以 JSON 格式打印返回结果 (如果返回的是 JSON)
        try:
            # print(json.dumps(response.json(), indent=4, ensure_ascii=False))
            result = response.json()
            res = result["rtnData"]["result"]
            print(res)

        except ValueError:
            # 如果返回的不是 JSON，直接打印文本
            print(response.text)
    else:
        print(f"❌ 请求失败，状态码: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ 发生错误: {e}")