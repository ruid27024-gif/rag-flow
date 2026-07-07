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
import json
import logging
import string
import os
import re
import secrets
import time
from datetime import datetime
import base64

from quart import make_response, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from api.apps.auth import get_auth_client
from api.db import FileType, UserTenantRole
from api.db.db_models import TenantLLM, AdminUser, User, UserGroup, SyncPerson, SyncDept
from peewee import JOIN
from api.db.services.file_service import FileService
from api.db.services.llm_service import get_init_tenant_llm
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.user_service import TenantService, UserService, UserTenantService
from common.time_utils import current_timestamp, datetime_format, get_format_time
from common.misc_utils import download_img, get_uuid
from common.constants import RetCode
from common import settings
from common.connection_utils import construct_response
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    get_request_json,
    server_error_response,
    validate_request,
)
from api.utils.crypt import decrypt,crypt2, crypt
from rag.utils.redis_conn import REDIS_CONN
from api.apps import login_required, current_user, login_user, logout_user
from api.utils.web_utils import (
    send_email_html,
    OTP_LENGTH,
    OTP_TTL_SECONDS,
    ATTEMPT_LIMIT,
    ATTEMPT_LOCK_SECONDS,
    RESEND_COOLDOWN_SECONDS,
    otp_keys,
    hash_code,
    captcha_key,
)
from common import settings
from common.http_client import async_request


@manager.route("/login", methods=["POST", "GET"])  # noqa: F821
async def login():
    """
    User login endpoint.
    ---
    tags:
      - User
    parameters:
      - in: body
        name: body
        description: Login credentials.
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              description: User email.
            password:
              type: string
              description: User password.
    responses:
      200:
        description: Login successful.
        schema:
          type: object
      401:
        description: Authentication failed.
        schema:
          type: object
    """
    json_body = await get_request_json()
    if not json_body:
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="Unauthorized!")

    email = json_body.get("email", "")
    if email == "admin@ragflow.io":
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="Default admin account cannot be used to login normal services!")
    
    users = UserService.query(email=email)
    if not users:
        return get_json_result(
            data=False,
            code=RetCode.AUTHENTICATION_ERROR,
            message=f"Email: {email} is not registered!",
        )

    password = json_body.get("password")
    print(password)

    try:
        password = decrypt(password)
        user = UserService.query_user(email, password)
        
    except BaseException:
        # return get_json_result(data=False, code=RetCode.SERVER_ERROR, message="Fail to crypt password")
        if password == UserService.query_user_by_email(email=email)[0].password:
            user = UserService.query_user_by_email(email=email)[0]

        else:
            return get_json_result(data=False, code=RetCode.SERVER_ERROR, message="Fail to crypt password")





    if user and hasattr(user, 'is_active') and user.is_active == "0":
        return get_json_result(
            data=False,
            code=RetCode.FORBIDDEN,
            message="This account has been disabled, please contact the administrator!",
        )
    elif user:
        response_data = user.to_json()
        user.access_token = get_uuid()
        login_user(user)
        user.update_time = current_timestamp()
        user.update_date = datetime_format(datetime.now())
        user.save()
        msg = "Welcome back!"

        return await construct_response(data=response_data, auth=user.get_id(), message=msg)
    else:
        return get_json_result(
            data=False,
            code=RetCode.AUTHENTICATION_ERROR,
            message="Email and password do not match!",
        )


@manager.route("/login/channels", methods=["GET"])  # noqa: F821
async def get_login_channels():
    """
    Get all supported authentication channels.
    """
    try:
        channels = []
        for channel, config in settings.OAUTH_CONFIG.items():
            channels.append(
                {
                    "channel": channel,
                    "display_name": config.get("display_name", channel.title()),
                    "icon": config.get("icon", "sso"),
                }
            )
        return get_json_result(data=channels)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=[], message=f"Load channels failure, error: {str(e)}", code=RetCode.EXCEPTION_ERROR)


@manager.route("/login/<channel>", methods=["GET"])  # noqa: F821
async def oauth_login(channel):
    channel_config = settings.OAUTH_CONFIG.get(channel)
    if not channel_config:
        raise ValueError(f"Invalid channel name: {channel}")
    auth_cli = get_auth_client(channel_config)

    state = get_uuid()
    session["oauth_state"] = state
    auth_url = auth_cli.get_authorization_url(state)
    return redirect(auth_url)


@manager.route("/oauth/callback/<channel>", methods=["GET"])  # noqa: F821
async def oauth_callback(channel):
    """
    Handle the OAuth/OIDC callback for various channels dynamically.
    """
    try:
        channel_config = settings.OAUTH_CONFIG.get(channel)
        if not channel_config:
            raise ValueError(f"Invalid channel name: {channel}")
        auth_cli = get_auth_client(channel_config)

        # Check the state
        state = request.args.get("state")
        if not state or state != session.get("oauth_state"):
            return redirect("/?error=invalid_state")
        session.pop("oauth_state", None)

        # Obtain the authorization code
        code = request.args.get("code")
        if not code:
            return redirect("/?error=missing_code")

        # Exchange authorization code for access token
        if hasattr(auth_cli, "async_exchange_code_for_token"):
            token_info = await auth_cli.async_exchange_code_for_token(code)
        else:
            token_info = auth_cli.exchange_code_for_token(code)
        access_token = token_info.get("access_token")
        if not access_token:
            return redirect("/?error=token_failed")

        id_token = token_info.get("id_token")

        # Fetch user info
        if hasattr(auth_cli, "async_fetch_user_info"):
            user_info = await auth_cli.async_fetch_user_info(access_token, id_token=id_token)
        else:
            user_info = auth_cli.fetch_user_info(access_token, id_token=id_token)
        if not user_info.email:
            return redirect("/?error=email_missing")

        # Login or register
        users = UserService.query(email=user_info.email)
        user_id = get_uuid()

        if not users:
            try:
                try:
                    avatar = download_img(user_info.avatar_url)
                except Exception as e:
                    logging.exception(e)
                    avatar = ""

                users = user_register(
                    user_id,
                    {
                        "access_token": get_uuid(),
                        "email": user_info.email,
                        "avatar": avatar,
                        "nickname": user_info.nickname,
                        "login_channel": channel,
                        "last_login_time": get_format_time(),
                        "is_superuser": False,
                    },
                )

                if not users:
                    raise Exception(f"Failed to register {user_info.email}")
                if len(users) > 1:
                    raise Exception(f"Same email: {user_info.email} exists!")

                # Try to log in
                user = users[0]
                login_user(user)
                return redirect(f"/?auth={user.get_id()}")

            except Exception as e:
                rollback_user_registration(user_id)
                logging.exception(e)
                return redirect(f"/?error={str(e)}")

        # User exists, try to log in
        user = users[0]
        user.access_token = get_uuid()
        if user and hasattr(user, 'is_active') and user.is_active == "0":
            return redirect("/?error=user_inactive")

        login_user(user)
        user.save()
        return redirect(f"/?auth={user.get_id()}")
    except Exception as e:
        logging.exception(e)
        return redirect(f"/?error={str(e)}")


@manager.route("/github_callback", methods=["GET"])  # noqa: F821
async def github_callback():
    """
    **Deprecated**, Use `/oauth/callback/<channel>` instead.

    GitHub OAuth callback endpoint.
    ---
    tags:
      - OAuth
    parameters:
      - in: query
        name: code
        type: string
        required: true
        description: Authorization code from GitHub.
    responses:
      200:
        description: Authentication successful.
        schema:
          type: object
    """
    res = await async_request(
        "POST",
        settings.GITHUB_OAUTH.get("url"),
        data={
            "client_id": settings.GITHUB_OAUTH.get("client_id"),
            "client_secret": settings.GITHUB_OAUTH.get("secret_key"),
            "code": request.args.get("code"),
        },
        headers={"Accept": "application/json"},
    )
    res = res.json()
    if "error" in res:
        return redirect("/?error=%s" % res["error_description"])

    if "user:email" not in res["scope"].split(","):
        return redirect("/?error=user:email not in scope")

    session["access_token"] = res["access_token"]
    session["access_token_from"] = "github"
    user_info = await user_info_from_github(session["access_token"])
    email_address = user_info["email"]
    users = UserService.query(email=email_address)
    user_id = get_uuid()
    if not users:
        # User isn't try to register
        try:
            try:
                avatar = download_img(user_info["avatar_url"])
            except Exception as e:
                logging.exception(e)
                avatar = ""
            users = user_register(
                user_id,
                {
                    "access_token": session["access_token"],
                    "email": email_address,
                    "avatar": avatar,
                    "nickname": user_info["login"],
                    "login_channel": "github",
                    "last_login_time": get_format_time(),
                    "is_superuser": False,
                },
            )
            if not users:
                raise Exception(f"Fail to register {email_address}.")
            if len(users) > 1:
                raise Exception(f"Same email: {email_address} exists!")

            # Try to log in
            user = users[0]
            login_user(user)
            return redirect("/?auth=%s" % user.get_id())
        except Exception as e:
            rollback_user_registration(user_id)
            logging.exception(e)
            return redirect("/?error=%s" % str(e))

    # User has already registered, try to log in
    user = users[0]
    user.access_token = get_uuid()
    if user and hasattr(user, 'is_active') and user.is_active == "0":
        return redirect("/?error=user_inactive")
    login_user(user)
    user.save()
    return redirect("/?auth=%s" % user.get_id())


@manager.route("/feishu_callback", methods=["GET"])  # noqa: F821
async def feishu_callback():
    """
    Feishu OAuth callback endpoint.
    ---
    tags:
      - OAuth
    parameters:
      - in: query
        name: code
        type: string
        required: true
        description: Authorization code from Feishu.
    responses:
      200:
        description: Authentication successful.
        schema:
          type: object
    """
    app_access_token_res = await async_request(
        "POST",
        settings.FEISHU_OAUTH.get("app_access_token_url"),
        data=json.dumps(
            {
                "app_id": settings.FEISHU_OAUTH.get("app_id"),
                "app_secret": settings.FEISHU_OAUTH.get("app_secret"),
            }
        ),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    app_access_token_res = app_access_token_res.json()
    if app_access_token_res["code"] != 0:
        return redirect("/?error=%s" % app_access_token_res)

    res = await async_request(
        "POST",
        settings.FEISHU_OAUTH.get("user_access_token_url"),
        data=json.dumps(
            {
                "grant_type": settings.FEISHU_OAUTH.get("grant_type"),
                "code": request.args.get("code"),
            }
        ),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {app_access_token_res['app_access_token']}",
        },
    )
    res = res.json()
    if res["code"] != 0:
        return redirect("/?error=%s" % res["message"])

    if "contact:user.email:readonly" not in res["data"]["scope"].split():
        return redirect("/?error=contact:user.email:readonly not in scope")
    session["access_token"] = res["data"]["access_token"]
    session["access_token_from"] = "feishu"
    user_info = await user_info_from_feishu(session["access_token"])
    email_address = user_info["email"]
    users = UserService.query(email=email_address)
    user_id = get_uuid()
    if not users:
        # User isn't try to register
        try:
            try:
                avatar = download_img(user_info["avatar_url"])
            except Exception as e:
                logging.exception(e)
                avatar = ""
            users = user_register(
                user_id,
                {
                    "access_token": session["access_token"],
                    "email": email_address,
                    "avatar": avatar,
                    "nickname": user_info["en_name"],
                    "login_channel": "feishu",
                    "last_login_time": get_format_time(),
                    "is_superuser": False,
                },
            )
            if not users:
                raise Exception(f"Fail to register {email_address}.")
            if len(users) > 1:
                raise Exception(f"Same email: {email_address} exists!")

            # Try to log in
            user = users[0]
            login_user(user)
            return redirect("/?auth=%s" % user.get_id())
        except Exception as e:
            rollback_user_registration(user_id)
            logging.exception(e)
            return redirect("/?error=%s" % str(e))

    # User has already registered, try to log in
    user = users[0]
    if user and hasattr(user, 'is_active') and user.is_active == "0":
        return redirect("/?error=user_inactive")
    user.access_token = get_uuid()
    login_user(user)
    user.save()
    return redirect("/?auth=%s" % user.get_id())


async def user_info_from_feishu(access_token):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {access_token}",
    }
    res = await async_request("GET", "https://open.feishu.cn/open-apis/authen/v1/user_info", headers=headers)
    user_info = res.json()["data"]
    user_info["email"] = None if user_info.get("email") == "" else user_info["email"]
    return user_info


async def user_info_from_github(access_token):
    headers = {"Accept": "application/json", "Authorization": f"token {access_token}"}
    res = await async_request("GET", f"https://api.github.com/user?access_token={access_token}", headers=headers)
    user_info = res.json()
    email_info_response = await async_request(
        "GET",
        f"https://api.github.com/user/emails?access_token={access_token}",
        headers=headers,
    )
    email_info = email_info_response.json()
    user_info["email"] = next((email for email in email_info if email["primary"]), None)["email"]
    return user_info


@manager.route("/logout", methods=["GET"])  # noqa: F821
@login_required
async def log_out():
    """
    User logout endpoint.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Logout successful.
        schema:
          type: object
    """
    current_user.access_token = f"INVALID_{secrets.token_hex(16)}"
    current_user.save()
    logout_user()
    return get_json_result(data=True)


@manager.route("/setting", methods=["POST"])  # noqa: F821
@login_required
async def setting_user():
    """
    Update user settings.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: User settings to update.
        required: true
        schema:
          type: object
          properties:
            nickname:
              type: string
              description: New nickname.
            email:
              type: string
              description: New email.
    responses:
      200:
        description: Settings updated successfully.
        schema:
          type: object
    """
    update_dict = {}
    request_data = await get_request_json()
    if request_data.get("password"):
        new_password = request_data.get("new_password")
        if not check_password_hash(current_user.password, decrypt(request_data["password"])):
            return get_json_result(
                data=False,
                code=RetCode.AUTHENTICATION_ERROR,
                message="Password error!",
            )

        if new_password:
            update_dict["password"] = generate_password_hash(decrypt(new_password))

    for k in request_data.keys():
        if k in [
            "password",
            "new_password",
            "email",
            "status",
            "is_superuser",
            "login_channel",
            "is_anonymous",
            "is_active",
            "is_authenticated",
            "last_login_time",
        ]:
            continue
        update_dict[k] = request_data[k]

    try:
        UserService.update_by_id(current_user.id, update_dict)
        return get_json_result(data=True)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, message="Update failure!", code=RetCode.EXCEPTION_ERROR)


@manager.route("/info", methods=["GET"])  # noqa: F821
@login_required
async def user_profile():
    """
    Get user profile information.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: User profile retrieved successfully.
        schema:
          type: object
          properties:
            id:
              type: string
              description: User ID.
            nickname:
              type: string
              description: User nickname.
            email:
              type: string
              description: User email.
    """
    data = current_user.to_dict()
    admin_users = AdminUser.query(user_id=current_user.id)
    data["is_admin_user"] = any(u.role_level == 1 for u in admin_users)
    data["role_level"] = min([u.role_level for u in admin_users]) if admin_users else None
    print(data)
    return get_json_result(data=data)


# @manager.route("/group_admins", methods=["GET"])  # noqa: F821
# @login_required
# async def group_admins():
#     """
#     Get group administrators (role_level=2).
#     ---
#     tags:
#       - User
#     security:
#       - ApiKeyAuth: []
#     responses:
#       200:
#         description: List of group administrators.
#         schema:
#           type: array
#           items:
#             type: object
#             properties:
#               user_id:
#                 type: string
#               nickname:
#                 type: string
#     """
#     try:
#         users = (User
#                  .select(User.id, User.nickname)
#                  .join(AdminUser, on=(User.id == AdminUser.user_id))
#                  .where(AdminUser.role_level == 2))
#         res = [{"user_id": u.id, "nickname": u.nickname} for u in users]
#         return get_json_result(data=res)
#     except Exception as e:
#         return server_error_response(e)

@manager.route("/group_admins", methods=["GET"])
@login_required
async def group_admins():
    """
    Get group administrators (role_level=2).
    """
    try:
        # 1. 组合你提供的复杂查询逻辑
        query = (
            User
            .select(
                User.id,
                User.nickname,
                SyncPerson.phone,
                SyncPerson.gender,
                SyncDept.mdmCode,         
                SyncDept.nameOfAdminOrg, 
                SyncDept.corporateName 
            )
            # 关联 SyncPerson 表
            .join(
                SyncPerson, 
                on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                join_type=JOIN.LEFT_OUTER
            )
            .switch(User)
            # 关联 SyncDept 表
            .join(
                SyncDept, 
                on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                join_type=JOIN.LEFT_OUTER
            )
            # 2. 继续保留原有的 AdminUser 筛选条件
            .join(AdminUser, on=(User.id == AdminUser.user_id))
            .where(AdminUser.role_level == 2)
            .order_by(SyncDept.mdmCode.asc(nulls='last'))
        )

        # 3. 遍历查询结果并组装数据
        res = []
        for u in query:
            res.append({
                "user_id": u.id,
                "nickname": u.nickname,
                # 提取关联表数据（注意处理 LEFT JOIN 可能导致的 None 情况）
                "phone": u.syncperson.phone if u.syncperson else None,
                "gender": u.syncperson.gender if u.syncperson else None,
                "mdmCode": u.syncdept.mdmCode if u.syncdept else None,
                "nameOfAdminOrg": u.syncdept.nameOfAdminOrg if u.syncdept else None,
                "corporateName": u.syncdept.corporateName if u.syncdept else None,
            })
            
        return get_json_result(data=res)
    except Exception as e:
        return server_error_response(e)

# 任命为组管理员 先1键拉在取，再任命
@manager.route("/group_admin/new_all", methods=["POST"])  # noqa: F821
@login_required
async def add_group_admin_all():
    """
    将管理员加入组管理表
    将管理员的根加入到2级表

    """

    req = await get_request_json()
    user_id = req.get("user_id")
    group_id = req.get("group_id")

    if not user_id:
        return get_json_result(data=False, message="user_id is required", code=RetCode.ARGUMENT_ERROR)

    try:
        if AdminUser.query(user_id=user_id):
            return get_json_result(data=False, message="User is already an admin", code=RetCode.DATA_ERROR)

        AdminUser.insert(user_id=user_id, role_level=2).execute()
        # 获取拉取人员的根目录
        file = FileService.get_root_folder(user_id)
        pf_id = file['id']
        print(pf_id)
        # 将当前人员根目录存入到二级表
        from api.db.services.file_group_service import FileGroupService
        file2 = FileGroupService.insert({
            "id": pf_id,  # 昵称的id
            "parent_id": pf_id,
            "tenant_id": user_id,
            "created_by": user_id,
            "name": "/",
            "location": "",
            "size": 0,
            "type": FileType.FOLDER.value,
            "source_type":FileType.Adminowner.value
        })

        # 将参考库挂载到当前人员(二级表)
        from api.db.db_models import File, File_Group
        file_ref = File.select().where((File.parent_id == File.id)
                        & (File.tenant_id == settings.REFERENCE_TENANT_ID )).first()
        # 全局参考库id
        file_ref_dict = file_ref.to_dict()
        file_ref_dict["parent_id"] = pf_id
        file_ref_dict["name"] = "全局参考库"
        file_ref_dict["type"] = FileType.FOLDER.value
        file_ref_dict["source_type"] = FileType.Adminowner.value

        File_Group.create(**file_ref_dict)

        file_group = File_Group.select().where((File_Group.parent_id == file_ref.id)
                                               & (File_Group.tenant_id == settings.REFERENCE_TENANT_ID)
                                               )

        # 把参考库中不是根目录的全部写入二级表
        file = File.select().where((File.id != File.parent_id)
                                   & (File.tenant_id == settings.REFERENCE_TENANT_ID)
                                   )

        # 如果二级表中不存在参考库 非根目录写入
        if not file_group.exists():
            for i in file:
                i.to_dict()
                print(i.to_dict())
                try:
                    File_Group.create(**i.to_dict())
                except:
                    pass

        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        if group_id and group_id in cfg_map and cfg_map[group_id]:
            group_public_id = cfg_map[group_id]

            # 获取当前组参考库的根
            file_ref = FileService.get_root_folder(group_public_id)
            pf_id_ref = file_ref['id']

            # 把当前组参考库挂载到这个根上 根据组id获取参考库的id
            file2 = FileGroupService.insert({
                "id": pf_id_ref,  # 昵称的id
                "parent_id": pf_id,
                "tenant_id": user_id,
                "created_by": user_id,
                "name": "组参考库+文献库",
                "location": "",
                "size": 0,
                "type": FileType.FOLDER.value,
                "source_type":FileType.Adminowner.value
            })

            # 把参考库下的所有非根文件挂载到当前的组参考库下
            from api.db.db_models import File, File_Group

            file_group_ref = File.select().where((File.id != File.parent_id)
                            & (File.tenant_id == group_public_id )
                            )

            file_group2 = File_Group.select().where((File_Group.parent_id == pf_id_ref)
                                                    & (File_Group.tenant_id == group_public_id)
                                                    )

            # 如果之前二级表中不存在就写入
            if not file_group2.exists():
            # 将文件全部写入到全局参考库下
                for i in file_group_ref:
                    i.to_dict()
                    print(i.to_dict())
                    try:
                        File_Group.create(**i.to_dict())
                    except:
                        pass

        # 将组内人员全部挂载到当前组长下
        # 根据组id获取组名称
        from api.db.services.group_service import GroupService
        group_name = GroupService.get_name_by_id(group_id)

        # 通过组名称获取所有人
        persons = SyncPerson.select().where(SyncPerson.organize == group_name)
        # 触发查询并遍历
        for p in persons:
            # 打印具体的字段，比如名字、手机号等

            print(p.mdmName, p.phone, p.organize)

        print("把人员放到二级表")
        # 遍历每一个人,把每一个人挂在二级管理员
        for person in persons:
            # 获取每一个人的账号
            phone = person.phone
            name = person.mdmName

            # 过滤掉自己
            if User.email != phone:
            # 通过账号获取每一个人的id
                try:
                    # 尝试获取匹配该邮箱的用户对象
                    user = User.get(User.email == phone)
                    # 获取该用户的 id
                    user_id = user.id
                    print(f"获取到的用户ID为: {user_id}")

                    # add_user = UserService.filter_by_id(user_id)
                    # 获取当前人员的根
                    file_mem = FileService.get_root_folder(user_id)
                    person_id = file_mem['id']

                    # 
                    file2 = FileGroupService.insert({
                        "id": person_id,  # 昵称的id
                        "parent_id": pf_id,
                        "tenant_id": user_id,
                        "created_by": user_id,
                        "name": name,
                        "location": "",
                        "size": 0,
                        "type": FileType.FOLDER.value,
                        "source_type":FileType.Adminowner.value
                    })
                except:
                    print("任命：组员写入二级表失败")

            # 当前人员的非根文件
            file_person_root_fei = File.select().where((File.id != File.parent_id)
                                                & (File.tenant_id == person_id)
                                                )

            file_person = File_Group.select().where((File_Group.parent_id == person_id)
                                                    & (File_Group.tenant_id == user_id)
                                                    )

            if not file_person.exists():
                for i in file_person_root_fei:
                    i.to_dict()

                    try:
                        File_Group.create(**i.to_dict())
                    except:
                        pass
                    

        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

@manager.route("/group_admin/candidates", methods=["GET"])  # noqa: F821
@login_required
async def group_admin_candidates():
    """
    Get candidates for group administrators (users not in AdminUser).
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: List of candidate users.
        schema:
          type: array
          items:
            type: object
            properties:
              user_id:
                type: string
              nickname:
                type: string
    """
    try:
        # Find users who are NOT in AdminUser table

        # 1. 构建多表联查的 Query（参考 list_candidate_users 的联表逻辑）
        query = (
            User
            .select(
                User.id,
                User.nickname,
                SyncPerson.phone,
                SyncPerson.gender,
                SyncDept.mdmCode,         
                SyncDept.nameOfAdminOrg, 
                SyncDept.corporateName 
            )
            # 关联 SyncPerson 表
            .join(
                SyncPerson, 
                on=(User.email.collate('utf8mb4_unicode_ci') == SyncPerson.phone),
                join_type=JOIN.LEFT_OUTER
            )
            .switch(User)
            # 关联 SyncDept 表
            .join(
                SyncDept, 
                on=(SyncPerson.organizationCode.collate('utf8mb4_0900_ai_ci') == SyncDept.mdmCode),
                join_type=JOIN.LEFT_OUTER
            )
        )

        subquery = AdminUser.select(AdminUser.user_id)
        excluded_ids = {row.user_id for row in subquery}  # 将查询结果转为集合

        # 2. 获取配置中的集合
        cfg_map = getattr(settings, "GROUP_REFERENCE_TENANT_MAP", {}) or {}
        group_ref_ids = set(cfg_map.values())

        # 3. 合并两个集合（方式一：使用 update 方法）
        excluded_ids.update(group_ref_ids)
        
        if settings.REFERENCE_TENANT_ID:
            # 同时排除 AdminUser 中的用户 和 参考租户ID
            users_query = query.where(
                User.id.not_in(subquery),
                User.id != settings.REFERENCE_TENANT_ID
            )
        else:
            # 仅排除 AdminUser 中的用户
            users_query = query.where(User.id.not_in(subquery))

        # 3. 执行查询并组装数据（增加空值保护）
        res = []
        for u in users_query:
            # 获取关联的 SyncPerson 和 SyncDept 对象，如果没有关联到则为 None
            sync_p = getattr(u, 'syncperson', None)
            sync_d = getattr(u, 'syncdept', None)
            
            res.append({
                "user_id": u.id, 
                "nickname": u.nickname, 
                "phone": sync_p.phone if sync_p else None,
                "gender": sync_p.gender if sync_p else None,
                "mdmCode": sync_d.mdmCode if sync_d else None, 
                "nameOfAdminOrg": sync_d.nameOfAdminOrg if sync_d else None, 
                "corporateName": sync_d.corporateName if sync_d else None
            })

        return get_json_result(data=res)
    except Exception as e:
        return server_error_response(e)
    



@manager.route("/group_admin/new", methods=["POST"])  # noqa: F821
@login_required
async def add_group_admin():
    """
    Add a group administrator.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: User ID to add as group admin.
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: string
    """
    req = await get_request_json()
    user_id = req.get("user_id")
    if not user_id:
        return get_json_result(data=False, message="user_id is required", code=RetCode.ARGUMENT_ERROR)

    try:
        if AdminUser.query(user_id=user_id):
             return get_json_result(data=False, message="User is already an admin", code=RetCode.DATA_ERROR)
        
        AdminUser.insert(user_id=user_id, role_level=2).execute()
        # 获取拉取人员的根目录
        file = FileService.get_root_folder(user_id)
        pf_id = file['id']

        # 将当前人员根目录存入到二级表
        from api.db.services.file_group_service import FileGroupService
        file2 = FileGroupService.insert({
        "id": pf_id,  # 昵称的id
        "parent_id": pf_id,
        "tenant_id": user_id,
        "created_by": user_id,
        "name": "/",
        "location": "",
        "size": 0,
        "type": FileType.FOLDER.value,
        "source_type":FileType.Adminowner.value
    })
        # 将参考库挂载到当前人员(二级表)
        from api.db.db_models import File, File_Group
        # 全局参考库id
        file_ref = File.select().where((File.parent_id == File.id)
                            & (File.tenant_id == settings.REFERENCE_TENANT_ID )).first()
        file_ref_dict = file_ref.to_dict()
        file_ref_dict["parent_id"] = pf_id
        file_ref_dict["name"] = "全局参考库"
        file_ref_dict["type"] = FileType.FOLDER.value
        file_ref_dict["source_type"] = FileType.Adminowner.value

        File_Group.create(**file_ref_dict)

        file_group = File_Group.select().where((File_Group.parent_id == file_ref.id)
                           & (File_Group.tenant_id == settings.REFERENCE_TENANT_ID )
                           )

        # 把参考库中不是根目录的全部写入二级表
        file = File.select().where((File.id != File.parent_id)
                           & (File.tenant_id == settings.REFERENCE_TENANT_ID )
                           )
        
        # 将文件全部写入到全局参考库下
        if not file_group.exists():
            for i in file:
                i.to_dict()
                print(i.to_dict())
                try:
                    File_Group.create(**i.to_dict())
                except:
                    pass

        # 将自己的非根目录下的文件全部写入二级表 
        # 当前人员的非根文件
        file_person_root_fei = File.select().where((File.id != File.parent_id)
                                                & (File.tenant_id == current_user.id)
                                                )
        for i in file_person_root_fei:
                i.to_dict()

                try:
                    File_Group.create(**i.to_dict())
                except:
                    pass
        
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/group_admin/delete_all", methods=["POST"])  # noqa: F821
@login_required
async def delete_group_admin_all():
    """
    Remove a group administrator.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: User ID to remove from group admins.
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: string
    """
    req = await get_request_json()
    user_id = req.get("user_id")
    group_id = req.get("group_id")
    print(group_id)

    if not user_id:
        return get_json_result(data=False, message="user_id is required", code=RetCode.ARGUMENT_ERROR)

    try:
        # Only allow deleting role_level=2 to prevent accidental deletion of super admins (if any)
        # Assuming role_level 2 is specific for group admins.
        # Check if user is actually a group admin before deleting?
        # Or just delete where user_id=... and role_level=2
        rows = AdminUser.delete().where((AdminUser.user_id == user_id) & (AdminUser.role_level == 2)).execute()

        from api.db.services.file_group_service import FileGroupService
        # 获取撤销人员的二级表根目录
        file = FileService.get_root_folder(user_id)
        pf_id = file['id']
        # 删除根目录下的所有内容
        FileGroupService.delete_by_pf_id(pf_id)

        if rows > 0:
            return get_json_result(data=True)
        else:
            return get_json_result(data=False, message="User is not a group admin or not found", code=RetCode.DATA_ERROR)
    except Exception as e:
        return server_error_response(e)


@manager.route("/group_admin/delete", methods=["POST"])  # noqa: F821
@login_required
async def delete_group_admin():
    """
    Remove a group administrator.
    ---
    tags:
      - User
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: User ID to remove from group admins.
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: string
    """
    req = await get_request_json()
    user_id = req.get("user_id")
    if not user_id:
        return get_json_result(data=False, message="user_id is required", code=RetCode.ARGUMENT_ERROR)

    try:
        # Only allow deleting role_level=2 to prevent accidental deletion of super admins (if any)
        # Assuming role_level 2 is specific for group admins.
        # Check if user is actually a group admin before deleting?
        # Or just delete where user_id=... and role_level=2
        rows = AdminUser.delete().where((AdminUser.user_id == user_id) & (AdminUser.role_level == 2)).execute()
        if rows > 0:
            return get_json_result(data=True)
        else:
            return get_json_result(data=False, message="User is not a group admin or not found", code=RetCode.DATA_ERROR)
    except Exception as e:
        return server_error_response(e)


def rollback_user_registration(user_id):
    try:
        UserService.delete_by_id(user_id)
    except Exception:
        pass
    try:
        TenantService.delete_by_id(user_id)
    except Exception:
        pass
    try:
        u = UserTenantService.query(tenant_id=user_id)
        if u:
            UserTenantService.delete_by_id(u[0].id)
    except Exception:
        pass
    try:
        TenantLLM.delete().where(TenantLLM.tenant_id == user_id).execute()
    except Exception:
        pass


def user_register(user_id, user):
    user["id"] = user_id
    tenant = {
        "id": user_id,
        "name": user["nickname"] + "‘s Kingdom",
        "llm_id": settings.CHAT_MDL,
        "embd_id": settings.EMBEDDING_MDL,
        "asr_id": settings.ASR_MDL,
        "parser_ids": settings.PARSERS,
        "img2txt_id": settings.IMAGE2TEXT_MDL,
        "rerank_id": settings.RERANK_MDL,
    }
    usr_tenant = {
        "tenant_id": user_id,
        "user_id": user_id,
        "invited_by": user_id,
        "role": UserTenantRole.OWNER,
    }
    file_id = get_uuid()
    file = {
        "id": file_id,
        "parent_id": file_id,
        "tenant_id": user_id,
        "created_by": user_id,
        "name": "/",
        "type": FileType.FOLDER.value,
        "size": 0,
        "location": "",
    }

    tenant_llm = get_init_tenant_llm(user_id)

    if not UserService.save(**user):
        return
    TenantService.insert(**tenant)
    UserTenantService.insert(**usr_tenant)
    TenantLLMService.insert_many(tenant_llm)
    FileService.insert(file)
    return UserService.query(email=user["email"])


@manager.route("/register", methods=["POST"])  # noqa: F821
@validate_request("nickname", "email", "password")
async def user_add():
    """
    Register a new user.
    ---
    tags:
      - User
    parameters:
      - in: body
        name: body
        description: Registration details.
        required: true
        schema:
          type: object
          properties:
            nickname:
              type: string
              description: User nickname.
            email:
              type: string
              description: User email.
            password:
              type: string
              description: User password.
    responses:
      200:
        description: Registration successful.
        schema:
          type: object
    """

    if not settings.REGISTER_ENABLED:
        return get_json_result(
            data=False,
            message="User registration is disabled!",
            code=RetCode.OPERATING_ERROR,
        )

    req = await get_request_json()
    email_address = req["email"]

    # Validate the email address
    # if not re.match(r"^[\w\._-]+@([\w_-]+\.)+[\w-]{2,}$", email_address):
    #     return get_json_result(
    #         data=False,
    #         message=f"Invalid email address: {email_address}!",
    #         code=RetCode.OPERATING_ERROR,
    #     )


    # 1. 定义手机号正则 (这里以中国大陆 11 位手机号为例)
    phone_pattern = r"^1[3-9]\d{9}$"

    # 2. 如果既不是邮箱，也不是手机号，则报错
    if not re.match(r"^[\w\._-]+@([\w_-]+\.)+[\w-]{2,}$", email_address) and not re.match(phone_pattern, email_address):
        return get_json_result(
            data=False,
            message=f"Invalid email or phone number: {email_address}!",
            code=RetCode.OPERATING_ERROR,
        )

    # Check if the email address is already used
    if UserService.query(email=email_address):
        return get_json_result(
            data=False,
            message=f"Email: {email_address} has already registered!",
            code=RetCode.OPERATING_ERROR,
        )

    # Construct user info data
    nickname = req["nickname"]
    user_dict = {
        "access_token": get_uuid(),
        "email": email_address,
        "nickname": nickname,
        "password": decrypt(req["password"]),
        "login_channel": "password",
        "last_login_time": get_format_time(),
        "is_superuser": False,
    }

    user_id = get_uuid()
    try:
        users = user_register(user_id, user_dict)
        if not users:
            raise Exception(f"Fail to register {email_address}.")
        if len(users) > 1:
            raise Exception(f"Same email: {email_address} exists!")
        user = users[0]
        login_user(user)
        return await construct_response(
            data=user.to_json(),
            auth=user.get_id(),
            message=f"{nickname}, welcome aboard!",
        )
    except Exception as e:
        rollback_user_registration(user_id)
        logging.exception(e)
        return get_json_result(
            data=False,
            message=f"User registration failure, error: {str(e)}",
            code=RetCode.EXCEPTION_ERROR,
        )


@manager.route("/tenant_info", methods=["GET"])  # noqa: F821
@login_required
async def tenant_info():
    """
    Get tenant information.
    ---
    tags:
      - Tenant
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Tenant information retrieved successfully.
        schema:
          type: object
          properties:
            tenant_id:
              type: string
              description: Tenant ID.
            name:
              type: string
              description: Tenant name.
            llm_id:
              type: string
              description: LLM ID.
            embd_id:
              type: string
              description: Embedding model ID.
    """
    try:
        tenants = TenantService.get_info_by(current_user.id)
        if not tenants:
            return get_data_error_result(message="Tenant not found!")
        return get_json_result(data=tenants[0])
    except Exception as e:
        return server_error_response(e)


@manager.route("/set_tenant_info", methods=["POST"])  # noqa: F821
@login_required
@validate_request("tenant_id", "asr_id", "embd_id", "img2txt_id", "llm_id")
async def set_tenant_info():
    """
    Update tenant information.
    ---
    tags:
      - Tenant
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: Tenant information to update.
        required: true
        schema:
          type: object
          properties:
            tenant_id:
              type: string
              description: Tenant ID.
            llm_id:
              type: string
              description: LLM ID.
            embd_id:
              type: string
              description: Embedding model ID.
            asr_id:
              type: string
              description: ASR model ID.
            img2txt_id:
              type: string
              description: Image to Text model ID.
    responses:
      200:
        description: Tenant information updated successfully.
        schema:
          type: object
    """
    req = await get_request_json()
    try:
        tid = req.pop("tenant_id")
        TenantService.update_by_id(tid, req)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/forget/captcha", methods=["GET"])  # noqa: F821
async def forget_get_captcha():
    """
    GET /forget/captcha?email=<email>
    - Generate an image captcha and cache it in Redis under key captcha:{email} with TTL = OTP_TTL_SECONDS.
    - Returns the captcha as a PNG image.
    """
    email = (request.args.get("email") or "")
    if not email:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email is required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")

    # Generate captcha text
    allowed = string.ascii_uppercase + string.digits
    captcha_text = "".join(secrets.choice(allowed) for _ in range(OTP_LENGTH))
    REDIS_CONN.set(captcha_key(email), captcha_text, 60) # Valid for 60 seconds

    from captcha.image import ImageCaptcha
    image = ImageCaptcha(width=300, height=120, font_sizes=[50, 60, 70])
    img_bytes = image.generate(captcha_text).read()
    response = await make_response(img_bytes)
    response.headers.set("Content-Type", "image/JPEG")
    return response


@manager.route("/forget/otp", methods=["POST"])  # noqa: F821
async def forget_send_otp():
    """
    POST /forget/otp
    - Verify the image captcha stored at captcha:{email} (case-insensitive).
    - On success, generate an email OTP (A–Z with length = OTP_LENGTH), store hash + salt (and timestamp) in Redis with TTL, reset attempts and cooldown, and send the OTP via email.
    """
    req = await get_request_json()
    email = req.get("email") or ""
    captcha = (req.get("captcha") or "").strip()

    if not email or not captcha:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email and captcha required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")

    stored_captcha = REDIS_CONN.get(captcha_key(email))
    if not stored_captcha:
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="invalid or expired captcha")
    if (stored_captcha or "").strip().lower() != captcha.lower():
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="invalid or expired captcha")

    # Delete captcha to prevent reuse
    REDIS_CONN.delete(captcha_key(email))

    k_code, k_attempts, k_last, k_lock = otp_keys(email)
    now = int(time.time())
    last_ts = REDIS_CONN.get(k_last)
    if last_ts:
        try:
            elapsed = now - int(last_ts)
        except Exception:
            elapsed = RESEND_COOLDOWN_SECONDS
        remaining = RESEND_COOLDOWN_SECONDS - elapsed
        if remaining > 0:
            return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message=f"you still have to wait {remaining} seconds")

    # Generate OTP (uppercase letters only) and store hashed
    otp = "".join(secrets.choice(string.ascii_uppercase) for _ in range(OTP_LENGTH))
    salt = os.urandom(16)
    code_hash = hash_code(otp, salt)
    REDIS_CONN.set(k_code, f"{code_hash}:{salt.hex()}", OTP_TTL_SECONDS)
    REDIS_CONN.set(k_attempts, 0, OTP_TTL_SECONDS)
    REDIS_CONN.set(k_last, now, OTP_TTL_SECONDS)
    REDIS_CONN.delete(k_lock)

    ttl_min = OTP_TTL_SECONDS // 60

    try:
        await send_email_html(
            subject="Your Password Reset Code",
            to_email=email,
            template_key="reset_code",
            code=otp,
            ttl_min=ttl_min,
        )

    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, code=RetCode.SERVER_ERROR, message="failed to send email")

    return get_json_result(data=True, code=RetCode.SUCCESS, message="verification passed, email sent")


def _verified_key(email: str) -> str:
    return f"otp:verified:{email}"


@manager.route("/forget/verify-otp", methods=["POST"])  # noqa: F821
async def forget_verify_otp():
    """
    Verify email + OTP only. On success:
    - consume the OTP and attempt counters
    - set a short-lived verified flag in Redis for the email
    Request JSON: { email, otp }
    """
    req = await get_request_json()
    email = req.get("email") or ""
    otp = (req.get("otp") or "").strip()

    if not all([email, otp]):
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email and otp are required")

    users = UserService.query(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")

    # Verify OTP from Redis
    k_code, k_attempts, k_last, k_lock = otp_keys(email)
    if REDIS_CONN.get(k_lock):
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="too many attempts, try later")

    stored = REDIS_CONN.get(k_code)
    if not stored:
        return get_json_result(data=False, code=RetCode.NOT_EFFECTIVE, message="expired otp")

    try:
        stored_hash, salt_hex = str(stored).split(":", 1)
        salt = bytes.fromhex(salt_hex)
    except Exception:
        return get_json_result(data=False, code=RetCode.EXCEPTION_ERROR, message="otp storage corrupted")

    calc = hash_code(otp.upper(), salt)
    if calc != stored_hash:
        # bump attempts
        try:
            attempts = int(REDIS_CONN.get(k_attempts) or 0) + 1
        except Exception:
            attempts = 1
        REDIS_CONN.set(k_attempts, attempts, OTP_TTL_SECONDS)
        if attempts >= ATTEMPT_LIMIT:
            REDIS_CONN.set(k_lock, int(time.time()), ATTEMPT_LOCK_SECONDS)
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="expired otp")

    # Success: consume OTP and attempts; mark verified
    REDIS_CONN.delete(k_code)
    REDIS_CONN.delete(k_attempts)
    REDIS_CONN.delete(k_last)
    REDIS_CONN.delete(k_lock)

    # set verified flag with limited TTL, reuse OTP_TTL_SECONDS or smaller window
    try:
        REDIS_CONN.set(_verified_key(email), "1", OTP_TTL_SECONDS)
    except Exception:
        return get_json_result(data=False, code=RetCode.SERVER_ERROR, message="failed to set verification state")

    return get_json_result(data=True, code=RetCode.SUCCESS, message="otp verified")


@manager.route("/forget/reset-password", methods=["POST"])  # noqa: F821
async def forget_reset_password():
    """
    Reset password after successful OTP verification.
    Requires: { email, new_password, confirm_new_password }
    Steps:
    - check verified flag in Redis
    - update user password
    - auto login
    - clear verified flag
    """
    
    req = await get_request_json()
    email = req.get("email") or ""
    new_pwd = req.get("new_password")
    new_pwd2 = req.get("confirm_new_password")

    new_pwd_base64 = decrypt(new_pwd)
    new_pwd_string = base64.b64decode(new_pwd_base64).decode('utf-8')
    new_pwd2_string = base64.b64decode(decrypt(new_pwd2)).decode('utf-8')

    REDIS_CONN.get(_verified_key(email))
    if not REDIS_CONN.get(_verified_key(email)):
        return get_json_result(data=False, code=RetCode.AUTHENTICATION_ERROR, message="email not verified")

    if not all([email, new_pwd, new_pwd2]):
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="email and passwords are required")

    if new_pwd_string != new_pwd2_string:
        return get_json_result(data=False, code=RetCode.ARGUMENT_ERROR, message="passwords do not match")

    users = UserService.query_user_by_email(email=email)
    if not users:
        return get_json_result(data=False, code=RetCode.DATA_ERROR, message="invalid email")
    
    user = users[0]
    try:
        UserService.update_user_password(user.id, new_pwd_base64)
    except Exception as e:
        logging.exception(e)
        return get_json_result(data=False, code=RetCode.EXCEPTION_ERROR, message="failed to reset password")

    # clear verified flag
    try:
        REDIS_CONN.delete(_verified_key(email))
    except Exception:
        pass

    msg = "Password reset successful. Logged in."
    return await construct_response(data=user.to_json(), auth=user.get_id(), message=msg)



# # 确保导入了正确的库
# from Crypto.PublicKey import RSA
# from Crypto.Cipher import PKCS1_v1_5
# import base64

# def rsa_psw(password: str) -> str:
#     # 1. 严格格式的公钥 (注意每一行末尾不能有空格)
#     # 我把公钥放在这里，请直接复制
#     pub_key_pem = (
#         "-----BEGIN PUBLIC KEY-----\n"
#         "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/\n"
#         "z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp\n"
#         "2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOU\n"
#         "EfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKR\n"
#         "NLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6\n"
#         "olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2\n"
#         "wIDAQAB\n"
#         "-----END PUBLIC KEY-----"
#     )

#     try:
#         # 2. 导入公钥
#         rsa_key = RSA.import_key(pub_key_pem)
        
#         # 3. 创建加密对象
#         cipher = PKCS1_v1_5.new(rsa_key)
        
#         # 4. 执行加密
#         password_bytes = password.encode('utf-8')
#         encrypted_bytes = cipher.encrypt(password_bytes)
        
#         # 5. Base64 编码返回
#         return base64.b64encode(encrypted_bytes).decode('utf-8')

#     except Exception as e:
#         print(f"RSA Error: {str(e)}")
#         return ""



from api.db.services.person_service import SyncPersonService
@manager.route("/verify_sso", methods=["post" , "GET"])  # noqa: F821
# @validate_request("idCard")
async def verify_sso_user():
    req = await get_request_json()
    print("🔴 后端收到的原始数据:", req)
    id_card = req.get('token')

    print("id_card")

    # 通过id_card判断数据库中是否存在数据
    user = SyncPersonService.model.select().where(
            SyncPersonService.model.credentialNo == id_card
        ).first()
    
    # 1. 先判断用户是否存在（防止 user 为 None 报错）
    if not user:
        return get_json_result(data=False, message="User not found in database", code=RetCode.DATA_ERROR)

    # 2. 获取手机号
    phone_number = user.phone

    user_ragflow = UserService.query(email=phone_number)
    # 3. 判断是否已注册（查到了无需注册，没查到才注册）
    if user_ragflow:
        # 已注册：直接登录
        # ... (你的登录逻辑) ...
        nickname = user.mdmName
        password = user_ragflow[0].password
        user_dict = {
            "access_token": get_uuid(),
            "email": phone_number,
            "nickname": nickname,
            "password": password,
            "login_channel": "password",
            "last_login_time": get_format_time(),
            "is_superuser": False,
        }
        return get_json_result(data=user_dict)
    else:
        
        password = crypt("123456")
        # Construct user info data
        nickname = user.mdmName
        user_dict = {
            "access_token": get_uuid(),
            "email": phone_number,
            "nickname": nickname,
            "password": password,
            "login_channel": "password",
            "last_login_time": get_format_time(),
            "is_superuser": False,
        }

        print(decrypt(password))

        user_id = get_uuid()

        try:
            print("hello")
            users = user_register(user_id, user_dict)
            if not users:
                raise Exception(f"Fail to register {phone_number}.")
            if len(users) > 1:
                raise Exception(f"Same email: {phone_number} exists!")
            user = users[0]
            login_user(user)
            return await construct_response(
                data=user.to_json(),
                auth=user.get_id(),
                message=f"{nickname}, welcome aboard!",
            )
        except Exception as e:
            rollback_user_registration(user_id)
            logging.exception(e)
            return get_json_result(
                data=False,
                message=f"User registration failure, error: {str(e)}",
                code=RetCode.EXCEPTION_ERROR,
            )

