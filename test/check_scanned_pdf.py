import fitz  # PyMuPDF
import io

def identify_pdf_type_from_stream(pdf_bytes):
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
        return f"无法解析 PDF 流: {e}"

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

    if is_scanned_structure:
        return "扫描型/双层 PDF (底层为全页图像，肉眼看很模糊)"
    else:
        return "原生矢量 PDF (由软件排版生成，文字清晰且无底层全页大图)"

# 使用示例：
with open("/home/hit802/RAG1/ragflow/test/二次纤维角质化及其纸页损伤研究.pdf", "rb") as f:
    pdf_data = f.read()
    result = identify_pdf_type_from_stream(pdf_data)
    print(result)