from dataclasses import asdict

from app.domains.extraction.rules.grandparent import GrandparentRule


def main():
    tests = [
        "Nguyễn Văn An là ông nội của Nguyễn Văn Nam.",
        "Trần Thị Hạnh là bà nội của Nguyễn Văn Nam.",
        "Nguyễn Văn Nam là cháu nội của Nguyễn Văn An.",
        "Nguyễn Văn Nam là cháu của Trần Thị Hạnh.",
        "Ông Nguyễn Văn An là ông ngoại của Nguyễn Thị Lan.",
        "Bà Trần Thị Hạnh là bà ngoại của Nguyễn Thị Lan.",
    ]

    rule = GrandparentRule()

    for text in tests:
        print("\nTEXT:", text)
        relations = rule.extract(text)

        for relation in relations:
            print(asdict(relation))


if __name__ == "__main__":
    main()