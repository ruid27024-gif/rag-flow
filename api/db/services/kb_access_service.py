
from peewee import *
from api.db.db_models import DB

# 假设你已经在 models 里定义好了 KnowledgebaseAccess 模型类
from api.db.db_models import KnowledgebaseAccess
from api.db.services.common_service import CommonService

class KnowledgebaseAccessService(CommonService):
    model = KnowledgebaseAccess

    @classmethod
    @DB.connection_context()
    def add_permission(cls, kb_id, user_id, permission):
        """
        增加一条权限记录（支持 read 或 write）
        """
        # 使用 get_or_create 防止重复插入报错
        obj, created = cls.model.get_or_create(
            kb_id=kb_id,
            user_id=user_id,
            permission=permission,
            defaults={} # 如果是新建，生成一个 UUID
        )
        return obj

    @classmethod
    @DB.connection_context()
    def remove_permission(cls, kb_id, user_id, permission=None):
        """
        删除权限记录
        如果不传 permission，则删除该用户在该知识库下的所有权限（read和write都删）
        """
        query = cls.model.delete().where(cls.model.kb_id == kb_id, cls.model.user_id == user_id)
        
        if permission:
            query = query.where(cls.model.permission == permission)
            
        return query.execute() # 返回受影响的行数

    @classmethod
    @DB.connection_context()
    def get_user_permissions(cls, kb_id, user_id):
        """
        查询某个用户在特定知识库下的所有权限列表，例如返回 ['read', 'write']
        """
        records = cls.model.select(cls.model.permission).where(
            cls.model.kb_id == kb_id,
            cls.model.user_id == user_id
        )
        return [r.permission for r in records]
    
    @classmethod
    @DB.connection_context()
    def get_read_users(cls, kb_id):
        """
        获取某个知识库下拥有读权限的所有用户ID列表
        """
        records = cls.model.select(cls.model.user_id).where(
            cls.model.kb_id == kb_id,
            cls.model.permission == 'read'
        )
        return [r.user_id for r in records]

    @classmethod
    @DB.connection_context()
    def get_write_users(cls, kb_id):
        """
        获取某个知识库下拥有写权限的所有用户ID列表
        """
        records = cls.model.select(cls.model.user_id).where(
            cls.model.kb_id == kb_id,
            cls.model.permission == 'write'
        )
        return [r.user_id for r in records]
    
    # 判断是否存在写入权限
    @classmethod
    @DB.connection_context()
    def has_write_permission(cls, kb_id, user_id):
        """
        判断指定用户在某个知识库下是否拥有写权限
        """
        # 使用 exists() 方法进行高效判断
        return cls.model.select().where(
            cls.model.kb_id == kb_id,
            cls.model.user_id == user_id,
            cls.model.permission == 'write'
        ).exists()