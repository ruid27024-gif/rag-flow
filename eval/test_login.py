import base64
import json
import uuid
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5


PUB_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/
z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp
2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOO
UEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVK
RNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK
6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs
2wIDAQAB
-----END PUBLIC KEY-----"""


def _encrypt_password(password: str) -> str:
    b64_password = base64.b64encode(password.encode("utf-8")).decode("utf-8")
    rsa_key = RSA.importKey(PUB_KEY)
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted = cipher.encrypt(b64_password.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def login_get_auth(email: str, password_plain: str) -> str | None:
    url = "http://127.0.0.1:9380/v1/user/login"
    encrypted_password = _encrypt_password(password_plain)
    payload = {"email": email, "password": encrypted_password}
    print("【DEBUG-HY】登录URL:", url)
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print("【DEBUG-HY】登录HTTP状态码:", resp.status_code)
        try:
            print("【DEBUG-HY】登录响应JSON:", resp.json())
        except Exception:
            print("【DEBUG-HY】登录响应文本:", resp.text)
        auth = resp.headers.get("Authorization")
        print("【DEBUG-HY】登录返回Authorization:", auth)
        return auth
    except Exception as e:
        print("【DEBUG-HY】登录请求异常:", str(e))
        return None


def create_conversation(auth: str, dialog_id: str, name: str, conversation_id: str) -> dict | None:
    url = "http://127.0.0.1:9380/v1/conversation/set"
    headers = {"Authorization": auth}
    payload = {
        "dialog_id": dialog_id,
        "is_new": True,
        "conversation_id": conversation_id,
        "name": name,
    }
    print("【DEBUG-HY】创建会话URL:", url)
    print("【DEBUG-HY】创建会话载荷:", payload)
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        print("【DEBUG-HY】创建会话HTTP状态码:", resp.status_code)
        data = resp.json()
        print("【DEBUG-HY】创建会话响应JSON:", data)
        return data
    except Exception as e:
        print("【DEBUG-HY】创建会话异常:", str(e))
        return None


def ask_completion(auth: str, conversation_id: str, question: str) -> dict | None:
    url = "http://127.0.0.1:9380/v1/conversation/completion"
    headers = {"Authorization": auth}
    body = {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": "user",
                "content": question,
                "id": uuid.uuid4().hex,
            }
        ],
        "stream": False,
    }
    print("【DEBUG-HY】提问URL:", url)
    print("【DEBUG-HY】提问载荷:", {"conversation_id": conversation_id, "messages": [{"role": "user", "content": question}]})
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        print("【DEBUG-HY】提问HTTP状态码:", resp.status_code)
        data = resp.json()
        print("【DEBUG-HY】提问响应JSON:", data)
        return data
    except Exception as e:
        print("【DEBUG-HY】提问异常:", str(e))
        return None


def run_flow():
    email = "1149925366@qq.com"
    password_plain = "123456"
    dialog_id = "f547a920e61b11f0811d10ffe02ab235"
    question = "请介绍热磨工艺是什么"
    # 1) 登录获取 Authorization
    auth = login_get_auth(email, password_plain)
    if not auth:
        print("【DEBUG-HY】未获取到Authorization，流程终止")
        return
    # 2) 创建会话（新会话）
    conversation_id = uuid.uuid4().hex
    create_conversation(auth, dialog_id, question, conversation_id)
    # 3) 首次提问，非流式返回
    ask_completion(auth, conversation_id, question)


def run_question(question: str) -> str:
    print("【DEBUG-HY】输入问题:", question)
    email = "1149925366@qq.com"
    password_plain = "123456"
    dialog_id = "7273efd6ebb111f0be4d10ffe02ab235"
    print("【DEBUG-HY】开始登录")
    auth = login_get_auth(email, password_plain)
    if not auth:
        print("【DEBUG-HY】未获取到Authorization，流程终止")
        return ""
    print("【DEBUG-HY】创建新会话")
    conversation_id = uuid.uuid4().hex
    create_conversation(auth, dialog_id, question, conversation_id)
    print("【DEBUG-HY】发送非流式提问")
    data = ask_completion(auth, conversation_id, question)
    try:
        fname = f"test/ask_completion_{conversation_id}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data if isinstance(data, dict) else {"data": data}, f, ensure_ascii=False, indent=2)
        print("【DEBUG-HY】保存JSON文件:", fname)
    except Exception as e:
        print("【DEBUG-HY】保存JSON失败:", str(e))
    answer = ""
    if isinstance(data, dict):
        d = data.get("data") or {}
        answer = d.get("answer") or ""
    # print("【DEBUG-HY】得到回答:", answer)
    return data

def answer_and_extract(real_info: dict) -> dict:
    result_dict = {}
    question = real_info.get("question") or ""
    if question == "":
        return result_dict
    answer = real_info.get("answer") or ""
    real_source = real_info.get("title") or ""
    result_dict["question"] = question
    result_dict["answer"] = answer
    result_dict["source"] = real_source
    model_ans = run_question(question)
    data = model_ans.get("data") or {}
    model_answer = data.get("answer") or ""
    model_references = data.get("reference") or []
    model_references = model_references.get("chunks") or []
    clear_referneces = []
    for ref in model_references:
        clear_ref = {}
        clear_ref["content"] = ref.get("content") or ""
        clear_ref["document_name"] = ref.get("document_name") or ""
        clear_referneces.append(clear_ref)
    result_dict["model_answer"] = model_answer
    result_dict["model_references"] = clear_referneces
    return result_dict


if __name__ == "__main__":
    # 读取数据集
    dataset_path = "dataset.json"
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        print(f"【DEBUG-HY】成功读取数据集: {dataset_path}, 共 {len(dataset)} 条数据")
    except Exception as e:
        print(f"【DEBUG-HY】读取数据集失败: {str(e)}")
        dataset = []

    # dataset = dataset[:1]  # Remove this limit if you want to process all
    all_results = []
    output_file = "final_answer.json"
    
    for i, item in enumerate(dataset):
        print(f"【DEBUG-HY】正在处理第 {i+1}/{len(dataset)} 条数据")
        try:
            result = answer_and_extract(item)
            all_results.append(result)
            
            # Save incrementally
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(all_results, f, ensure_ascii=False, indent=4)
                print(f"【DEBUG-HY】已保存前 {i+1} 条结果到 {output_file}")
            except Exception as e:
                print(f"【DEBUG-HY】增量保存失败: {str(e)}")
                
        except Exception as e:
            print(f"【DEBUG-HY】处理第 {i+1} 条数据时出错: {str(e)}")

