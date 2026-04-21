# api/db/services/sync_dept_service.py
from api.db.db_models import DB, SyncDept
from api.db.services.common_service import CommonService

class SyncDeptService(CommonService):
    model = SyncDept

    @classmethod
    @DB.connection_context()
    def raw_batch_insert(cls, dict_list):
        """
        将字典列表直接插入，不做任何补值、判空、改名。
        要求：每个字典的 key 必须与模型字段名完全一致。
        """
        if not dict_list:
            return 0
        with DB.atomic():
            cls.model.insert_many(dict_list).execute()
        return len(dict_list)