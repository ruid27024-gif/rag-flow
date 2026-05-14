import requests

# 1. 设置 URL
url = "http://localhost:9222/v1/document/upload/report"

# 100146  100147  100148

# 2. 准备表单数据
data = {
    "dept_id": "100051",
    "user_id": "105405",
    "file_name2": "12345.pdf"
}

# 3. 准备文件 (注意使用 'rb' 二进制读取模式)
# 这里的 key 'file' 必须和后端代码里获取的一致
files = [
    ('file', ('我的文档.pdf', open('/home/hengyue/文档/xwechat_files/wxid_0n7eboddvh9u22_76fc/msg/file/2026-05/Untitled.pdf', 'rb'), 'application/pdf')),
    ('file', ('report2.pdf', open('/home/hengyue/文档/xwechat_files/wxid_0n7eboddvh9u22_76fc/msg/file/2026-05/Untitled.pdf', 'rb'), 'application/pdf')),
]

# 4. 发送请求
try:
    response = requests.post(url, data=data, files=files)
    
    print("状态码:", response.status_code)
    

    print("原始返回内容:", response.text)  # 先看它到底回了什么
    
    if response.text:
        print("JSON内容:", response.json())
    else:
        print("⚠️ 后端返回内容为空！")

except Exception as e:
    print("请求出错:", e)
finally:
    # 记得关闭文件
    for f in files:
        f[1][1].close()