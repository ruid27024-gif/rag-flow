import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.app.paper import chunk

def callback(*args, **kwargs):
    # print(f"Callback: args={args} kwargs={kwargs}")
    pass

if __name__ == "__main__":
    paper_path = "/home/hit802/RAG1/ragflow/test/62″热磨机主轴及密封系统的设计.pdf"
    if os.path.exists(paper_path):
        with open(paper_path, "rb") as f:
            paper_bytes = f.read()
        
        print("\n--- Test 1: Default Backend (Expected: vlm-vllm-engine) ---")
        try:
            chunk(filename=paper_path, binary=paper_bytes, callback=callback, 
                  parser_config={"layout_recognize": "MinerU"})
        except Exception as e:
            print(f"Error in Test 1: {e}")

            
    else:
        print(f"File not found: {paper_path}")
