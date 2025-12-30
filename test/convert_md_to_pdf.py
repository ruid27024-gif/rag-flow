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
    # Remove unsupported commands
    latex_str = latex_str.replace(r"\scriptstyle", "")
    latex_str = latex_str.replace(r"\smash", "")
    latex_str = latex_str.replace(r"\displaystyle", "")
    latex_str = latex_str.replace(r"\bigl", "")
    latex_str = latex_str.replace(r"\bigr", "")
    latex_str = latex_str.replace(r"\phantom", "")
    latex_str = latex_str.replace(r"\atop", "")
    
    # Handle array environment (Matplotlib doesn't support array)
    # Be more aggressive: remove \begin{array}{...} and \end{array}, replace \\ with space
    latex_str = re.sub(r"\\begin\{array\}\{[^}]+\}", "", latex_str)
    latex_str = re.sub(r"\\begin\{array\}", "", latex_str) # Catch malformed
    latex_str = latex_str.replace(r"\end{array}", "")
    latex_str = latex_str.replace(r"\\", " ")
    
    # Remove \overbrace{...}^{...} or \overbrace{...}
    # Using a loop to handle nested braces or complex content inside overbrace
    # Simple regex won't work well for nested braces, but we can try to just remove the command
    # and keep the content. Since parsing braces is hard with regex, we'll strip the command name
    # and hope the braces balance out or are ignored if they are just grouping.
    # Actually, \overbrace{content} -> content is what we want.
    # Mathtext might complain about loose braces if we just strip the command, but let's try
    # simply removing the command keyword first.
    latex_str = latex_str.replace(r"\overbrace", "")
    
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
    try:
        _configure_matplotlib_font()
        latex_str = _sanitize_latex(latex_str)
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${latex_str}$", fontsize=14 if is_block else 12)
        
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        fig.savefig(tmp_path, dpi=300, bbox_inches='tight', pad_inches=0.02, transparent=True)
        plt.close(fig)
        return tmp_path
    except Exception as e:
        print(f"Latex render error: {latex_str}, error: {e}")
        return None


def _parse_markdown(md_text: str, base_dir: str, max_width: float, styles):
    story = []
    in_code = False
    code_lines = []
    bullet_buffer = []
    
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
                story.append(Preformatted("\n".join(code_lines), ParagraphStyle("Code", parent=styles["Code"], fontName="Courier", fontSize=9, leading=11)))
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
    md_path = os.path.abspath(md_path)
    if not os.path.exists(md_path):
        raise FileNotFoundError(md_path)
    base_dir = os.path.dirname(md_path)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    test_dir = os.path.join(project_root, "test")
    out_path = os.path.join(test_dir, os.path.splitext(os.path.basename(md_path))[0] + ".pdf")
    font_name = _choose_font()
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = font_name
    styles["Heading1"].fontName = font_name
    styles["Heading2"].fontName = font_name
    styles["Heading3"].fontName = font_name
    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    story = _parse_markdown(text, base_dir, doc.width, styles)
    doc.build(story)
    return out_path


if __name__ == "__main__":
    md_file_path = "/home/hit802/MinerU/demo/output/二次纤维角质化及其纸页损伤研究/auto/二次纤维角质化及其纸页损伤研究.md"
    if os.path.exists(md_file_path):
        pdf_path = convert_md_to_pdf(md_file_path)
        print(pdf_path)
    else:
        print(md_file_path)
