from dataclasses import asdict

from app.domains.extraction.rules.sibling import SiblingRule


def main():
    tests = [
        "Nguyễn Văn Bình và Nguyễn Thị Lan là anh em.",
        "Nguyễn Văn Bình và Nguyễn Thị Lan là anh chị em.",
        "Nguyễn Văn Bình và Nguyễn Thị Lan là anh chị em ruột.",
        "Nguyễn Văn Bình là anh trai của Nguyễn Thị Lan.",
        "Nguyễn Thị Lan là em gái của Nguyễn Văn Bình.",
        "Ông Nguyễn Văn Bình là anh trai của bà Nguyễn Thị Lan.",
    ]

    rule = SiblingRule()

    for text in tests:
        print("\nTEXT:", text)
        relations = rule.extract(text)

        for relation in relations:
            print(asdict(relation))


if __name__ == "__main__":
    main()