import json
from pathlib import Path

from app.domains.extraction.extractor import RuleBasedRelationExtractor
from app.domains.extraction.family_json_builder import FamilyJsonBuilder


def main():
    text = """
    Ông Nguyễn Văn An kết hôn với bà Trần Thị Hạnh.
    Ông Nguyễn Văn An và bà Trần Thị Hạnh sinh được Nguyễn Văn Bình và Nguyễn Thị Lan.
    Nguyễn Văn Bình kết hôn với Lê Thị Hoa, sinh được Nguyễn Văn Nam và Nguyễn Thị Mai.
    Nguyễn Thị Lan kết hôn với Phạm Văn Hùng và có con là Phạm Thị Ngọc.
    """

    extractor = RuleBasedRelationExtractor()
    relations = extractor.extract_relations(text)

    builder = FamilyJsonBuilder()
    family_graph = builder.build(relations)

    output_path = Path("data/output_family_graph.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(family_graph, file, ensure_ascii=False, indent=2)

    print(f"Exported to: {output_path}")

    print("\nPeople:")
    for person in family_graph["people"]:
        print(person)

    print("\nRelationships:")
    for relationship in family_graph["relationships"]:
        print(relationship)


if __name__ == "__main__":
    main()