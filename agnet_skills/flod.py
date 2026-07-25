from pathlib import Path

BASE_DIR = Path(r"C:\Users\28023\Desktop\rag-flow\agnet_skills\skills").resolve()

def build_file_tree(directory: Path):
    directory = directory.resolve()

    result = []

    for item in directory.iterdir():
        node = {
            "name": item.name,
            "path": str(item.relative_to(BASE_DIR)),
            "type": "directory" if item.is_dir() else "file",
        }

        if item.is_dir():
            node["children"] = build_file_tree(item)

        result.append(node)

    return result


if __name__ == "__main__":
    print(build_file_tree(BASE_DIR))