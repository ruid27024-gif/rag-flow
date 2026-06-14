# file = FileAdminService.insert({
#     "id": user_id,  # 昵称的id
#     "parent_id": group_id,
#     "tenant_id": current_user.id,
#     "created_by": current_user.id,
#     "name": add_user.nickname,
#     "location": "",
#     "size": 0,
#     "type": FileType.FOLDER.value
# })

from api.db import FileType
from api.db.db_models import AdminUser, Group, File, File_Admin, User, UserGroup


from api.db.db_models import AdminUser
from peewee import *
File_Admin.create_table()
def test():
    # # 1. 获取管理员
    # admin_user = AdminUser.select().where(AdminUser.role_level == 1).first()
    # if not admin_user:
    #     print("❌ 没有管理员用户")
    #     return

    # user_id = admin_user.user_id
    # print("admin user_id:", user_id)

    # # 2. 获取管理员根目录
    # root = (
    #     File
    #     .select()
    #     .where(
    #         (File.parent_id == File.id) &
    #         (File.tenant_id == user_id)
    #     )
    #     .first()
    # )

    

    # if not root:
    #     print("❌ 没有找到管理员根目录")
    #     return

    # print("✅ 根目录 ID:", root.id)
    # print("✅ parent_id:", root.parent_id)
    # print("✅ tenant_id:", root.tenant_id)


    # files = File.select().where(File.tenant_id == user_id).execute()
    # # 现在你可以像操作普通列表一样遍历它
    # for file in files:
    #     print(file.to_dict())  # 假设你的 File 模型有一个 filename 字段

    #     try:
    #         File_Admin.create(**file.to_dict())
    #     except IntegrityError as e:
    #         print("主键已存在，跳过:", file.id)


    # # 获取到所有的组id 名称

    # query = (
    #     Group
    #     .select(Group.group_id, Group.group_name)
    #     .dicts()  # 返回 dict，而不是 Model 对象
    # )

    # groups =list(query)
    # for g in groups:
    #     print(g["group_id"], g["group_name"])

    #     try:
    #         # root1 = root.copy()
    #         root.id = g["group_id"]
    #         root.name = g["group_name"]

    #         File_Admin.create(**root.to_dict())
    #     except IntegrityError as e:
    #         print("主键已存在，跳过:",g["group_id"])

    # # 将其他人的根挂载到组id    将组员的根目录id挂载到组号上
    # # 左关联到 --> 组id + 人名
    # query = (
    #     File
    #     .select(File, UserGroup, User)
    #     .join(UserGroup, JOIN.LEFT_OUTER,
    #           on=File.tenant_id == UserGroup.user_id)
    #     .switch(File)
    #     .join(User, JOIN.LEFT_OUTER,
    #           on=UserGroup.user_id == User.id)
    #     .where(
    #         (File.parent_id == File.id) &
    #         (File.id != root.id)
    #     )
    # )

    # print(f"共查询到 {query.count()} 条数据：")

    # for row in query.execute():
    #     print(f"File: {row.id}")


    #     # --- 修改点开始 ---
    #     # 使用 getattr 安全地获取属性，如果不存在则返回 None
    #     # 这样即使没有关联到 UserGroup，程序也不会崩溃
    #     ug = getattr(row, 'usergroup', None)
    #     user = getattr(row, 'user', None)

    #     if ug:
    #         try:
    #             print(f"  - UserGroup: {ug.group_id} (已关联)")
    #             row.parent_id = ug.group_id
    #             row.name = user.nickname
    #             row.to_dict()
    #             File_Admin.create(**row.to_dict())
    #             print("hello")
    #         except Exception as e:
    #             pass
    #     else:
    #         print(f"  - UserGroup: None (无关联，但文件已保留)")

    #     if user:
    #         print(f"  - User: {user}")
    #     else:
    #         print(f"  - User: None")
    #     # --- 修改点结束 ---

    # # 将数据库中不是根且不是管理员的数据直接转入
    # files = File.select().where((File.parent_id != File.id)
    #                             & (File.tenant_id != admin_user.user_id)).execute()
    
    # print("-----------------------------------------------------")
    # # 现在你可以像操作普通列表一样遍历它
    # for file in files:

    #     try:
    #         # print(file.to_dict())
    #         # 假设你的 File 模型有一个 filename 字段
    #         File_Admin.create(**file.to_dict()) 
    #     except Exception as e:
    #         pass
    
    # """
    # group_reference_tenant_map:
    # # 实验室1
    # '71196836278011f19ca210ffe02ab235': 'b49914742aa211f1a25910ffe02ab235'  # 1组id : 参考库tennat_id
    # # test_a
    # 'e013c3d4278611f1a03d10ffe02ab235': 'f3cb12522aa011f199ea10ffe02ab235'
    # # test_b
    # '8e865b04278a11f1a03d10ffe02ab235': '145307e82a9011f1b25310ffe02ab235'
    # # 实验室4
    # '1dc3a6243ed711f1a593345a60aae1f7': 'b76923563eb111f1942e345a60aae1f7'

    # # 组名 --> 组id
    # group_name_id_map:
    # '工艺研究一室（100146）': '71196836278011f19ca210ffe02ab235' 
    # '工艺研究二室（100147）': 'e013c3d4278611f1a03d10ffe02ab235'
    # '工艺研究三室（100148）': '8e865b04278a11f1a03d10ffe02ab235'
    # '新品事业部研发部（100051）': '1dc3a6243ed711f1a593345a60aae1f7'
    
    # """
    
    # 把4个组参考库分别接入组内
    # 获取参考库的根
    # file1 = File.select().where((File.parent_id == File.id)
    #                             & (File.tenant_id == 'b49914742aa211f1a25910ffe02ab235')).first()
    
    # file1.parent_id = '71196836278011f19ca210ffe02ab235'
    # file1.name = '工艺研究一室'
    # try:
    #     File_Admin.create(**file1.to_dict())
    # except Exception as e:
    #     pass 
    
    # file2 = File.select().where((File.parent_id == File.id)
    #                         & (File.tenant_id == 'f3cb12522aa011f199ea10ffe02ab235')).first()
    # file2.parent_id = 'e013c3d4278611f1a03d10ffe02ab235'
    # file2.name = '工艺研究二室'
    # try:
    #     File_Admin.create(**file2.to_dict()) 
    # except Exception as e:
    #     pass 
    
    # file3 = File.select().where((File.parent_id == File.id)
    #                         & (File.tenant_id == '145307e82a9011f1b25310ffe02ab235')).first()
    # file3.parent_id = '8e865b04278a11f1a03d10ffe02ab235'
    # file3.name = '工艺研究三室'
    # try:
    #     File_Admin.create(**file3.to_dict()) 
    # except Exception as e:
    #     pass 
    # file4 = File.select().where((File.parent_id == File.id)
    #                         & (File.tenant_id == 'b76923563eb111f1942e345a60aae1f7')).first()
    # file4.parent_id = '1dc3a6243ed711f1a593345a60aae1f7'
    # file4.name = '新品事业部研发部'

    # try:
    #     File_Admin.create(**file4.to_dict()) 
    # except Exception as e:
    #     pass 

    file5 = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == '18b80f5c661f11f1bd02e8473ae7fab0')).first()
    file5.parent_id = '72551b94660711f19ddbe8473ae7fab0'
    file5.name = '数字化管理中心'




    File_Admin.create(**file5.to_dict()) 


    # # 全局参考库
    # file5 = File.select().where((File.parent_id == File.id)
    #                             & (File.tenant_id == 'e475b8cc215711f1b64c10ffe02ab235')).first()
    # file5.parent_id = 'c6b07758278a11f1a03d10ffe02ab235'
    # file5.name = '全局参考库'

    # try:
    #     File_Admin.create(**file5.to_dict()) 
    # except Exception as e:
    #     pass 
    


if __name__ == "__main__":
    test()


