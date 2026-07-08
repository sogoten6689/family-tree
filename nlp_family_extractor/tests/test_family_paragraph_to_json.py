import json
from dataclasses import asdict
from pathlib import Path

from app.domains.extraction.extractor import RuleBasedRelationExtractor


def build_family_json(relations):
    people_map = {}
    relationships = []

    def get_person_id(name: str) -> str:
        if name not in people_map:
            person_id = f"P{len(people_map) + 1:03d}"
            people_map[name] = {
                "id": person_id,
                "full_name": name,
            }

        return people_map[name]["id"]

    for relation in relations:
        source_id = get_person_id(relation.source_person)
        target_id = get_person_id(relation.target_person)

        relationships.append(
            {
                "from_id": source_id,
                "from_name": relation.source_person,
                "to_id": target_id,
                "to_name": relation.target_person,
                "type": relation.relation_type,
                "confidence": relation.confidence,
                "evidence": relation.evidence,
                "rule_name": relation.rule_name,
            }
        )

    return {
        "people": list(people_map.values()),
        "relationships": relationships,
    }


def main():
    text = """
    Ông Nguyễn Văn An kết hôn với bà Trần Thị Hạnh.
    Ông Nguyễn Văn An và bà Trần Thị Hạnh có con là Nguyễn Văn Bình và Nguyễn Thị Lan.
    Nguyễn Văn Bình là con của Nguyễn Văn An và Trần Thị Hạnh.
    Nguyễn Văn Bình và Nguyễn Thị Lan là anh chị em ruột.
    Nguyễn Văn Bình kết hôn với Lê Thị Hoa.
    Nguyễn Văn Bình và Lê Thị Hoa có con là Nguyễn Văn Nam.
    """

    extractor = RuleBasedRelationExtractor()
    relations = extractor.extract_relations(text)

    output = build_family_json(relations)

    output_path = Path("data/output_family_rule_based.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Exported to: {output_path}")

    print("\nPeople:")
    for person in output["people"]:
        print(person)

    print("\nRelationships:")
    for relationship in output["relationships"]:
        print(relationship)


if __name__ == "__main__":
    main()