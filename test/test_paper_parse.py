import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.app.paper import chunk

def callback(*args, **kwargs):
    print(f"Callback: args={args} kwargs={kwargs}")

if __name__ == "__main__":
    paper_path = "/home/hit802/RAG1/ragflow/test/1-s2.0-S1877050922001363-main (1).pdf"
    if os.path.exists(paper_path):
        with open(paper_path, "rb") as f:
            paper_bytes = f.read()
            chunks = chunk(filename=paper_path, binary=paper_bytes, callback=callback)
        # print(chunks)
    else:
        print(f"File not found: {paper_path}")
