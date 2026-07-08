from dataclasses import asdict

from app.domains.extraction.extractor import RuleBasedRelationExtractor


def main():
    text = """
    Ông Nguyễn Văn An kết hôn với bà Trần Thị Hạnh.
    Ông Nguyễn Văn An và bà Trần Thị Hạnh có con là Nguyễn Văn Bình và Nguyễn Thị Lan.
    Nguyễn Văn Bình là con của Nguyễn Văn An và Trần Thị Hạnh.
    """

    extractor = RuleBasedRelationExtractor()
    relations = extractor.extract_relations(text)

    for relation in relations:
        print(asdict(relation))


if __name__ == "__main__":
    main()