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
from api.db.db_models import APIToken, Dialog, Conversation, User
from api.db.services.api_service import APITokenService, API4ConversationService
from api.db.services.user_service import UserTenantService
from api.utils.api_utils import generate_confirmation_token, get_data_error_result, get_json_result, get_request_json, server_error_response, validate_request
from common.time_utils import current_timestamp, datetime_format
from api.apps import login_required, current_user

import csv
import io
import openpyxl
from flask import Response
# ... 其他已有的 import
@manager.route('/user_dialogs_export_excel', methods=['POST'])
async def export_user_dialogs_excel():
    import time

    t = time.time()
    req = await get_request_json()
    tenant_id = req.get("tenant_id")
    dialog_id = req.get("dialog_id")

    if not tenant_id:
        return get_data_error_result(message="Tenant_id not found!")

    if not dialog_id:
        return get_data_error_result(message="Dialog_id not found!")

    try:
        import io
        import json
        from peewee import fn
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        # 1. 查询 Token 和对话次数统计
        token_stat = (
            APIToken.select(
                fn.SUM(APIToken.token).alias("total_tokens"),
                fn.COUNT(APIToken.dialog_id).alias("dialog_count")
            )
            .where(APIToken.dialog_id == dialog_id)
            .dicts()
            .first()
        )

        total_tokens = (
            int(token_stat["total_tokens"])
            if token_stat and token_stat["total_tokens"]
            else 0
        )
        dialog_count = (
            int(token_stat["dialog_count"])
            if token_stat and token_stat["dialog_count"]
            else 0
        )

        # 2. 查询用户昵称
        user = (
            User
            .select(User.id, User.nickname)
            .where(User.id == tenant_id)
            .first()
        )
        user_name = user.nickname if user else tenant_id

        # 3. 查询智能体
        dialog = (
            Dialog
            .select(Dialog.id, Dialog.name, Dialog.tenant_id)
            .where(
                (Dialog.id == dialog_id) &
                (Dialog.tenant_id == tenant_id)
            )
            .first()
        )

        if not dialog:
            return get_data_error_result(message="Dialog not found!")

        # 4. 查询 conversation，只查需要字段
        conversations = list(
            Conversation
            .select(Conversation.id, Conversation.message)
            .where(
                (Conversation.dialog_id == dialog_id) &
                (Conversation.user_id == tenant_id)
            )
            .order_by(Conversation.id)
        )

        # 5. 创建 Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "对话记录"

        headers = [
            "智能体名称",
            "用户名称",
            "Conversation ID",
            "消息序号",
            "发送者",
            "消息详情",
            "总 Token 消耗",
            "对话次数"
        ]

        ws.append(headers)

        # 样式
        header_fill = PatternFill("solid", fgColor="D9EAF7")
        header_font = Font(bold=True)
        center_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        thin_side = Side(style="thin", color="CCCCCC")
        border = Border(
            left=thin_side,
            right=thin_side,
            top=thin_side,
            bottom=thin_side
        )

        # 表头样式
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_alignment
            cell.border = border

        current_row = 2
        data_start_row = current_row

        for c in conversations:
            conversation_start_row = current_row

            # 解析消息
            try:
                msg_data = c.message

                if isinstance(msg_data, str):
                    msg_list = json.loads(msg_data)
                else:
                    msg_list = msg_data

                if isinstance(msg_list, list):
                    messages = msg_list
                else:
                    messages = [{"role": "unknown", "content": str(msg_list)}]

            except Exception:
                messages = [{"role": "unknown", "content": str(c.message)}]

            if not messages:
                messages = [{"role": "", "content": ""}]

            for index, msg in enumerate(messages, start=1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if isinstance(content, (dict, list)):
                    content = json.dumps(content, ensure_ascii=False)

                safe_content = str(content).replace("\r", "")

                ws.append([
                    dialog.name,
                    user_name,
                    c.id,
                    index,
                    role,
                    safe_content,
                    total_tokens,
                    dialog_count
                ])

                # 直接给当前行设置样式，避免后面再全表遍历
                for col_idx in range(1, 9):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.border = border
                    cell.alignment = left_alignment if col_idx == 6 else center_alignment

                current_row += 1

            conversation_end_row = current_row - 1

            # 合并同一个 conversation_id
            if conversation_start_row < conversation_end_row:
                ws.merge_cells(
                    start_row=conversation_start_row,
                    start_column=3,
                    end_row=conversation_end_row,
                    end_column=3
                )

            ws.cell(row=conversation_start_row, column=3).alignment = center_alignment
            ws.cell(row=conversation_start_row, column=3).border = border

        data_end_row = current_row - 1

        # 6. 合并智能体名称、用户名称、Token、对话次数
        if data_start_row <= data_end_row:
            if data_start_row < data_end_row:
                ws.merge_cells(
                    start_row=data_start_row,
                    start_column=1,
                    end_row=data_end_row,
                    end_column=1
                )
                ws.merge_cells(
                    start_row=data_start_row,
                    start_column=2,
                    end_row=data_end_row,
                    end_column=2
                )
                ws.merge_cells(
                    start_row=data_start_row,
                    start_column=7,
                    end_row=data_end_row,
                    end_column=7
                )
                ws.merge_cells(
                    start_row=data_start_row,
                    start_column=8,
                    end_row=data_end_row,
                    end_column=8
                )

            for col_idx in [1, 2, 7, 8]:
                cell = ws.cell(row=data_start_row, column=col_idx)
                cell.alignment = center_alignment
                cell.border = border

        # 7. 设置列宽
        column_widths = {
            1: 20,
            2: 20,
            3: 36,
            4: 10,
            5: 15,
            6: 80,
            7: 18,
            8: 12
        }

        for col_idx, width in column_widths.items():
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        ws.freeze_panes = "A2"

        # 8. 导出 Excel
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=dialog_logs_{dialog_id}.xlsx"
            }
        )

        print(response)
        print("后端:", time.time() - t)
        output.close()

        return response

    except Exception as e:
        print(f"Export Excel Error: {e}")
        return server_error_response(e)

@manager.route('/user_dialogs_and_conversations', methods=['POST'])
# @login_required
async def get_user_dialogs_and_conversations():
    req = await get_request_json()
    tenant_id = req.get("tenant_id")

    if not tenant_id:
        return get_data_error_result(message="Tenant_id not found!")

    try:
        # 1. 查询该租户下的所有 Dialog
        dialogs = Dialog.select().where(Dialog.tenant_id == tenant_id)

        # 2. 查询该租户下的所有 Conversation
        conversations = Conversation.select().where(Conversation.user_id == tenant_id)

        # 3. 【核心优化】将 Conversation 转换为以 dialog_id 为键的字典，实现 O(1) 查找
        # 这样避免了在遍历 Dialog 时再去遍历 Conversation（避免 O(N*M) 的嵌套循环）
        conv_map = {}
        for c in conversations:
            if c.dialog_id not in conv_map:
                conv_map[c.dialog_id] = []
            conv_map[c.dialog_id].append({
                "id": c.id,
                "name": c.name,
                "message": c.message
            })

        # 4. 组装最终的树状结构
        dialog_list = []
        for d in dialogs:
            dialog_list.append({
                "id": d.id,
                "name": d.name,
                "conversations": conv_map.get(d.id, [])  # 直接取出该 Dialog 下的所有对话，如果没有则为空列表
            })
        print(dialog_list)
        return get_json_result(data=dialog_list)

    except Exception as e:
        return server_error_response(e)
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

        req = await get_request_json()
        req = req or {}

        period = req.get("period", "all")

        if period not in ["all", "day", "week", "month", "year"]:
            period = "all"

        now = datetime.now()

        start_time = None
        end_time = None
        start_time_ts = None
        end_time_ts = None

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
            start_time = None
            end_time = None

        if start_time and end_time:
            start_time_ts = int(start_time.timestamp() * 1000)
            end_time_ts = int(end_time.timestamp() * 1000)

        def ms_to_date(ms):
            return datetime.fromtimestamp(int(ms) / 1000).strftime("%Y-%m-%d")

        def ms_to_datetime(ms):
            return datetime.fromtimestamp(int(ms) / 1000)

        def build_day_items_by_range(range_start, range_end):
            if not range_start or not range_end:
                return []

            current_day = range_start.replace(hour=0, minute=0, second=0, microsecond=0)
            last_day = range_end.replace(hour=0, minute=0, second=0, microsecond=0)

            days = []

            while current_day <= last_day:
                days.append({
                    "date": current_day.strftime("%Y-%m-%d"),
                    "tokens": 0
                })
                current_day += timedelta(days=1)

            return days

        def build_week_day_items(week_start):
            days = []

            for i in range(7):
                day = week_start + timedelta(days=i)
                days.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "tokens": 0
                })

            return days

        groups = Group.select()
        final_result = []

        for group in groups:
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
            daily_tokens = []

            if tenant_ids:
                conditions = [
                    APIToken.tenant_id.in_(tenant_ids)
                ]

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

                group_token_rows = list(
                    APIToken
                    .select(
                        APIToken.create_time,
                        APIToken.token
                    )
                    .where(*conditions)
                    .dicts()
                )

                if period == "week" and start_time:
                    daily_tokens = build_week_day_items(start_time)

                elif period != "all":
                    daily_tokens = build_day_items_by_range(start_time, end_time)

                else:
                    create_times = [
                        int(row["create_time"])
                        for row in group_token_rows
                        if row.get("create_time")
                    ]

                    if create_times:
                        group_start_time = ms_to_datetime(min(create_times))
                        group_end_time = ms_to_datetime(max(create_times))
                        daily_tokens = build_day_items_by_range(
                            group_start_time,
                            group_end_time
                        )
                    else:
                        daily_tokens = []

                daily_token_map = {
                    item["date"]: item
                    for item in daily_tokens
                }

                for row in group_token_rows:
                    create_time = row.get("create_time")
                    token = int(row.get("token") or 0)

                    if not create_time:
                        continue

                    day_key = ms_to_date(create_time)

                    if day_key in daily_token_map:
                        daily_token_map[day_key]["tokens"] += token

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

                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else None,
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S") if end_time else None,

                "start_time_ts": start_time_ts,
                "end_time_ts": end_time_ts,

                "total_tokens": total_tokens,
                "total_dialogs": total_dialogs,
                "daily_tokens": daily_tokens,
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

        print(final_result)
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
