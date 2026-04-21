import requests
import json

# 接口地址 (假设你的服务跑在本地 8080 端口)
url = "http://localhost:9222/v1/document/upload/report"

# 1. 准备请求头 (因为用了 get_json，必须告诉服务器发的是 JSON)
headers = {
    "Content-Type": "application/json",
    # 如果接口有登录验证，可能还需要加上 token
    # "Authorization": "Bearer YOUR_TOKEN_HERE" 
}

# 2. 准备 JSON 数据 (对应代码里的 json_data.get(...))
payload = {
    "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",  # 这里填一个真实的 PDF 文件链接，方便测试下载
    "dept_id": "100146",
    "user_id": "105405",
    "fileName": "test_report.pdf"
}

# 3. 发送 POST 请求
# json=payload 会自动把字典转成 JSON 字符串
response = requests.post(url, json=payload, headers=headers)

# 4. 打印结果
print(f"状态码: {response.status_code}")
print(f"返回内容: {response.text}")