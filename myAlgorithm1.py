import sys
from steinerGraph import Graph

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("JSONファイルを指定してください")
        sys.exit(1)
    vertices, edges = load_from_json(sys.argv[1])
