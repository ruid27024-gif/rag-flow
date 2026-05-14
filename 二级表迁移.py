# 获取组管理员id  --> 把管理员的根放进表中
from playhouse.shortcuts import model_to_dict

from api.db.db_models import AdminUser, File, File_Group, Group, UserGroup, User

query = AdminUser.select().where(AdminUser.role_level == 2)

# admin_user = AdminUser.select().where(AdminUser.role_level == 1)[1]

# 获取到超级管理员
admin_user1 = AdminUser.select().where(AdminUser.role_level == 1).first()
File_Group.create_table(safe=True)
# 遍历2级别管理员
for user in query:
    # 组管理员写入表中
    print(f"用户ID: {user.user_id}, 角色等级: {user.role_level}")

    # 获取2级管理员的根
    file = (
        File
        .select()
        .where(
            (File.parent_id == File.id) &
            (File.tenant_id == user.user_id)
        )
        .first()
    )
    print(file.to_dict())
    try:
        File_Group.create(**file.to_dict())
    except Exception as e:
        pass


    # 然后获取组管理员所在的组  --> 找管理员所在的组
    user_group = UserGroup.select().where(UserGroup.user_id == user.user_id).first()
    group_id = user_group.group_id
    print(group_id)  # 组id
    print(user.user_id)  # 管理员id
    # 找出组员
    user_groups = UserGroup.select().where((UserGroup.group_id == group_id) & (UserGroup.user_id != user.user_id)
                                           & (UserGroup.user_id != admin_user1.user_id))
    print("--------------------------------------------------")
    for i in user_groups:
        print(model_to_dict(i))

    print("-------------------------------------------")
    U_ID = user.user_id
    # 通过组长id获取根
    file = File.select().where(
        (File.id == File.parent_id) & (File.tenant_id == U_ID)
    ).first()
    print(file.to_dict())
    pf_id = file.parent_id

    print(f"{"管理员的根为{pf_id}"}")

    # 获取组里所有成员的id --> 找到组内所有成员的id(挂到组管理员根上)
    for user_group in user_groups:
        print(model_to_dict(user_group))

        # 组内所有成员
        user_group_id = user_group.user_id

        user1 = User.select().where(User.id == user_group_id).first()
        user_nickname = user1.nickname
        print(user_group_id)
        print(user_nickname)


        # 拿到成员的根 --> 挂到组长的根上
        file = File.select().where((File.id == File.parent_id )& (File.tenant_id == user_group_id) & (File.tenant_id != user.user_id)).first()
        # print(file.to_dict())

        if file:
            print(".......................................................")
            print(file.to_dict())
            file.parent_id = pf_id
            file.name = user_nickname
            try:
                File_Group.create(**file.to_dict())
            except Exception as e:
                pass

        



# 表格中不是根的且不是二级管理员的直接写入
query = AdminUser.select().where(AdminUser.role_level == 2)
# ids = [i.user_id for i in query]
file = File.select().where((File.id != File.parent_id)
                           & (File.tenant_id != admin_user1.user_id)
                        #    & (File.tenant_id.not_in(ids))
                           )

for i in file:
    i.to_dict()
    print(i.to_dict())
    try:
        File_Group.create(**i.to_dict())
    except:
        pass


# 把4个组参考库分别接入组内
# 获取参考库的根
file1 = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == 'b49914742aa211f1a25910ffe02ab235')).first()

# 获取工艺研究一室的组长的tenant
# "9157d24e235311f1b18e10ffe02ab235"
file1_ = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == "9157d24e235311f1b18e10ffe02ab235")).first()


file1.parent_id = file1_.id
file1.name = '工艺研究一室参考库 + 报告库'
try:
    File_Group.create(**file1.to_dict())
except Exception as e:
    pass 

file2 = File.select().where((File.parent_id == File.id)
                        & (File.tenant_id == 'f3cb12522aa011f199ea10ffe02ab235')).first()

# 获取工艺研究二室的组长的tenant
# "9157d24e235311f1b18e10ffe02ab235"
file2_ = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == "68ff1df2278611f1a03d10ffe02ab235")).first()


file2.parent_id = file2_.id
file2.name = '工艺研究二室参考库 + 报告库'
try:
    File_Group.create(**file2.to_dict()) 
except Exception as e:
    pass 




file3 = File.select().where((File.parent_id == File.id)
                        & (File.tenant_id == '145307e82a9011f1b25310ffe02ab235')).first()

# 获取工艺研究三室的组长的tenant
# "9157d24e235311f1b18e10ffe02ab235"
file3_ = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == "b75b9ad6278911f1a03d10ffe02ab235")).first()


file3.parent_id = file3_.id
file3.name = '工艺研究三室参考库 + 报告库'
try:
    File_Group.create(**file3.to_dict()) 
except Exception as e:
    pass 





file4 = File.select().where((File.parent_id == File.id)
                        & (File.tenant_id == 'b76923563eb111f1942e345a60aae1f7')).first()


# 组
file4_ = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == "cbd67f624e7111f1960ee8473ae7fab0")).first()


file4.parent_id = file4_.id
file4.name = '新品事业部研发部参考库 + 报告库'

try:
    File_Group.create(**file4.to_dict()) 
except Exception as e:
    pass 



# 1 挂5
# 全局参考库
file5 = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == 'e475b8cc215711f1b64c10ffe02ab235')).first()

file5.parent_id = file1_.id
file5.name = '全局参考库'

try:
    File_Group.create(**file5.to_dict()) 
except Exception as e:
    pass 

file5.parent_id = file2_.id
file5.name = '全局参考库'

try:
    File_Group.create(**file5.to_dict()) 
except Exception as e:
    pass 

file5.parent_id = file3_.id
file5.name = '全局参考库'

try:
    File_Group.create(**file5.to_dict()) 
except Exception as e:
    pass 

file5.parent_id = file4_.id
file5.name = '全局参考库'

try:
    File_Group.create(**file5.to_dict()) 
except:
    pass
