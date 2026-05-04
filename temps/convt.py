import os
import subprocess


def convert_to_pdf_windows_fixed(file_path):
    """
    修正版：适配 Windows 和带有空格的 LibreOffice 路径
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return

    # 1. 指定你的 LibreOffice 路径 (使用 r"" 原始字符串防止转义问题)
    libreoffice_exe = r"C:\Program Files\LibreOffice\program\soffice.exe"

    # 双重检查：确保这个 exe 真的存在
    if not os.path.exists(libreoffice_exe):
        print(f"CRITICAL ERROR: LibreOffice executable not found at: {libreoffice_exe}")
        print("Please verify the path is correct.")
        return

    # 2. 确定输出目录
    output_dir = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    pdf_path = os.path.join(output_dir, base_name + ".pdf")

    # 3. 构建命令字符串 (注意引号的使用)
    # 格式："C:\Path\To\soffice.exe" --headless --convert-to pdf "输入文件" --outdir "输出目录"
    # 给所有包含路径的参数加上双引号是 Windows 批处理的最佳实践
    command = f'"{libreoffice_exe}" --headless --convert-to pdf --outdir "{output_dir}" "{file_path}"'

    print(f"DEBUG-HY: Starting conversion...")
    print(f"DEBUG-HY: Command: {command}")

    try:
        # 4. 执行命令
        # shell=True 是关键，它告诉 Windows 通过 cmd.exe 来运行这个字符串
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        print("DEBUG-HY: Command executed successfully.")

        # 5. 验证结果
        if os.path.exists(pdf_path):
            print(f"DEBUG-HY: PDF generated at: {pdf_path}")
            return pdf_path
        else:
            print("DEBUG-HY: Warning: Command finished but PDF file is missing.")
            # 尝试打印错误流，使用 gbk 解码以适配中文 Windows
            err_msg = result.stderr.decode('gbk', errors='ignore')
            if err_msg:
                print(f"DEBUG-HY: System Error Output: {err_msg}")
            return None

    except subprocess.CalledProcessError as e:
        print("DEBUG-HY: Execution failed with return code:", e.returncode)
        print("DEBUG-HY: Error details:", e.stderr.decode('gbk', errors='ignore'))
        return None
    except Exception as e:
        print(f"DEBUG-HY: Unexpected error: {e}")
        return None




# --- 测试调用 ---
# 模拟你日志中的文件路径
target_file = r"C:\Users\28023\Desktop\rag-flow\temps\11.doc"
convert_to_pdf_windows_fixed(target_file)