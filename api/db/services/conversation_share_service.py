import time
from uuid import uuid4
from common.constants import StatusEnum
from api.db.db_models import Conversation, DB, ConversationShare
from api.db.services.api_service import API4ConversationService
from api.db.services.common_service import CommonService
from api.db.services.dialog_service import DialogService, async_chat
from common.misc_utils import get_uuid
import json

from rag.prompts.generator import chunks_format


class ConversationShareService(CommonService):
    model = ConversationShare

    @classmethod
    @DB.connection_context()
    def create_share(cls, conversation_id, dialog_id, name, user_id, snapshot):
        share_id = uuid4().hex

        share = cls.model.create(
            id=share_id,
            conversation_id=conversation_id,
            dialog_id=dialog_id,
            name=name,
            user_id=user_id,
            snapshot=snapshot,
        )

        return share

    @classmethod
    @DB.connection_context()
    def get_share_by_id(cls, share_id):
        e, share = cls.get_by_id(share_id)
        if not e:
            return None
        return share.to_dict()