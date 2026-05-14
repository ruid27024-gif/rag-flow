#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

import logging
import time
import os
import subprocess
import shutil
import tempfile
import pathlib
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
from io import BytesIO
from common.decorator import singleton
from common import settings
import sys

def convert_to_pdf(file_path):
    """
    Converts a doc or docx file to pdf format.

    Args:
        file_path (str): The absolute path to the doc/docx file.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return

    # Determine output directory (same as input file)
    output_dir = os.path.dirname(file_path)

    # Construct the libreoffice command
    # libreoffice --headless --convert-to pdf <file_path> --outdir <output_dir>
    # Add LD_LIBRARY_PATH to environment variables
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/usr/lib/libreoffice/program:' + env.get('LD_LIBRARY_PATH', '')

    command = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        file_path,
        "--outdir",
        output_dir
    ]

    print(f"DEBUG-HY: Starting conversion for: {file_path}")
    print(f"DEBUG-HY:Output directory: {output_dir}")

    try:
        # Run the command
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        print("DEBUG-HY: Conversion completed successfully.")
        print("LibreOffice Output:")
        print(result.stdout.decode())

        # Verify output file exists
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        pdf_path = os.path.join(output_dir, base_name + ".pdf")
        if os.path.exists(pdf_path):
            print(f"DEBUG-HY: PDF generated at: {pdf_path}")
            return pdf_path
        else:
            print("DEBUG-HY: Warning: PDF file not found despite successful command execution.")
            return None

    except subprocess.CalledProcessError as e:
        print("DEBUG-HY: Error during conversion.")
        print("DEBUG-HY: Return code:", e.returncode)
        print("DEBUG-HY: Stderr:", e.stderr.decode())
        return None
    except Exception as e:
        print(f"DEBUG-HY: An unexpected error occurred: {e}")
        return None

# def convert_to_pdf(file_path):
#     """
#     跨平台稳健版：使用临时目录，防止进程卡死，自动适配 Linux/Windows
#     """
#     # 1. 检查源文件是否存在
#     if not os.path.exists(file_path):
#         print(f"Error: File '{file_path}' does not exist.")
#         return None

#     # 2. 自动识别系统并指定 LibreOffice 执行路径
#     system = platform.system()
#     libreoffice_cmd = "libreoffice"  # 默认 Linux 命令
    
#     if system == "Windows":
#         # Windows 下通常的默认安装路径
#         win_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
#         if os.path.exists(win_path):
#             libreoffice_cmd = win_path
#         else:
#             # 如果默认路径没有，尝试依赖系统环境变量
#             print("Warning: Default LibreOffice path not found on Windows, trying system PATH...")
#     elif system == "Linux":
#         # Linux 下设置 LD_LIBRARY_PATH，防止找不到 LibreOffice 依赖库
#         # 同时解决部分 Linux 环境下转换 PDF 中文乱码的问题
#         env = os.environ.copy()
#         env['LD_LIBRARY_PATH'] = '/usr/lib/libreoffice/program:' + env.get('LD_LIBRARY_PATH', '')
#     else:
#         # macOS 等其他系统，默认依赖环境变量中的 libreoffice 命令
#         env = os.environ.copy()

#     # 3. 创建临时目录用于输出 (绝对安全，避免文件名冲突)
#     temp_output_dir = tempfile.mkdtemp()

#     try:
#         # 构建命令参数列表
#         # --headless: 无头模式（后台运行）
#         # --nologo: 不显示启动画面（提升速度，减少资源占用）
#         # --convert-to pdf: 转换格式
#         # --outdir: 输出目录 (指向临时目录)
#         command = [
#             libreoffice_cmd,
#             "--headless",
#             "--nologo",
#             "--convert-to", "pdf",
#             "--outdir", temp_output_dir,
#             file_path
#         ]

#         print(f"Starting conversion for: {os.path.basename(file_path)}...")

#         # 4. 执行转换
#         # 在 Linux 下传入优化后的环境变量，设置 60 秒超时防止卡死
#         run_kwargs = {
#             "stdout": subprocess.PIPE,
#             "stderr": subprocess.PIPE,
#             "timeout": 60,
#         }
        
#         if system == "Linux":
#             run_kwargs["env"] = env
        
#         result = subprocess.run(command, **run_kwargs)

#         # 5. 检查结果
#         if result.returncode == 0:
#             # 在临时目录中寻找生成的 PDF
#             base_name = os.path.splitext(os.path.basename(file_path))[0]
#             generated_pdf_name = base_name + ".pdf"
#             temp_pdf_path = os.path.join(temp_output_dir, generated_pdf_name)

#             if os.path.exists(temp_pdf_path):
#                 # 目标路径 (与原文件同目录)
#                 final_pdf_path = os.path.join(os.path.dirname(file_path), generated_pdf_name)

#                 # 移动文件 (如果目标已存在则覆盖)
#                 shutil.move(temp_pdf_path, final_pdf_path)
#                 print(f"SUCCESS: PDF saved to: {final_pdf_path}")
#                 return final_pdf_path
#             else:
#                 print("ERROR: Conversion finished but PDF file not found in temp dir.")
#                 print(f"DEBUG: Temp dir contents: {os.listdir(temp_output_dir)}")
#                 return None
#         else:
#             print(f"ERROR: LibreOffice exited with code {result.returncode}")
#             # 尝试解码错误日志
#             try:
#                 err_msg = result.stderr.decode('utf-8', errors='ignore')
#             except:
#                 err_msg = result.stderr.decode('gbk', errors='ignore')
#             print(f"DEBUG: Error details: {err_msg}")
#             return None

#     except subprocess.TimeoutExpired:
#         print("ERROR: Conversion timed out (60s). Force killing process.")
#         return None
#     except FileNotFoundError:
#         print(f"CRITICAL ERROR: LibreOffice command '{libreoffice_cmd}' not found. Please install LibreOffice.")
#         return None
#     except Exception as e:
#         print(f"ERROR: Unexpected exception: {e}")
#         return None
#     finally:
#         # 6. 无论如何都要清理临时目录，防止垃圾文件堆积
#         if os.path.exists(temp_output_dir):
#             try:
#                 shutil.rmtree(temp_output_dir)
#             except Exception as e:
#                 print(f"Warning: Failed to clean up temp directory {temp_output_dir}: {e}")

# import os
# import subprocess
#
# import os
# import subprocess
# import tempfile
# import shutil
#
#
# def convert_to_pdf(file_path):
#     """
#     稳健版：使用临时目录，修复路径问题，防止进程卡死
#     """
#     # 1. 检查源文件
#     if not os.path.exists(file_path):
#         print(f"Error: File '{file_path}' does not exist.")
#         return None
#
#     # 2. 指定 LibreOffice 路径 (建议检查环境变量，或者直接写死)
#     # 注意：这里保留反斜杠，因为这是 Windows 本地路径
#     libreoffice_exe = r"C:\Program Files\LibreOffice\program\soffice.exe"
#
#     if not os.path.exists(libreoffice_exe):
#         print(f"CRITICAL ERROR: LibreOffice not found at: {libreoffice_exe}")
#         print("HINT: Please install LibreOffice or update the path.")
#         return None
#
#     # 3. 创建临时目录用于输出 (避免与原文件冲突)
#     # 使用 mkdtemp 创建一个唯一的临时文件夹
#     temp_output_dir = tempfile.mkdtemp()
#
#     try:
#         # 构建命令参数列表 (推荐方式，比 shell=True 更安全，避免转义问题)
#         # --headless: 无头模式
#         # --convert-to pdf: 转换格式
#         # --outdir: 输出目录 (指向临时目录)
#         cmd = [
#             libreoffice_exe,
#             "--headless",
#             "--convert-to", "pdf",
#             "--outdir", temp_output_dir,
#             file_path  # 输入文件路径 (LibreOffice 能够处理 Windows 路径)
#         ]
#
#         print(f"DEBUG: Starting conversion for: {os.path.basename(file_path)}")
#
#         # 4. 执行转换
#         # startupinfo 用于在 Windows 下不显示黑色命令行窗口
#         startupinfo = None
#         if os.name == 'nt':
#             startupinfo = subprocess.STARTUPINFO()
#             startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
#
#         result = subprocess.run(
#             cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             timeout=60,  # 60秒超时
#             startupinfo=startupinfo
#         )
#
#         # 5. 检查结果
#         if result.returncode == 0:
#             # 在临时目录中寻找生成的 PDF
#             # 文件名应该与源文件相同，只是后缀变了
#             base_name = os.path.basename(file_path)
#             # 移除后缀并加上 .pdf
#             name_without_ext = os.path.splitext(base_name)[0]
#             generated_pdf_name = name_without_ext + ".pdf"
#             temp_pdf_path = os.path.join(temp_output_dir, generated_pdf_name)
#
#             if os.path.exists(temp_pdf_path):
#                 # 目标路径 (与原文件同目录)
#                 final_pdf_path = os.path.join(os.path.dirname(file_path), generated_pdf_name)
#
#                 # 移动文件 (如果目标已存在则覆盖)
#                 shutil.move(temp_pdf_path, final_pdf_path)
#                 print(f"SUCCESS: PDF saved to: {final_pdf_path}")
#                 return final_pdf_path
#             else:
#                 print("ERROR: Conversion finished but PDF file not found in temp dir.")
#                 # 调试：列出临时目录内容
#                 print(f"DEBUG: Temp dir contents: {os.listdir(temp_output_dir)}")
#                 return None
#         else:
#             print(f"ERROR: LibreOffice exited with code {result.returncode}")
#             # 尝试解码错误日志 (LibreOffice 有时输出 GBK 编码)
#             try:
#                 err_msg = result.stderr.decode('gbk', errors='ignore')
#             except:
#                 err_msg = result.stderr.decode('utf-8', errors='ignore')
#             print(f"DEBUG: Error details: {err_msg}")
#             return None
#
#     except subprocess.TimeoutExpired:
#         print("ERROR: Conversion timed out. Force killing process.")
#         return None
#     except Exception as e:
#         print(f"ERROR: Unexpected exception: {e}")
#         return None
#     finally:
#         # 6. 清理临时目录
#         if os.path.exists(temp_output_dir):
#             try:
#                 shutil.rmtree(temp_output_dir)
#             except:
#                 pass  # 忽略清理失败，让系统稍后清理


# 测试调用
# convert_to_pdf_robust(r"D:\test\example.docx")



@singleton
class RAGFlowMinio:
    def __init__(self):
        self.conn = None
        # Use `or None` to convert empty strings to None, ensuring single-bucket
        # mode is truly disabled when not configured
        self.bucket = settings.MINIO.get('bucket', None) or None
        self.prefix_path = settings.MINIO.get('prefix_path', None) or None
        self.__open__()

    @staticmethod
    def use_default_bucket(method):
        def wrapper(self, bucket, *args, **kwargs):
            # If there is a default bucket, use the default bucket
            # but preserve the original bucket identifier so it can be
            # used as a path prefix inside the physical/default bucket.
            original_bucket = bucket
            actual_bucket = self.bucket if self.bucket else bucket
            if self.bucket:
                # pass original identifier forward for use by other decorators
                kwargs['_orig_bucket'] = original_bucket
            return method(self, actual_bucket, *args, **kwargs)
        return wrapper

    @staticmethod
    def use_prefix_path(method):
        def wrapper(self, bucket, fnm, *args, **kwargs):
            # If a default MINIO bucket is configured, the use_default_bucket
            # decorator will have replaced the `bucket` arg with the physical
            # bucket name and forwarded the original identifier as `_orig_bucket`.
            # Prefer that original identifier when constructing the key path so
            # objects are stored under <physical-bucket>/<identifier>/...
            orig_bucket = kwargs.pop('_orig_bucket', None)

            if self.prefix_path:
                # If a prefix_path is configured, include it and then the identifier
                if orig_bucket:
                    fnm = f"{self.prefix_path}/{orig_bucket}/{fnm}"
                else:
                    fnm = f"{self.prefix_path}/{fnm}"
            else:
                # No prefix_path configured. If orig_bucket exists and the
                # physical bucket equals configured default, use orig_bucket as a path.
                if orig_bucket and bucket == self.bucket:
                    fnm = f"{orig_bucket}/{fnm}"

            return method(self, bucket, fnm, *args, **kwargs)
        return wrapper

    def __open__(self):
        try:
            if self.conn:
                self.__close__()
        except Exception:
            pass

        try:
            self.conn = Minio(settings.MINIO["host"],
                              access_key=settings.MINIO["user"],
                              secret_key=settings.MINIO["password"],
                              secure=False
                              )
        except Exception:
            logging.exception(
                "Fail to connect %s " % settings.MINIO["host"])

    def __close__(self):
        del self.conn
        self.conn = None

    def health(self):
        bucket = self.bucket if self.bucket else "ragflow-bucket"
        fnm = "_health_check"
        if self.prefix_path:
            fnm = f"{self.prefix_path}/{fnm}"
        binary = b"_t@@@1"
        # Don't try to create bucket - it should already exist
        # if not self.conn.bucket_exists(bucket):
        #     self.conn.make_bucket(bucket)
        r = self.conn.put_object(bucket, fnm,
                                 BytesIO(binary),
                                 len(binary)
                                 )
        return r

    @use_default_bucket
    @use_prefix_path
    def put(self, bucket, fnm, binary, tenant_id=None):
        for _ in range(3):
            try:
                # Note: bucket must already exist - we don't have permission to create buckets
                if not self.bucket and not self.conn.bucket_exists(bucket):
                    self.conn.make_bucket(bucket)

                r = self.conn.put_object(bucket, fnm,
                                         BytesIO(binary),
                                         len(binary)
                                         )
                return r
            except Exception:
                logging.exception(f"Fail to put {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)

    @use_default_bucket
    @use_prefix_path
    def rm(self, bucket, fnm, tenant_id=None):
        try:
            self.conn.remove_object(bucket, fnm)
        except Exception:
            logging.exception(f"Fail to remove {bucket}/{fnm}:")

    @use_default_bucket
    @use_prefix_path
    def get(self, bucket, filename, tenant_id=None):
        for _ in range(1):
            try:
                base, ext = os.path.splitext(filename)
                ext = ext.lower()
                pdf_cache_name = base + ".pdf"




                if ext == ".pdf":
                    # PDF：先查缓存（同名 .pdf），命中直接返回；否则读原对象并写入缓存
                    r = self.conn.get_object(bucket, filename)
                    print(f"【DEBUG-HY】: get {bucket}/{filename}, type is {type(r)}", file=sys.stderr, flush=True)
                    content = r.read()
                    # 判断文件是否是扫描文件
                    # is_scan = is_scanned_pdf_from_stream(content)
                    # is_scan = False
                    # if is_scan:
                    #     # 是扫描件，需要进行扫面件流程
                    #     print(f"【DEBUG-HY】: {base} is scanned pdf, need to parse it", file=sys.stderr, flush=True)
                    #     # 解析扫描件
                    #     print(f"【DEBUG-HY】: {base} start to parse it", file=sys.stderr, flush=True)
                    #     content = parse_pdf_stream(content,"temp_pdf",base)
                    try:
                        r.close()
                    except Exception:
                        pass
                    try:
                        if hasattr(r, "release_conn"):
                            r.release_conn()
                    except Exception:
                        pass
                    try:
                        if is_scan:
                            self.conn.put_object(bucket, pdf_cache_name, BytesIO(content), len(content))
                    except Exception:
                        pass
                    return content




                elif ext in [".doc", ".docx"]:
                    # DOC/DOCX：优先查同名 .pdf 缓存；未命中则读取原对象并转换为 PDF，写回缓存并返回 PDF 二进制
                    try:
                        cr = self.conn.get_object(bucket, pdf_cache_name)
                        content = cr.read()
                        try:
                            cr.close()
                        except Exception:
                            pass
                        try:
                            if hasattr(cr, "release_conn"):
                                cr.release_conn()
                        except Exception:
                            pass
                        return content
                    except Exception:
                        pass

                    # 1. 获取当前文件所在的文件夹路径 (绝对路径)
                    # 结果类似: C:\Users\...\rag-flow\rag\utils
                    current_dir = os.path.dirname(os.path.abspath(__file__))

                    # 2. 手动拼接相对路径逻辑
                    # 这里的 ".." 是字符串拼接，不是依赖系统环境，所以是安全的
                    # 意思就是：当前目录 -> 上一级 -> 再上一级 -> temp_pdf
                    save_dir = os.path.join(current_dir, "..", "..", "temp_pdf")

                    # 3. 创建目录
                    os.makedirs(save_dir, exist_ok=True)

                    print(f"最终绝对路径是: {os.path.abspath(save_dir)}")

                    r = self.conn.get_object(bucket, filename)
                    print(f"【DEBUG-HY】: get {bucket}/{filename}, type is {type(r)}", file=sys.stderr, flush=True)
                    orig_bytes = r.read()

                    save_path = os.path.join(save_dir, filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(orig_bytes)
                    pdf_bytes = None
                    try:
                        pdf_path = convert_to_pdf(save_path)
                        if pdf_path and os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as pf:
                                pdf_bytes = pf.read()
                        else:
                            print(f"【DEBUG-HY】DOC/DOCX→PDF fallback to original for {save_path}", file=sys.stderr, flush=True)
                    except Exception:
                        print(f"【DEBUG-HY】Fail to convert {save_path} to PDF", file=sys.stderr, flush=True)
                    try:
                        r.close()
                    except Exception:
                        pass
                    try:
                        if hasattr(r, "release_conn"):
                            r.release_conn()
                    except Exception:
                        pass
                    if pdf_bytes:
                        try:
                            self.conn.put_object(bucket, pdf_cache_name, BytesIO(pdf_bytes), len(pdf_bytes))
                        except Exception:
                            pass
                        return pdf_bytes
                    return orig_bytes

                else:
                    # 其他类型：保持原有读取逻辑
                    r = self.conn.get_object(bucket, filename)
                    print(f"【DEBUG-HY】: get {bucket}/{filename}, type is {type(r)}", file=sys.stderr, flush=True)
                    content = r.read()
                    try:
                        r.close()
                    except Exception:
                        pass
                    try:
                        if hasattr(r, "release_conn"):
                            r.release_conn()
                    except Exception:
                        pass
                    return content
            except Exception:
                print(f"【DEBUG-HY】Fail to get {bucket}/{filename}", file=sys.stderr, flush=True)
                self.__open__()
                time.sleep(1)
        return

    @use_default_bucket
    @use_prefix_path
    def obj_exist(self, bucket, filename, tenant_id=None):
        try:
            if not self.conn.bucket_exists(bucket):
                return False
            if self.conn.stat_object(bucket, filename):
                return True
            else:
                return False
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket", "ResourceNotFound"]:
                return False
        except Exception:
            logging.exception(f"obj_exist {bucket}/{filename} got exception")
            return False

    @use_default_bucket
    def bucket_exists(self, bucket):
        try:
            if not self.conn.bucket_exists(bucket):
                return False
            else:
                return True
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket", "ResourceNotFound"]:
                return False
        except Exception:
            logging.exception(f"bucket_exist {bucket} got exception")
            return False

    @use_default_bucket
    @use_prefix_path
    def get_presigned_url(self, bucket, fnm, expires, tenant_id=None):
        for _ in range(10):
            try:
                return self.conn.get_presigned_url("GET", bucket, fnm, expires)
            except Exception:
                logging.exception(f"Fail to get_presigned {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)
        return

    @use_default_bucket
    def remove_bucket(self, bucket, **kwargs):
        orig_bucket = kwargs.pop('_orig_bucket', None)
        try:
            if self.bucket:
                # Single bucket mode: remove objects with prefix
                prefix = ""
                if self.prefix_path:
                    prefix = f"{self.prefix_path}/"
                if orig_bucket:
                    prefix += f"{orig_bucket}/"

                # List objects with prefix
                objects_to_delete = self.conn.list_objects(bucket, prefix=prefix, recursive=True)
                for obj in objects_to_delete:
                    self.conn.remove_object(bucket, obj.object_name)
                # Do NOT remove the physical bucket
            else:
                if self.conn.bucket_exists(bucket):
                    objects_to_delete = self.conn.list_objects(bucket, recursive=True)
                    for obj in objects_to_delete:
                        self.conn.remove_object(bucket, obj.object_name)
                    self.conn.remove_bucket(bucket)
        except Exception:
            logging.exception(f"Fail to remove bucket {bucket}")

    def _resolve_bucket_and_path(self, bucket, fnm):
        if self.bucket:
            if self.prefix_path:
                fnm = f"{self.prefix_path}/{bucket}/{fnm}"
            else:
                fnm = f"{bucket}/{fnm}"
            bucket = self.bucket
        elif self.prefix_path:
            fnm = f"{self.prefix_path}/{fnm}"
        return bucket, fnm

    def copy(self, src_bucket, src_path, dest_bucket, dest_path):
        try:
            src_bucket, src_path = self._resolve_bucket_and_path(src_bucket, src_path)
            dest_bucket, dest_path = self._resolve_bucket_and_path(dest_bucket, dest_path)

            if not self.conn.bucket_exists(dest_bucket):
                self.conn.make_bucket(dest_bucket)

            try:
                self.conn.stat_object(src_bucket, src_path)
            except Exception as e:
                logging.exception(f"Source object not found: {src_bucket}/{src_path}, {e}")
                return False

            self.conn.copy_object(
                dest_bucket,
                dest_path,
                CopySource(src_bucket, src_path),
            )
            return True

        except Exception:
            logging.exception(f"Fail to copy {src_bucket}/{src_path} -> {dest_bucket}/{dest_path}")
            return False

    def move(self, src_bucket, src_path, dest_bucket, dest_path):
        try:
            if self.copy(src_bucket, src_path, dest_bucket, dest_path):
                self.rm(src_bucket, src_path)
                return True
            else:
                logging.error(f"Copy failed, move aborted: {src_bucket}/{src_path}")
                return False
        except Exception:
            logging.exception(f"Fail to move {src_bucket}/{src_path} -> {dest_bucket}/{dest_path}")
            return False
