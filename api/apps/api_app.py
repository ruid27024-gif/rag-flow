#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from datetime import datetime, timedelta
from quart import request
from api.db.db_models import APIToken
from api.db.services.api_service import APITokenService, API4ConversationService
from api.db.services.user_service import UserTenantService
from api.utils.api_utils import generate_confirmation_token, get_data_error_result, get_json_result, get_request_json, server_error_response, validate_request
from common.time_utils import current_timestamp, datetime_format
from api.apps import login_required, current_user
@manager.route('/group_member_stats', methods=['POST'])
# @login_required
async def group_member_stats():
    """
    获取所有组及组内成员的 Token 和问答次数统计

    POST body:
    {
        "period": "all" | "day" | "week" | "month" | "year"
    }
    """
    try:
        from datetime import datetime, timedelta
        from api.db.db_models import APIToken
        from api.db.db_models import Group, UserGroup, User
        from peewee import fn

        # 1. 接收 POST JSON 参数
        req = await get_request_json()
        req = req or {}

        period = req.get("period", "all")

        # 防止非法参数
        if period not in ["all", "day", "week", "month", "year"]:
            period = "all"

        # 2. 根据 period 计算时间范围
        now = datetime.now()

        start_time = None
        end_time = None

        start_time_ts = None
        end_time_ts = None

        print("group_member_stats period:", period)

        if period == "day":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now

        elif period == "week":
            start_time = now - timedelta(days=now.weekday())
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now

        elif period == "month":
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = now

        elif period == "year":
            start_time = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = now

        elif period == "all":
            # 全部数据，不加时间过滤
            start_time = None
            end_time = None

        # 3. datetime 转 create_time 使用的时间戳
        # RAGFlow 里 create_time 通常是毫秒时间戳，所以乘 1000
        if start_time and end_time:
            start_time_ts = int(start_time.timestamp() * 1000)
            end_time_ts = int(end_time.timestamp() * 1000)

        print("start_time:", start_time)
        print("end_time:", end_time)
        print("start_time_ts:", start_time_ts)
        print("end_time_ts:", end_time_ts)

        # 4. 查出所有组
        groups = Group.select()
        final_result = []

        # 5. 遍历每个组
        for group in groups:
            # 5.1 查出该组下所有人员，并联查 User 获取 nickname
            members = list(
                UserGroup
                .select(
                    UserGroup.user_id,
                    User.nickname
                )
                .join(User, on=(UserGroup.user_id == User.id))
                .where(UserGroup.group_id == group.group_id)
                .dicts()
            )

            tenant_ids = [m["user_id"] for m in members]

            member_list = []
            total_tokens = 0
            total_dialogs = 0

            if tenant_ids:
                conditions = [
                    APIToken.tenant_id.in_(tenant_ids)
                ]

                # period != all 时才加时间过滤
                if period != "all":
                    conditions.extend([
                        APIToken.create_time >= start_time_ts,
                        APIToken.create_time <= end_time_ts
                    ])

                member_stats_list = (
                    APIToken
                    .select(
                        APIToken.tenant_id,
                        fn.SUM(APIToken.token).alias("total_tokens"),
                        fn.COUNT(APIToken.dialog_id).alias("dialog_count")
                    )
                    .where(*conditions)
                    .group_by(APIToken.tenant_id)
                    .dicts()
                )

                stats_map = {
                    stat["tenant_id"]: stat
                    for stat in member_stats_list
                }

                for m in members:
                    user_id = m["user_id"]
                    nickname = m.get("nickname") or ""

                    stat = stats_map.get(
                        user_id,
                        {
                            "total_tokens": 0,
                            "dialog_count": 0
                        }
                    )

                    tokens = int(stat["total_tokens"] or 0)
                    dialogs = int(stat["dialog_count"] or 0)

                    total_tokens += tokens
                    total_dialogs += dialogs

                    member_list.append({
                        "user_id": user_id,
                        "nickname": nickname,
                        "token_usage": tokens,
                        "dialog_count": dialogs
                    })

            final_result.append({
                "group_id": group.group_id,
                "group_name": group.group_name,
                "period": period,

                # 给前端/调试看的可读时间
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else None,
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S") if end_time else None,

                # 如果你想调试，也可以返回时间戳
                "start_time_ts": start_time_ts,
                "end_time_ts": end_time_ts,

                "total_tokens": total_tokens,
                "total_dialogs": total_dialogs,
                "members": member_list
            })
        group_order = {
            "工艺研究一室": 0,
            "工艺研究二室": 1,
            "工艺研究三室": 2,
            "新品事业部研发部": 3,
        }   
        final_result.sort(
            key=lambda item: group_order.get(item.get("group_name"), 999)
        )

        return get_json_result(data=final_result)

    except Exception as e:
        return server_error_response(e)

@manager.route('/new_token', methods=['POST'])  # noqa: F821
@login_required
async def new_token():
    req = await get_request_json()
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")

        tenant_id = tenants[0].tenant_id
        obj = {"tenant_id": tenant_id, "token": generate_confirmation_token(),
               "create_time": current_timestamp(),
               "create_date": datetime_format(datetime.now()),
               "update_time": None,
               "update_date": None
               }
        if req.get("canvas_id"):
            obj["dialog_id"] = req["canvas_id"]
            obj["source"] = "agent"
        else:
            obj["dialog_id"] = req["dialog_id"]

        if not APITokenService.save(**obj):
            return get_data_error_result(message="Fail to new a dialog!")

        return get_json_result(data=obj)
    except Exception as e:
        return server_error_response(e)


@manager.route('/token_list', methods=['GET'])  # noqa: F821
@login_required
def token_list():
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")

        id = request.args["dialog_id"] if "dialog_id" in request.args else request.args["canvas_id"]
        objs = APITokenService.query(tenant_id=tenants[0].tenant_id, dialog_id=id)
        return get_json_result(data=[o.to_dict() for o in objs])
    except Exception as e:
        return server_error_response(e)


@manager.route('/rm', methods=['POST'])  # noqa: F821
@validate_request("tokens", "tenant_id")
@login_required
async def rm():
    req = await get_request_json()
    try:
        for token in req["tokens"]:
            APITokenService.filter_delete(
                [APIToken.tenant_id == req["tenant_id"], APIToken.token == token])
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route('/stats', methods=['GET'])  # noqa: F821
@login_required
def stats():
    try:
        tenants = UserTenantService.query(user_id=current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")
        objs = API4ConversationService.stats(
            tenants[0].tenant_id,
            request.args.get(
                "from_date",
                (datetime.now() -
                 timedelta(
                     days=7)).strftime("%Y-%m-%d 00:00:00")),
            request.args.get(
                "to_date",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "agent" if "canvas_id" in request.args else None)

        res = {"pv": [], "uv": [], "speed": [], "tokens": [], "round": [], "thumb_up": []}

        for obj in objs:
            dt = obj["dt"]
            res["pv"].append((dt, obj["pv"]))
            res["uv"].append((dt, obj["uv"]))
            res["speed"].append((dt, float(obj["tokens"]) / (float(obj["duration"]) + 0.1))) # +0.1 to avoid division by zero
            res["tokens"].append((dt, float(obj["tokens"]) / 1000.0)) # convert to thousands
            res["round"].append((dt, obj["round"]))
            res["thumb_up"].append((dt, obj["thumb_up"]))

        return get_json_result(data=res)
    except Exception as e:
        return server_error_response(e)
