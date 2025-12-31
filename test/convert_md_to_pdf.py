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
        attempts = [latex_str, _sanitize_latex(latex_str)]
        for idx, content in enumerate(attempts):
            try:
                fig = plt.figure(figsize=(0.01, 0.01))
                fig.text(0, 0, f"${content}$", fontsize=14 if is_block else 12)
                fd, tmp_path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                fig.savefig(tmp_path, dpi=300, bbox_inches='tight', pad_inches=0.02, transparent=True)
                return tmp_path
            except Exception as e:
                print(f"[DEBUG-HY] Latex render attempt {idx+1} failed: {content}, error: {e}")
                if fig is not None:
                    try:
                        plt.close(fig)
                    except Exception:
                        pass
                fig = None
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                tmp_path = None
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

    lines = md_text.splitlines()
    n = len(lines)
    i = 0
    current_para_lines: list[str] = []

    def ends_with_sentence_punct(text: str) -> bool:
        return bool(re.search(r"[。！？.!?]$", text.strip()))

    def flush_paragraph_buffer():
        nonlocal current_para_lines
        if not current_para_lines:
            return
        text = " ".join([ln.rstrip("\n") for ln in current_para_lines]).strip()
        current_para_lines = []
        if not text:
            return
        sanitized = html.escape(text, quote=False)
        parts = re.split(r"(\$[^\$]+\$)", sanitized)
        new_parts = []
        for part in parts:
            if part.startswith("$") and part.endswith("$"):
                new_parts.append(part)
            else:
                new_parts.append(re.sub(r"([\u4e00-\u9fa5])", r"\1" + "\u200b", part))
        sanitized = "".join(new_parts)
        if sanitized.strip():
            story.append(Paragraph(sanitized, styles["Indented"]))

    def make_caption_paragraph(text: str):
        sanitized = html.escape(text, quote=False)
        parts = re.split(r"(\$[^\$]+\$)", sanitized)
        new_parts = []
        for part in parts:
            if part.startswith("$") and part.endswith("$"):
                new_parts.append(part)
            else:
                new_parts.append(re.sub(r"([\u4e00-\u9fa5])", r"\1" + "\u200b", part))
        sanitized = "".join(new_parts)
        story.append(Paragraph(sanitized, styles["Caption"]))

    def add_image_to_story(use_path: str):
        try:
            img = Image(use_path)
        except Exception:
            img = None
        if img:
            story.append(_scale_image_component(img, max_width))
            story.append(Spacer(1, 0.2 * inch))

    def is_caption_line(s: str) -> bool:
        return bool(re.match(r"^\s*图[\s\u200b]*\d+", s.strip()))

    def is_desc_line(s: str) -> bool:
        return bool(re.match(r"^\s*\d+[\.\uFF0E、．]\s+", s.strip()))

    while i < n:
        raw_line = lines[i]
        line = raw_line.rstrip("\n")

        if line.strip().startswith("```"):
            flush_paragraph_buffer()
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                story.append(Preformatted("\n".join(code_lines), code_style))
                story.append(Spacer(1, 0.2 * inch))
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if re.match(r"^\s*([-*])\s+.+", line):
            flush_paragraph_buffer()
            bullet_buffer.append(line.strip()[1:].strip())
            i += 1
            continue
        if bullet_buffer and not line.strip():
            items = [ListItem(Paragraph(t, styles["Normal"])) for t in bullet_buffer]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
            bullet_buffer = []
            i += 1
            continue

        m_h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m_h:
            flush_paragraph_buffer()
            level = len(m_h.group(1))
            text = m_h.group(2).strip()
            if re.match(r"^[（(]\s*\d+(?:\.\d+)?\s*[）)]", text):
                sanitized = html.escape(text, quote=False)
                parts = re.split(r"(\$[^\$]+\$)", sanitized)
                new_parts = []
                for part in parts:
                    if part.startswith("$") and part.endswith("$"):
                        new_parts.append(part)
                    else:
                        new_parts.append(re.sub(r"([\u4e00-\u9fa5])", r"\1" + "\u200b", part))
                sanitized = "".join(new_parts)
                story.append(Paragraph(sanitized, styles["Normal"]))
                story.append(Spacer(1, 0.1 * inch))
            else:
                sanitized = html.escape(text, quote=False)
                parts = re.split(r"(\$[^\$]+\$)", sanitized)
                new_parts = []
                for part in parts:
                    if part.startswith("$") and part.endswith("$"):
                        new_parts.append(part)
                    else:
                        new_parts.append(re.sub(r"([\u4e00-\u9fa5])", r"\1" + "\u200b", part))
                sanitized = "".join(new_parts)
                if level == 1:
                    story.append(Paragraph(sanitized, styles["Heading1"]))
                elif level == 2:
                    story.append(Paragraph(sanitized, styles["Heading2"]))
                elif level == 3:
                    story.append(Paragraph(sanitized, styles["Heading3"]))
                else:
                    story.append(Paragraph(sanitized, styles["Normal"]))
                story.append(Spacer(1, 0.1 * inch))
            i += 1
            continue

        m_html_img = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"'][^>]*>", line, flags=re.IGNORECASE)
        m_img_md = re.match(r"^\s*!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)\s*$", line)
        if m_html_img or m_img_md or is_caption_line(line) or is_desc_line(line):
            # Build block
            j = i
            block_lines = []
            while j < n and lines[j].strip():
                block_lines.append(lines[j])
                j += 1
            # Find image in block
            pass_src = None
            for bl in block_lines:
                m_hi = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"'][^>]*>", bl, flags=re.IGNORECASE)
                m_md = re.match(r"^\s*!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)\s*$", bl)
                if m_hi:
                    img_src = m_hi.group(1).strip()
                    if not img_src.lower().endswith(".svg"):
                        if re.match(r"^https?://", img_src):
                            tmp_path = _download_remote_image(img_src)
                            pass_src = tmp_path
                        else:
                            use_path = img_src
                            if not os.path.isabs(use_path):
                                use_path = os.path.join(base_dir, use_path)
                            pass_src = use_path
                    break
                if m_md:
                    img_path = m_md.group(1)
                    if not re.match(r"^https?://", img_path):
                        if not os.path.isabs(img_path):
                            img_path = os.path.join(base_dir, img_path)
                    if not img_path.lower().endswith(".svg"):
                        pass_src = img_path
                    break
            caption_line = None
            description_lines = []
            for bl in block_lines:
                if is_caption_line(bl):
                    caption_line = bl.strip()
                elif not (re.match(r"^\s*!\[[^\]]*\]\(", bl) or re.search(r"<img[^>]+src=", bl, flags=re.IGNORECASE)):
                    if is_desc_line(bl) or bl.strip():
                        description_lines.append(bl.strip())
            combined_caption = None
            if caption_line:
                if description_lines:
                    combined_caption = (caption_line + " " + " ".join(description_lines)).strip()
                else:
                    combined_caption = caption_line.strip()
            prev_text = " ".join(current_para_lines).strip() if current_para_lines else ""
            prev_incomplete = bool(prev_text) and not ends_with_sentence_punct(prev_text)

            # Determine next paragraph after the block for possible merge with previous incomplete
            k = j
            while k < n and not lines[k].strip():
                k += 1
            next_para_lines = []
            t = k
            while t < n:
                nxt = lines[t]
                if not nxt.strip():
                    break
                if re.match(r"^\s*!\[[^\]]*\]\(", nxt) or re.search(r"<img[^>]+src=", nxt, flags=re.IGNORECASE):
                    break
                if re.match(r"^(#{1,6})\s+", nxt):
                    break
                if nxt.strip().startswith("```"):
                    break
                if re.match(r"^\s*([-*])\s+.+", nxt):
                    break
                next_para_lines.append(nxt.rstrip("\n"))
                t += 1

            # Apply ordering: if previous incomplete, merge next paragraph first, then image and caption
            if prev_incomplete and next_para_lines:
                current_para_lines.extend(next_para_lines)
                flush_paragraph_buffer()
                # Insert image first
                if pass_src:
                    if re.match(r"^https?://", pass_src or ""):
                        tmp_path2 = _download_remote_image(pass_src)
                        if tmp_path2 and os.path.exists(tmp_path2):
                            add_image_to_story(tmp_path2)
                            try:
                                os.remove(tmp_path2)
                            except Exception:
                                pass
                    else:
                        if os.path.exists(pass_src):
                            add_image_to_story(pass_src)
                # Insert caption (merged with description) if exists, else keep description as normal paragraphs
                if combined_caption:
                    make_caption_paragraph(combined_caption)
                else:
                    for desc in description_lines:
                        sanitized = html.escape(desc, quote=False)
                        parts = re.split(r"(\$[^\$]+\$)", sanitized)
                        new_parts = []
                        for part in parts:
                            if part.startswith("$") and part.endswith("$"):
                                new_parts.append(part)
                            else:
                                new_parts.append(re.sub(r"([\u4e00-\u9fa5])", r"\1" + "\u200b", part))
                        sanitized = "".join(new_parts)
                        story.append(Paragraph(sanitized, styles["Indented"]))
                i = t
                continue
            else:
                # Normal order: flush current text, then image at top of block, then caption (merged) or description lines
                flush_paragraph_buffer()
                if pass_src:
                    if re.match(r"^https?://", pass_src or ""):
                        tmp_path2 = _download_remote_image(pass_src)
                        if tmp_path2 and os.path.exists(tmp_path2):
                            add_image_to_story(tmp_path2)
                            try:
                                os.remove(tmp_path2)
                            except Exception:
                                pass
                    else:
                        if os.path.exists(pass_src):
                            add_image_to_story(pass_src)
                if combined_caption:
                    make_caption_paragraph(combined_caption)
                else:
                    for desc in description_lines:
                        sanitized = html.escape(desc, quote=False)
                        parts = re.split(r"(\$[^\$]+\$)", sanitized)
                        new_parts = []
                        for part in parts:
                            if part.startswith("$") and part.endswith("$"):
                                new_parts.append(part)
                            else:
                                new_parts.append(re.sub(r"([\u4e00-\u9fa5])", r"\1" + "\u200b", part))
                        sanitized = "".join(new_parts)
                        story.append(Paragraph(sanitized, styles["Indented"]))
                i = j
                continue

        if not line.strip():
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and (
                re.match(r"^\s*!\[[^\]]*\]\(", lines[j]) or
                re.search(r"<img[^>]+src=", lines[j], flags=re.IGNORECASE) or
                is_caption_line(lines[j]) or
                is_desc_line(lines[j])
            ):
                i += 1
                continue
            flush_paragraph_buffer()
            i += 1
            continue

        # Accumulate normal text line into paragraph buffer
        current_para_lines.append(line)
        i += 1

    # End of file: flush any remaining
    flush_paragraph_buffer()
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
    
    # Create Indented style for normal paragraphs
    # Indent 2 chars approx. Assuming 10pt font, 2 chars is ~20pt.
    # reportlab styles["Normal"] defaults to 10pt usually.
    # Let's use fontSize * 2
    normal_font_size = styles["Normal"].fontSize
    styles.add(ParagraphStyle(
        "Indented", 
        parent=styles["Normal"], 
        firstLineIndent=normal_font_size * 2
    ))
    
    # Create Caption style for figures
    from reportlab.lib.enums import TA_CENTER
    styles.add(ParagraphStyle(
        "Caption", 
        parent=styles["Normal"], 
        alignment=TA_CENTER
    ))

    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    story = _parse_markdown(text, base_dir, doc.width, styles)
    doc.build(story)
    return out_path


if __name__ == "__main__":
    md_file_path = "/home/hit802/RAG1/ragflow/temp_pdf/62″热磨机主轴及密封系统的设计/62″热磨机主轴及密封系统的设计.md"
    if os.path.exists(md_file_path):
        pdf_path = convert_md_to_pdf(md_file_path)
        print(pdf_path)
    else:
        print(md_file_path)
