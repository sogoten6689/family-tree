from dataclasses import asdict

from app.domains.extraction.rules.spouse import SpouseRule


def main():
    tests = [
        "Nguyễn Văn An lấy Trần Thị Hạnh.",
        "Nguyễn Văn An cưới Trần Thị Hạnh.",
        "Nguyễn Văn An là chồng của Trần Thị Hạnh.",
        "Trần Thị Hạnh là vợ của Nguyễn Văn An.",
        "Ông Nguyễn Văn An kết hôn với bà Trần Thị Hạnh.",
        "Bà Trần Thị Hạnh là vợ của ông Nguyễn Văn An.",
    ]

    rule = SpouseRule()

    for text in tests:
        print("\nTEXT:", text)
        relations = rule.extract(text)

        for relation in relations:
            print(asdict(relation))


if __name__ == "__main__":
    main()