import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.app.paper import chunk

def callback(*args, **kwargs):
    print(f"Callback: args={args} kwargs={kwargs}")

if __name__ == "__main__":
    paper_path = "/home/hit802/RAG1/ragflow/test/62″热磨机主轴及密封系统的设计.pdf"
    if os.path.exists(paper_path):
        with open(paper_path, "rb") as f:
            paper_bytes = f.read()
            # Pass parser_config to enable mineru
            chunks = chunk(filename=paper_path, binary=paper_bytes, callback=callback, 
                           parser_config={"layout_recognize": "MinerU"})
        
        # Inspect chunks for image descriptions
        print("\n--- Inspection Results ---")
        found_graph = False
        for i, c in enumerate(chunks):
            # Check if this chunk looks like the expected image description
            if "Visual Type:" in str(c) and "蒸煮预热压力与纤维热水抽出物的关系" in str(c):
                print(f"Found candidate chunk {i}:")
                print(c)
                found_graph = True
            elif "Visual Type:" in str(c):
                 print(f"Found other vision chunk {i}:")
                 # print(c) # Print others if needed, but keep output clean
        
        if not found_graph:
            print("Did not find the specific graph description in the chunks.")
            # Print all chunks to see what we got
            # print(json.dumps(chunks, ensure_ascii=False, indent=2, default=str))

    else:
        print(f"File not found: {paper_path}")
