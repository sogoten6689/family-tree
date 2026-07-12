from dataclasses import asdict

from app.domains.extraction.extractor import RuleBasedRelationExtractor


def main():
    text = """
Ông Nguyễn Văn An kết hôn với bà Trần Thị Hạnh.
Ông Nguyễn Văn An và bà Trần Thị Hạnh có con là Nguyễn Văn Bình và Nguyễn Thị Lan.
Nguyễn Văn Bình và Nguyễn Thị Lan là anh chị em ruột.
Nguyễn Văn An là ông nội của Nguyễn Văn Nam.
Trần Thị Hạnh là bà nội của Nguyễn Văn Nam.
Nguyễn Văn Nam là cháu nội của Nguyễn Văn An.
"""

    extractor = RuleBasedRelationExtractor()
    relations = extractor.extract_relations(text)

    for relation in relations:
        print(asdict(relation))


if __name__ == "__main__":
    main()