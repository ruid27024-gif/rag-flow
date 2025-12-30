import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deepdoc.dolphin.model import process_single_layout, get_model,process_single_image,process_document
from deepdoc.dolphin.utils.utils import convert_pdf_to_images
from PIL import Image

if __name__ == "__main__":
    model = get_model()
    
    # Use an existing PDF in the directory
    pdf_files = "/home/hit802/RAG1/ragflow/test/二次纤维角质化及其纸页损伤研究.pdf"
    process_document(pdf_files, model=model, save_dir="/home/hit802/RAG1/ragflow/test")
    # pdf_images = convert_pdf_to_images(pdf_files)
    # image = pdf_images[7]
    # process_single_image(image, model=model, save_dir="/home/hit802/RAG1/ragflow/test",image_name=f"page_8.png")