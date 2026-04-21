# api/db/services/sync_person_service.py
from api.db.db_models import DB, SyncPerson
from api.db.services.common_service import CommonService

class SyncPersonService(CommonService):
    model = SyncPerson

    @classmethod
    @DB.connection_context()
    def raw_batch_insert(cls, dict_list):
        if not dict_list:
            return 0
        
        total_count = 0
        batch_size = 500  # 每次只插 500 条，避免超过 max_allowed_packet
        
        # 分批处理
        for i in range(0, len(dict_list), batch_size):
            batch_data = dict_list[i : i + batch_size]
            try:
                with DB.atomic():
                    cls.model.insert_many(batch_data).execute()
                    total_count += len(batch_data)
                    # 可选：打印进度
                    # print(f"已插入批次: {i//batch_size + 1}, 当前批次数量: {len(batch_data)}")
            except Exception as e:
                print(f"❌ 批量插入失败，批次索引: {i}, 错误: {e}")
                # 这里可以选择抛出异常中断，或者继续尝试下一批
                # raise e 
        
        return total_count