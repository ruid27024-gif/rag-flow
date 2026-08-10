"""
用户上传文件
  ↓
保存到本地 runtime/staging_upload
  ↓
写入 StagedFile 表
  ↓
生成一个临时下载 URL
  ↓
把 URL + 标签 + 审批人列表发送给 OA
  ↓
OA 通过 URL 下载/预览文件

"""

# 通过ragflow后端接口把本地路径转为可请求的url

# 1. 生成下载 URL 的方法
import os
from urllib.parse import quote
from itsdangerous import URLSafeTimedSerializer


STAGED_FILE_DOWNLOAD_SALT = "staged-file-download"


def get_staged_file_serializer():
    secret = os.environ.get("STAGED_FILE_URL_SECRET")
    if not secret:
        raise RuntimeError("Missing STAGED_FILE_URL_SECRET")
    return URLSafeTimedSerializer(secret)


def make_staged_file_download_url(stage_id: str) -> str:
    public_base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

    if not public_base_url:
        raise RuntimeError("Missing PUBLIC_BASE_URL")

    serializer = get_staged_file_serializer()

    token = serializer.dumps(
        {
            "stage_id": stage_id,
        },
        salt=STAGED_FILE_DOWNLOAD_SALT,
    )

    return (
        f"{public_base_url}"
        f"/api/document/staged-file/{stage_id}/download"
        f"?token={quote(token)}"
    )

# 2. 下载接口(通过url来获取到本地文件)
import os
from pathlib import Path
from itsdangerous import BadSignature, SignatureExpired

# 如果你的项目用 Flask
# from flask import send_file

# 如果你的项目用 Quart，可能需要：
from quart import send_file


@manager.route("/staged-file/<stage_id>/download", methods=["GET"])  # noqa: F821
async def download_staged_file(stage_id):
    token = request.args.get("token")

    if not token:
        return get_json_result(
            data=False,
            message="Missing token.",
            code=RetCode.ARGUMENT_ERROR,
        )

    serializer = get_staged_file_serializer()

    try:
        data = serializer.loads(
            token,
            salt=STAGED_FILE_DOWNLOAD_SALT,
            max_age=7 * 24 * 3600,  # URL 有效期 7 天，可按需要调整
        )
    except SignatureExpired:
        return get_json_result(
            data=False,
            message="Download URL has expired.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    except BadSignature:
        return get_json_result(
            data=False,
            message="Invalid token.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    if data.get("stage_id") != stage_id:
        return get_json_result(
            data=False,
            message="Invalid download URL.",
            code=RetCode.AUTHENTICATION_ERROR,
        )

    staged_file = StagedFile.get_or_none(StagedFile.id == stage_id)

    if not staged_file:
        return get_json_result(
            data=False,
            message="Staged file not found.",
            code=RetCode.NOT_FOUND,
        )

    file_path = staged_file.path

    if not file_path or not os.path.exists(file_path):
        return get_json_result(
            data=False,
            message="File does not exist.",
            code=RetCode.NOT_FOUND,
        )

    filename = staged_file.filename or Path(file_path).name

    # Flask 写法
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
    )

    # 如果你项目是 Quart，可能需要：
    # return await send_file(
    #     file_path,
    #     as_attachment=True,
    #     attachment_filename=filename,
    # )

