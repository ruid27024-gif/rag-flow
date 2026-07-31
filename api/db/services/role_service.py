from api.db.db_models import DB, Role
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp
from api.db.db_models import User


class FilePermissionLevel:
    PUBLIC = 1
    INTERNAL = 2


class OperationPermissionBits:
    VIEW = 1 << 0
    UPLOAD = 1 << 1
    DOWNLOAD = 1 << 2
    DELETE = 1 << 3
    EDIT = 1 << 4


OPERATION_PERMISSION_MAP = {
    "view": OperationPermissionBits.VIEW,
    "upload": OperationPermissionBits.UPLOAD,
    "download": OperationPermissionBits.DOWNLOAD,
    "delete": OperationPermissionBits.DELETE,
    "edit": OperationPermissionBits.EDIT,
}


def validate_file_permission_level(value):
    return value in (
        FilePermissionLevel.PUBLIC,
        FilePermissionLevel.INTERNAL,
    )


def validate_operation_permissions(operation_permissions):
    if not isinstance(operation_permissions, list):
        return False

    for permission in operation_permissions:
        if permission not in OPERATION_PERMISSION_MAP:
            return False

    return True


def build_operation_permission_mask(operation_permissions):
    mask = 0

    for permission in operation_permissions:
        mask |= OPERATION_PERMISSION_MAP[permission]

    return mask


class RoleService(CommonService):
    model = Role

    @classmethod
    @DB.connection_context()
    def save(cls, **kwargs):
        if "created_time" not in kwargs:
            kwargs["created_time"] = current_timestamp()

        if "updated_time" not in kwargs:
            kwargs["updated_time"] = current_timestamp()

        if "enabled" not in kwargs:
            kwargs["enabled"] = True

        obj = cls.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def get_by_name(cls, role_name):
        return cls.model.select().where(
            cls.model.role_name == role_name
        ).first()

    @classmethod
    @DB.connection_context()
    def get_by_id(cls, role_id):
        return cls.model.select().where(
            cls.model.id == role_id
        ).first()

    @classmethod
    @DB.connection_context()
    def update_by_id(cls, role_id, **kwargs):
        kwargs["updated_time"] = current_timestamp()

        return cls.model.update(**kwargs).where(
            cls.model.id == role_id
        ).execute()

    @classmethod
    @DB.connection_context()
    def list_all(cls):
        return list(
            cls.model
            .select()
            .order_by(cls.model.created_time.desc())
        )