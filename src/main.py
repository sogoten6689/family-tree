import argparse
from src.loader import load_family_json
from src.validator import validate_data
from src.graph_builder import build_family_graph
from src.visualize import draw_static_png, draw_interactive_html


def main():
    parser = argparse.ArgumentParser(description="Build basic family tree from JSON data")
    parser.add_argument("--input", type=str, default="data/sample_family.json", help="Path to input JSON")
    args = parser.parse_args()

    people, relationships = load_family_json(args.input)

    errors = validate_data(people, relationships)
    if errors:
        print("Validation errors found:")
        for e in errors:
            print(" -", e)
        print("\nVui lòng sửa dữ liệu JSON rồi chạy lại.")
        return

    G = build_family_graph(people, relationships)
    draw_static_png(G, "output/family_tree.png")
    draw_interactive_html(G, "output/family_tree.html")

    print("Done")
    print(" - Static image: output/family_tree.png")
    print(" - Interactive html: output/family_tree.html")


if __name__ == "__main__":
    main()
