import json
import sys
import os

# 获取当前脚本所在的目录 (/home/zyb/rag-flow/zzz)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (/home/zyb/rag-flow)
project_root = os.path.dirname(current_dir)

# 将项目根目录加入 sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from api.db.services.dept_service import SyncDeptService
from api.db.db_models import DB, SyncDept  # 你现有的连接
from peewee import *

# 3. 首次运行：自动建表并插入数据
def setup_and_insert(data_list):
    with DB.connection_context():
        print(len(data_list))
        # 如果表不存在就创建
        if not SyncDept.table_exists():
            SyncDept.create_table()
            print("✅ 表 sync_dept 已创建")

        # 插入数据
        count = SyncDeptService.raw_batch_insert(data_list)
        print(f"✅ 已插入 {count} 条数据")

try:
    with open('/home/hengyue/rag-flow/zzz/dept.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        # print(data['rtnData']['result'][0])
        setup_and_insert(data['rtnData']['result'])

except FileNotFoundError:
    print("错误：找不到指定的文件，请检查路径是否正确。")
except json.JSONDecodeError as e:
    print(f"错误：JSON 格式不正确，无法解析。详情: {e}")

