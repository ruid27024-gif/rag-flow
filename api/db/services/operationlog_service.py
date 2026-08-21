import json
import uuid
from datetime import datetime

from api.db.db_models import OperationLog
from api.db.services.common_service import CommonService


class OperationLogService(CommonService):
    model = OperationLog

    @classmethod
    def get_cls_model_fields(cls):
        return [
            cls.model.id,

            cls.model.user_id,
            cls.model.user_name,
            cls.model.user_email,

            cls.model.kb_id,
            cls.model.kb_name,

            cls.model.target_id,
            cls.model.target_name,

            cls.model.action,
            cls.model.status,
            cls.model.message,

            cls.model.before_data,
            cls.model.after_data,

            cls.model.ip,
            cls.model.operation_time,
        ]

    @classmethod
    def datetime_format(cls, value):
        if not value:
            return None

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        return value

    @classmethod
    def json_dumps(cls, value):
        if value is None:
            return None

        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    @classmethod
    def get_request_ip(cls, request_obj=None):
        if not request_obj:
            return None

        try:
            ip = (
                request_obj.headers.get("X-Forwarded-For")
                or request_obj.headers.get("X-Real-IP")
                or getattr(request_obj, "remote_addr", None)
            )

            if ip and "," in ip:
                ip = ip.split(",")[0].strip()

            return ip
        except Exception:
            return None

    from datetime import datetime
    import uuid


    @classmethod
    def add_log(
        cls,
        user_id=None,
        user_name=None,
        user_email=None,
        kb_id=None,
        kb_name=None,
        target_id=None,
        target_name=None,
        action=None,
        status="success",
        message=None,
        before_data=None,
        after_data=None,
        request_obj=None,
        ip=None,
    ):
        try:
            if not ip:
                ip = cls.get_request_ip(request_obj)

            now = datetime.now()

            print("OperationLog model:", cls.model)
            print("OperationLog create_time before insert:", now)

            log = cls.model.create(
                id=uuid.uuid4().hex,
                user_id=str(user_id) if user_id else "",
                user_name=user_name,
                user_email=user_email,
                kb_id=str(kb_id) if kb_id else None,
                kb_name=kb_name,
                target_id=str(target_id) if target_id else None,
                target_name=target_name,
                action=action or "",
                status=status or "success",
                message=message,
                before_data=cls.json_dumps(before_data),
                after_data=cls.json_dumps(after_data),
                ip=ip,
                operation_time=now,
            )


            return log

        except Exception as e:
            print(f"OperationLogService.add_log error: {e}")
            return None


    @classmethod
    def list_by_target_id(
        cls,
        target_id,
        page_number=1,
        items_per_page=20,
    ):
        """
        根据文档/对象 ID 查询操作日志。
        """

        query = cls.model.select(*cls.get_cls_model_fields()).where(
            cls.model.target_id == str(target_id)
        )

        query = query.order_by(cls.model.operation_time.desc())

        count = query.count()

        if page_number and items_per_page:
            offset = (page_number - 1) * items_per_page
            query = query.offset(offset).limit(items_per_page)

        rows = list(query.dicts())

        for row in rows:
            row["operation_time"] = cls.datetime_format(row.get("operation_time"))

        return rows, count

    @classmethod
    def list_by_kb_id(
        cls,
        kb_id=None,
        page_number=1,
        items_per_page=20,
        action=None,
        keyword=None,
    ):
        query = cls.model.select(*cls.get_cls_model_fields())

        if kb_id:
            query = query.where(cls.model.kb_id == str(kb_id))

        if action:
            query = query.where(cls.model.action == action)

        if keyword:
            keyword = keyword.strip()
            if keyword:
                query = query.where(
                    (cls.model.target_name.contains(keyword))
                    | (cls.model.user_name.contains(keyword))
                    | (cls.model.user_email.contains(keyword))
                    | (cls.model.kb_name.contains(keyword))
                )

        query = query.order_by(cls.model.operation_time.desc())

        count = query.count()

        if page_number and items_per_page:
            offset = (int(page_number) - 1) * int(items_per_page)
            query = query.offset(offset).limit(int(items_per_page))

        rows = list(query.dicts())

        for row in rows:
            row["operation_time"] = cls.datetime_format(row.get("operation_time"))
        return rows, count