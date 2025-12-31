import fitz  # PyMuPDF
import io
import copy
import json
import os
from pathlib import Path
import tempfile
import sys
from loguru import logger

from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox
from mineru.utils.enum_class import MakeMode
from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.backend.vlm.vlm_analyze import ModelSingleton as VLMModelSingleton
from mineru.backend.pipeline.pipeline_analyze import ModelSingleton as PipelineModelSingleton
from mineru.utils.model_utils import clean_memory
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path, guess_suffix_by_bytes
from mineru.utils.pdf_image_tools import images_bytes_to_pdf_bytes
import os
import re
import tempfile
import urllib.request
import html
import mimetypes
import logging
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rcParams

logging.getLogger('matplotlib').setLevel(logging.WARNING)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, ListFlowable, ListItem, Preformatted
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader


def _choose_font():
    candidates = [
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttf", "WQYMicroHei"),
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "WQYMicroHei"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans"),
        ("/usr/share/fonts/truetype/simsun.ttf", "SimSun"),
    ]
    env_font = os.getenv("RAGFLOW_PDF_FONT")
    if env_font and os.path.exists(env_font):
        pdfmetrics.registerFont(TTFont("CustomFont", env_font))
        return "CustomFont"
    for path, name in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            return name
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        return "Helvetica"


def _scale_image_component(img: Image, max_width: float):
    # If drawWidth/drawHeight are already set (e.g. for LaTeX), use them as base
    # Otherwise use intrinsic image size
    current_w = getattr(img, 'drawWidth', img.imageWidth)
    current_h = getattr(img, 'drawHeight', img.imageHeight)
    
    if current_w > max_width:
        ratio = max_width / float(current_w)
        img.drawWidth = max_width
        img.drawHeight = current_h * ratio
    else:
        img.drawWidth = current_w
        img.drawHeight = current_h
    return img


def _download_remote_image(url: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        ctype = resp.headers.get_content_type()
        if not (ctype.startswith("image/") and ctype != "image/svg+xml"):
            return None
        suffix = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "image/gif": ".gif"
        }.get(ctype, ".img")
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(tmp_path, "wb") as wf:
            wf.write(resp.read())
        return tmp_path
    except Exception:
        return None


_FONT_CONFIGURED = False

def _configure_matplotlib_font():
    global _FONT_CONFIGURED
    if _FONT_CONFIGURED:
        return
    try:
        font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            prop = fm.FontProperties(fname=font_path)
            font_name = prop.get_name()
            rcParams['font.family'] = font_name
            rcParams['mathtext.fontset'] = 'custom'
            rcParams['mathtext.rm'] = font_name
            rcParams['mathtext.it'] = font_name
            rcParams['mathtext.bf'] = font_name
            rcParams['axes.unicode_minus'] = False
        _FONT_CONFIGURED = True
    except Exception:
        pass


def _sanitize_latex(latex_str: str) -> str:
    # Unescape HTML entities (e.g., &amp; -> &)
    latex_str = html.unescape(latex_str)

    # Convert common LaTeX symbols to Unicode characters to improve compatibility with Matplotlib mathtext
    # especially when using CJK fonts or when specific symbols are missing.
    replacements = {
        r"\sim": "\u223C",     # ∼ (Tilde Operator)
        r"\approx": "\u2248",  # ≈
        r"\le": "\u2264",      # ≤
        r"\leq": "\u2264",     # ≤
        r"\ge": "\u2265",      # ≥
        r"\geq": "\u2265",     # ≥
        r"\times": "\u00D7",   # ×
        r"\div": "\u00F7",     # ÷
        r"\pm": "\u00B1",      # ±
        r"\cdot": "\u00B7",    # ·
        r"\neq": "\u2260",     # ≠
        r"\ne": "\u2260",      # ≠
        r"\infty": "\u221E",   # ∞
        r"\deg": "\u00B0",     # °
        r"\circ": "\u00B0",    # ° (Often used as degree)
        r"\dots": "...",
        r"\cdots": "...",
        r"\prime": "'",
        r"\forall": "\u2200",  # ∀
        r"\exists": "\u2203",  # ∃
        r"\in": "\u2208",      # ∈
        r"\notin": "\u2209",   # ∉
        r"\subset": "\u2282",  # ⊂
        r"\subseteq": "\u2286",# ⊆
        r"\cup": "\u222A",     # ∪
        r"\cap": "\u2229",     # ∩
        r"\rightarrow": "\u2192", # →
        r"\to": "\u2192",      # →
        r"\leftarrow": "\u2190",  # ←
        r"\Rightarrow": "\u21D2", # ⇒
        r"\Leftarrow": "\u21D0",  # ⇐
    }
    for cmd, char in replacements.items():
        # Use word boundary for commands to avoid partial replacement (e.g. \times vs \timestamp if existed)
        # But \sim might be followed by non-word char like space or number.
        # \b matches boundary between \w and \W.
        # For LaTeX commands, they usually end with space or non-letter.
        # Regex to match command followed by optional space or non-letter.
        # Simple replace is risky if one command is prefix of another.
        # But here we have standard commands.
        latex_str = re.sub(re.escape(cmd) + r"(?![a-zA-Z])", char, latex_str)

    # Remove unsupported commands
    latex_str = latex_str.replace(r"\scriptstyle", "")
    latex_str = latex_str.replace(r"\smash", "")
    latex_str = latex_str.replace(r"\displaystyle", "")
    latex_str = latex_str.replace(r"\bigl", "")
    latex_str = latex_str.replace(r"\bigr", "")
    latex_str = latex_str.replace(r"\phantom", "")
    latex_str = latex_str.replace(r"\atop", "")
    # Handle \tag{...} -> \qquad (content)
    latex_str = re.sub(r"\\tag\s*\{([^}]+)\}", r"\\qquad (\1)", latex_str)
    latex_str = re.sub(r"\\tag\b", "", latex_str)
    
    # Handle array environment (Matplotlib doesn't support array)
    # Be more aggressive: remove \begin{array}{...} and \end{array}, replace \\ with space
    latex_str = re.sub(r"\\begin\{array\}\{[^}]+\}", "", latex_str)
    latex_str = re.sub(r"\\begin\{array\}", "", latex_str) # Catch malformed
    latex_str = latex_str.replace(r"\end{array}", "")
    
    # Handle matrix environments (bmatrix, pmatrix, vmatrix, matrix, etc.)
    # Matplotlib mathtext doesn't support these environments.
    # We replace them with their bracket equivalents and clean up content.
    # bmatrix -> [ ... ]
    latex_str = re.sub(r"\\begin\{bmatrix\}", "[", latex_str)
    latex_str = re.sub(r"\\end\{bmatrix\}", "]", latex_str)
    # pmatrix -> ( ... )
    latex_str = re.sub(r"\\begin\{pmatrix\}", "(", latex_str)
    latex_str = re.sub(r"\\end\{pmatrix\}", ")", latex_str)
    # vmatrix -> | ... |
    latex_str = re.sub(r"\\begin\{vmatrix\}", "|", latex_str)
    latex_str = re.sub(r"\\end\{vmatrix\}", "|", latex_str)
    # Bmatrix -> { ... }
    latex_str = re.sub(r"\\begin\{Bmatrix\}", "{", latex_str)
    latex_str = re.sub(r"\\end\{Bmatrix\}", "}", latex_str)
    # Vmatrix -> || ... ||
    latex_str = re.sub(r"\\begin\{Vmatrix\}", "||", latex_str)
    latex_str = re.sub(r"\\end\{Vmatrix\}", "||", latex_str)
    # matrix -> ...
    latex_str = re.sub(r"\\begin\{matrix\}", "", latex_str)
    latex_str = re.sub(r"\\end\{matrix\}", "", latex_str)

    # Clean up matrix/array content
    # Replace & with comma or space (mathtext doesn't support alignment tabs)
    latex_str = latex_str.replace("&", ", ") 
    # Replace \\ with space or semicolon
    latex_str = latex_str.replace(r"\\", "; ")
    
    # Remove \overbrace{...}^{...} or \overbrace{...}
    # Using a loop to handle nested braces or complex content inside overbrace
    # Simple regex won't work well for nested braces, but we can try to just remove the command
    # and keep the content. Since parsing braces is hard with regex, we'll strip the command name
    # and hope the braces balance out or are ignored if they are just grouping.
    # Actually, \overbrace{content} -> content is what we want.
    # Mathtext might complain about loose braces if we just strip the command, but let's try
    # simply removing the command keyword first.
    latex_str = latex_str.replace(r"\overbrace", "")
    
    # Strip \mathfrak{...}, \mathcal{...}, \mathbb{...} as they might require unsupported fonts
    # Just keep the content.
    # Handle \mathfrak{content} -> content
    latex_str = re.sub(r"\\mathfrak\s*\{([^}]+)\}", r"\1", latex_str)
    latex_str = latex_str.replace(r"\mathfrak", "")
    # Handle \mathcal{content} -> content
    latex_str = re.sub(r"\\mathcal\s*\{([^}]+)\}", r"\1", latex_str)
    latex_str = latex_str.replace(r"\mathcal", "")
    # Handle \mathbb{content} -> content
    latex_str = re.sub(r"\\mathbb\s*\{([^}]+)\}", r"\1", latex_str)
    latex_str = latex_str.replace(r"\mathbb", "")

    # Replace commands
    latex_str = latex_str.replace(r"\pmb", r"\mathbf")
    latex_str = latex_str.replace(r"\textbf", r"\mathbf")
    latex_str = latex_str.replace(r"\textsf", r"\mathsf")
    latex_str = latex_str.replace(r"\textrm", r"\mathrm")
    
    # Fix \mathbf x -> \mathbf{x} (Matplotlib requires braces)
    # Matches \mathbf or \mathsf followed by optional space and then a single char or a backslash command
    # Excludes cases where the argument is already in braces (checked implicitly by character class)
    pattern = r"(\\(?:mathbf|mathsf))\s+([a-zA-Z0-9]|\\[a-zA-Z]+)"
    latex_str = re.sub(pattern, r"\1{\2}", latex_str)

    # Handle \textcircled{x} -> (x)
    latex_str = re.sub(r"\\textcircled\s*\{([^}]+)\}", r"(\1)", latex_str)
    return latex_str


def _render_latex(latex_str: str, is_block: bool = False) -> str | None:
    fig = None
    tmp_path = None
    try:
        _configure_matplotlib_font()
        latex_str = _sanitize_latex(latex_str)
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${latex_str}$", fontsize=14 if is_block else 12)
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        fig.savefig(tmp_path, dpi=300, bbox_inches='tight', pad_inches=0.02, transparent=True)
        return tmp_path
    except Exception as e:
        print(f"[DEBUG-HY] Latex render error: {latex_str}, error: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return None
    finally:
        if fig is not None:
            plt.close(fig)


def _parse_markdown(md_text: str, base_dir: str, max_width: float, styles):
    story = []
    in_code = False
    code_lines = []
    bullet_buffer = []
    try:
        code_style = styles["Code"]
    except KeyError:
        code_style = ParagraphStyle("CodeLocal", parent=styles["Normal"], fontName="Courier", fontSize=9, leading=11)
    
    # Pre-process block math to single line
    # Matches $$...$$ across multiple lines
    md_text = re.sub(r'\$\$(.*?)\$\$', lambda m: '$$' + m.group(1).replace('\n', ' ') + '$$', md_text, flags=re.DOTALL)

    def replace_inline_math(match):
        latex = match.group(1)
        img_path = _render_latex(latex, is_block=False)
        if img_path:
            try:
                iw, ih = ImageReader(img_path).getSize()
                # Matplotlib saves at 300 DPI, ReportLab uses 72 DPI
                # Scale down to match text size
                scale = 72.0 / 300.0
                new_w = iw * scale
                new_h = ih * scale
                # Adjust valign to align with text baseline (approx -1/4 of height)
                valign = -new_h / 4.0 
                return f'<img src="{img_path}" width="{new_w}" height="{new_h}" valign="{valign}"/>'
            except Exception:
                return f'<img src="{img_path}" valign="-3"/>'
        return match.group(0)

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip("\n")

        m_block_math = re.match(r"^\$\$(.+)\$\$$", line.strip())
        if m_block_math:
            latex_str = m_block_math.group(1).strip()
            img_path = _render_latex(latex_str, is_block=True)
            if img_path:
                try:
                    img = Image(img_path)
                    # Scale for block math as well
                    iw, ih = img.imageWidth, img.imageHeight
                    scale = 72.0 / 300.0
                    img.drawWidth = iw * scale
                    img.drawHeight = ih * scale
                    
                    story.append(_scale_image_component(img, max_width))
                    story.append(Spacer(1, 0.2 * inch))
                except Exception:
                    pass
            continue

        m_html_img = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"'][^>]*>", line, flags=re.IGNORECASE)
        if m_html_img:
            img_src = m_html_img.group(1).strip()
            if img_src.lower().endswith(".svg"):
                pass
            else:
                tmp_path = None
                try:
                    if re.match(r"^https?://", img_src):
                        tmp_path = _download_remote_image(img_src)
                        use_path = tmp_path
                    else:
                        use_path = img_src
                        if not os.path.isabs(use_path):
                            use_path = os.path.join(base_dir, use_path)
                    if use_path and os.path.exists(use_path):
                        try:
                            img = Image(use_path)
                        except Exception:
                            img = None
                        if img:
                            story.append(_scale_image_component(img, max_width))
                            story.append(Spacer(1, 0.2 * inch))
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
            continue
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                story.append(Preformatted("\n".join(code_lines), code_style))
                story.append(Spacer(1, 0.2 * inch))
            continue
        if in_code:
            code_lines.append(line)
            continue
        m_img = re.match(r"^\s*!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)\s*$", line)
        if m_img:
            img_path = m_img.group(1)
            if not re.match(r"^https?://", img_path):
                if not os.path.isabs(img_path):
                    img_path = os.path.join(base_dir, img_path)
            if re.match(r"^https?://", img_path):
                if img_path.lower().endswith(".svg"):
                    pass
                else:
                    tmp_path = None
                    try:
                        tmp_path = _download_remote_image(img_path)
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                img = Image(tmp_path)
                            except Exception:
                                img = None
                            if img:
                                story.append(_scale_image_component(img, max_width))
                                story.append(Spacer(1, 0.2 * inch))
                    finally:
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
            elif os.path.exists(img_path):
                try:
                    img = Image(img_path)
                except Exception:
                    img = None
                if img:
                    story.append(_scale_image_component(img, max_width))
                    story.append(Spacer(1, 0.2 * inch))
            continue
        if re.match(r"^\s*([-*])\s+.+", line):
            bullet_buffer.append(line.strip()[1:].strip())
            continue
        if bullet_buffer and not line.strip():
            items = [ListItem(Paragraph(t, styles["Normal"])) for t in bullet_buffer]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
            story.append(Spacer(1, 0.2 * inch))
            bullet_buffer = []
            continue
        if not line.strip():
            story.append(Spacer(1, 0.15 * inch))
            continue
        m_h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m_h:
            level = len(m_h.group(1))
            text = m_h.group(2).strip()
            text = re.sub(r"<[^>]+>", "", text)
            text = html.escape(text, quote=False)
            text = re.sub(r"\$([^\$]+)\$", replace_inline_math, text)
            if level == 1:
                story.append(Paragraph(text, styles["Heading1"]))
            elif level == 2:
                story.append(Paragraph(text, styles["Heading2"]))
            elif level == 3:
                story.append(Paragraph(text, styles["Heading3"]))
            else:
                story.append(Paragraph(text, styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))
            continue
        sanitized = re.sub(r"<[^>]+>", "", line)
        sanitized = html.escape(sanitized, quote=False)
        sanitized = re.sub(r"\$([^\$]+)\$", replace_inline_math, sanitized)
        if not sanitized.strip():
            continue
        story.append(Paragraph(sanitized, styles["Normal"]))
    if bullet_buffer:
        items = [ListItem(Paragraph(t, styles["Normal"])) for t in bullet_buffer]
        story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
    return story


def convert_md_to_pdf(md_path: str) -> str:
    print(f"【DEBUG-HY】: {md_path} in convert_md_to_pdf", file=sys.stderr, flush=True)
    md_path = os.path.abspath(md_path)
    if not os.path.exists(md_path):
        raise FileNotFoundError(md_path)
    base_dir = os.path.dirname(md_path)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    # 获取md的无后缀文件名
    md_base_name = os.path.splitext(os.path.basename(md_path))[0]
    test_dir = os.path.join(project_root, f"temp_pdf/{md_base_name}")
    os.makedirs(test_dir, exist_ok=True)
    out_path = os.path.join(test_dir, os.path.splitext(os.path.basename(md_path))[0] + ".pdf")
    font_name = _choose_font()
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = font_name
    styles["Heading1"].fontName = font_name
    styles["Heading2"].fontName = font_name
    styles["Heading3"].fontName = font_name
    print(f"【DEBUG-HY】: {md_path} styles build", file=sys.stderr, flush=True)
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
    print(f"【DEBUG-HY】: {md_path} doc build", file=sys.stderr, flush=True)
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    story = _parse_markdown(text, base_dir, doc.width, styles)
    doc.build(story)
    return out_path


def is_scanned_pdf_from_stream(pdf_bytes):
    """
    通过 PDF 二进制流判断其是否为扫描型 PDF。
    
    逻辑：即使存在透明文本层（双层PDF），
    如果页面底层存在一张覆盖面积 > 90% 的图像，即判定为扫描件。
    """
    # 将二进制流加载到内存
    stream = io.BytesIO(pdf_bytes)
    
    try:
        doc = fitz.open(stream=stream, filetype="pdf")
    except Exception as e:
        return False

    # 抽样前 2 页进行深度像素分析
    pages_to_check = min(len(doc), 2)
    is_scanned_structure = False

    for i in range(pages_to_check):
        page = doc[i]
        page_area = page.rect.width * page.rect.height
        
        # 获取页面所有图像的信息
        img_info = page.get_image_info()
        
        # 核心判断：寻找填满页面的大图
        for img in img_info:
            # 计算单个图像在页面上的实际占用面积
            # bbox 为 [x0, y0, x1, y1]
            bbox = img['bbox']
            img_display_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            
            # 如果某张图片占据了页面 90% 以上的面积，说明文字极大概率是“浮”在图片上的 OCR 层
            if img_display_area > (page_area * 0.9):
                is_scanned_structure = True
                break
        
        if is_scanned_structure:
            break

    doc.close()

    return is_scanned_structure

def do_parse(
    output_dir,  # Output directory for storing parsing results
    pdf_file_names: list[str],  # List of PDF file names to be parsed
    pdf_bytes_list: list[bytes],  # List of PDF bytes to be parsed
    p_lang_list: list[str],  # List of languages for each PDF, default is 'ch' (Chinese)
    backend="pipeline",  # The backend for parsing PDF, default is 'pipeline'
    parse_method="auto",  # The method for parsing PDF, default is 'auto'
    formula_enable=True,  # Enable formula parsing
    table_enable=True,  # Enable table parsing
    server_url=None,  # Server URL for vlm-http-client backend
    f_draw_layout_bbox=False,  # Whether to draw layout bounding boxes
    f_draw_span_bbox=False,  # Whether to draw span bounding boxes
    f_dump_md=True,  # Whether to dump markdown files
    f_dump_middle_json=False,  # Whether to dump middle JSON files
    f_dump_model_output=True,  # Whether to dump model output files
    f_dump_orig_pdf=False,  # Whether to dump original PDF files
    f_dump_content_list=False,  # Whether to dump content list files
    f_make_md_mode=MakeMode.MM_MD,  # The mode for making markdown content, default is MM_MD
    start_page_id=0,  # Start page ID for parsing, default is 0
    end_page_id=None,  # End page ID for parsing, default is None (parse all pages until the end of the document)
):

    try:
        backend = backend[4:]

        f_draw_span_bbox = False
        parse_method = "vlm"
        for idx, pdf_bytes in enumerate(pdf_bytes_list):
            pdf_file_name = pdf_file_names[idx]
            pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, '.')
            image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)
            middle_json, infer_result = vlm_doc_analyze(pdf_bytes, image_writer=image_writer, backend=backend, server_url=server_url)

            pdf_info = middle_json["pdf_info"]

            _process_output(
                pdf_info, pdf_bytes, pdf_file_name, local_md_dir, local_image_dir,
                md_writer, f_draw_layout_bbox, f_draw_span_bbox, f_dump_orig_pdf,
                f_dump_md, f_dump_content_list, f_dump_middle_json, f_dump_model_output,
                f_make_md_mode, middle_json, infer_result, is_pipeline=False
            )
    finally:
        # Clear models and memory
        VLMModelSingleton._models.clear()
        PipelineModelSingleton._models.clear()
        clean_memory()


def _process_output(
        pdf_info,
        pdf_bytes,
        pdf_file_name,
        local_md_dir,
        local_image_dir,
        md_writer,
        f_draw_layout_bbox,
        f_draw_span_bbox,
        f_dump_orig_pdf,
        f_dump_md,
        f_dump_content_list,
        f_dump_middle_json,
        f_dump_model_output,
        f_make_md_mode,
        middle_json,
        model_output=None,
        is_pipeline=True
):
    """处理输出文件"""
    if f_draw_layout_bbox:
        draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_layout.pdf")

    if f_draw_span_bbox:
        draw_span_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_span.pdf")

    if f_dump_orig_pdf:
        md_writer.write(
            f"{pdf_file_name}_origin.pdf",
            pdf_bytes,
        )

    image_dir = str(os.path.basename(local_image_dir))

    if f_dump_md:
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        md_content_str = make_func(pdf_info, f_make_md_mode, image_dir)
        md_writer.write_string(
            f"{pdf_file_name}.md",
            md_content_str,
        )

    if f_dump_content_list:
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        content_list = make_func(pdf_info, MakeMode.CONTENT_LIST, image_dir)
        md_writer.write_string(
            f"{pdf_file_name}_content_list.json",
            json.dumps(content_list, ensure_ascii=False, indent=4),
        )

    if f_dump_middle_json:
        md_writer.write_string(
            f"{pdf_file_name}_middle.json",
            json.dumps(middle_json, ensure_ascii=False, indent=4),
        )

    if f_dump_model_output:
        md_writer.write_string(
            f"{pdf_file_name}_model.json",
            json.dumps(model_output, ensure_ascii=False, indent=4),
        )

    logger.info(f"local output dir is {local_md_dir}")


def parse_pdf_stream(
        file_stream,
        output_dir,
        file_name_prefix="output",
        lang="ch",
        start_page_id=0,
        end_page_id=None
):
    """
    Parse a PDF or image stream using vlm-vllm-engine backend.

    Args:
        file_stream: File-like object (io.read) or bytes
        output_dir: Output directory
        file_name_prefix: Prefix for output files
        lang: Language hint
        start_page_id: Start page index
        end_page_id: End page index
    """
    os.environ['MINERU_MODEL_SOURCE'] = "modelscope"
    backend = "vlm-vllm-engine"

    if hasattr(file_stream, "read"):
        file_bytes = file_stream.read()
    else:
        file_bytes = file_stream

    # Check suffix and convert image to pdf if needed
    suffix = guess_suffix_by_bytes(file_bytes)
    image_suffixes = ["png", "jpeg", "jp2", "webp", "gif", "bmp", "jpg", "tiff"]

    if suffix in image_suffixes:
        file_bytes = images_bytes_to_pdf_bytes(file_bytes)

    do_parse(
        output_dir=output_dir,
        pdf_file_names=[file_name_prefix],
        pdf_bytes_list=[file_bytes],
        p_lang_list=[lang],
        backend=backend,
        parse_method="vlm",
        start_page_id=start_page_id,
        end_page_id=end_page_id
    )
    print(f"【DEBUG-HY】: {file_name_prefix} parse it done", file=sys.stderr, flush=True)
    # 解析完成之后，需要重新解析为pdf文件
    # 从目标文件夹进行转换
    file_path = os.path.join(os.path.join(output_dir, file_name_prefix), f"{file_name_prefix}.md")
    print(f"【DEBUG-HY】: {file_path} is target md path", file=sys.stderr, flush=True)
    try:
        outpath = convert_md_to_pdf(file_path)
    except Exception as e:
        print(f"【DEBUG-HY】: {e} is convert md to pdf error", file=sys.stderr, flush=True)
        return None
    print(f"【DEBUG-HY】: {outpath} is target pdf path", file=sys.stderr, flush=True)
    # 从输出路径读取pdf文件返回
    with open(outpath, "rb") as f:
        pdf_bytes = f.read()
    print(f"【DEBUG-HY】: {len(pdf_bytes)} is target pdf bytes len", file=sys.stderr, flush=True)
    return pdf_bytes




if __name__ == "__main__":
    os.environ['MINERU_MODEL_SOURCE'] = "modelscope"
    with open("/home/hit802/docs/二次纤维角质化及其纸页损伤研究.pdf", "rb") as f:
        parse_pdf_stream(
            f,
            output_dir="/home/hit802/RAG1/ragflow/rag/utils",
            file_name_prefix="output",
            lang="ch",
            start_page_id=0,
            end_page_id=None
        )
