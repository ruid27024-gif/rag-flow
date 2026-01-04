
import sys
import os
import logging

# Add project root to sys.path
sys.path.append(os.getcwd())

# Mocking some dependencies if needed, but let's try importing first.
try:
    from rag.app.paper import chunk
    print("Successfully imported chunk from rag.app.paper")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

def test_chunk_mineru():
    filename = "test/README.pdf"
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return

    print(f"Testing chunk with {filename} using MinerU...")
    
    # Callback to print progress
    def callback(prog=None, msg=None):
        print(f"Callback: {prog} - {msg}")

    try:
        # Pass parser_config with layout_recognize="MinerU"
        parser_config = {"layout_recognize": "MinerU"}
        chunks = chunk(filename, parser_config=parser_config, callback=callback)
        
        print(f"Chunking complete. Generated {len(chunks)} chunks.")
        for i, c in enumerate(chunks[:3]):
            print(f"Chunk {i}: {c['content_with_weight'][:100]}...")
            
    except Exception as e:
        print(f"Error during chunking: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_chunk_mineru()
