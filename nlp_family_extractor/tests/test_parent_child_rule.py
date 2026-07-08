from dataclasses import asdict

from app.domains.extraction.rules.parent_child import ParentChildRule


def main():
    tests = [
        "Nguyễn Văn An là cha của Nguyễn Văn Bình.",
        "Trần Thị Hạnh là mẹ của Nguyễn Văn Bình.",
        "Nguyễn Văn Bình là con của Nguyễn Văn An và Trần Thị Hạnh.",
        "Nguyễn Văn An và Trần Thị Hạnh có con là Nguyễn Văn Bình và Nguyễn Thị Lan.",
        "Ông Nguyễn Văn An và bà Trần Thị Hạnh có con là Nguyễn Văn Bình và Nguyễn Thị Lan.",
        "Ông Nguyễn Văn An có con là Nguyễn Văn Bình.",
    ]

    rule = ParentChildRule()

    for text in tests:
        print("\nTEXT:", text)
        relations = rule.extract(text)

        for relation in relations:
            print(asdict(relation))


if __name__ == "__main__":
    main()