import requests

url = "http://10.1.2.100:9000/hf/mdm/staffQuery/M0011"

# 直接复制上面的 JSON 数据
payload = {
    "formId": "615410e7c211c4436089bbce",
    "apiManageId": "235416243119620096",
    "page": "1",
    "pageSize": "500"
}

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic T0E6aGZvYUAxMjM=',
    'reqTime': '2025-12-01 00:00:00',
    'reqFrom': 'ERP',
    'reqld': 'test_p_20251201'
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)