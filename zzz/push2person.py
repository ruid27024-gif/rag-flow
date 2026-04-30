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

import json

from api.db.services.person_service import SyncPersonService


from api.db.db_models import DB, SyncPerson, SyncDept  # 你现有的连接
from peewee import *

# 3. 首次运行：自动建表并插入数据
def setup_and_insert(data_list):
    with DB.connection_context():
        print(len(data_list))
        # 如果表不存在就创建
        if not SyncPerson.table_exists():
            SyncPerson.create_table()
            print("✅ 表 sync_dept 已创建")

        # 插入数据
        count = SyncPersonService.raw_batch_insert(data_list)
        print(f"✅ 已插入 {count} 条数据")

try:
    with open('/home/zyb/rag-flow/zzz/people.json', 'r', encoding='utf-8') as file:
        # 写入数据库
        data = json.load(file)
        print(data['rtnData']['result'][0])
        print(len(data['rtnData']['result']))
        setup_and_insert(data['rtnData']['result'])
        #
        # dept = SyncDept.select(SyncDept.mdmName).where(SyncDept.mdmCode == "100534").first()
        # print(dept)
        
        # with DB.connection_context():
        #     cur = DB.cursor()
        #     cur.execute("SELECT DATABASE()")
        #     db_name = cur.fetchone()[0]
        #     print("Peewee 当前库:", db_name)

        # dept = SyncDept.select(SyncDept.mdmName).where(
        #     SyncDept.mdmCode == 100534
        # ).first()

        # dept = SyncDept.select(SyncDept.mdmCode).where(
        #     SyncDept.mdmName == '工艺研究一室（100146）'
        # ).first()

        # # person = SyncPerson.select(SyncPerson.mdmName).where(
        # #     SyncPerson.mdmCode == 105405
        # # ).first()
        # print(dept.mdmCode)


except FileNotFoundError:
    print("错误：找不到指定的文件，请检查路径是否正确。")
except json.JSONDecodeError as e:
    print(f"错误：JSON 格式不正确，无法解析。详情: {e}")





{'id': '830366547842207744',
 'organize': '16#机成品工段',
 'organizationCode': '100105',
 'mdmName': '',
 'mdmCode': '105405',
 'part': '',
 'gender': '男',
 'onDutyOrNot': '是',
 'credentialNo': '',
 'phone': '',
 'birthday': '1989-05-09',
 'timeOfEnteringTheGroup': '2026-04-10 00:00:00',
 'personnelCategory': '劳务派遣',
 'dateOfResignation': None,
 'email': None,
 'erpid': '2454349193435696128',
 'childData': {'contactInformation': [], 'department': [{'id': '833875226205917184', 'department': '16#机成品工段', 'departmentName': '牡丹江恒丰纸业集团有限责任公司_牡丹江恒丰纸业股份有限公司_抄纸三分厂_16#机_16#机成品工段', 'position': '16#机打件工', 'principal': '否', 'part': '否', 'superior': None}], 'information': [{'id': '833875226222694400', 'personnelCategory': '劳务派遣', 'personnelCode': '105405', 'jobCode': 'ZW000513', 'post': '16#机打件工', 'resignationDate': None, 'jobSequenceCode': 'ZD035', 'jobSequence': '一般操作工人', 'onDuty': '是', 'remark': None, 'companyName': '牡丹江恒丰纸业股份有限公司', 'companyAbbreviation': '牡丹江恒丰纸业股份有限公司', 'firstTimeIntoTheGroup': '2026-04-10 00:00:00', 'mnemonicCode': None, 'responsibleManNumber': '100206', 'principal': '喻小桥', 'primaryDepartmentCode': '100094', 'firstLevelDepartment': '抄纸三分厂', 'mainPost': '是'}]}}

# {'id': '',
#  'mdmCode': '',
#  'mdmName': '',
#  'companyCode': '',
#  'corporateName': '',
#  'nameOfAdminOrg': '',
#  'administrativeOrganizationCode': '',
#  'parentId': '',
#  'parentAdminOrgCode': '',
#  'departmentName': '',
#  'departmentCode': '',
#  'remarks': ' ',
#  'sealed': '',
#  'administrativeOrganizationType': '',
#  'longName': '',
#  'longCode': '',
#  'erpid': ''}