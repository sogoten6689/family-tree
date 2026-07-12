from dataclasses import asdict

from app.domains.extraction.rules.spouse_children import SpouseChildrenRule


def main():
    tests = [
        "Nguyễn Văn Bình kết hôn với Lê Thị Hoa, sinh được Nguyễn Văn Nam và Nguyễn Thị Mai.",
        "Nguyễn Văn Bình kết hôn với Lê Thị Hoa và có con là Nguyễn Văn Nam.",
        "Nguyễn Văn Bình lấy Lê Thị Hoa, sinh được hai người con là Nguyễn Văn Nam và Nguyễn Thị Mai.",
        "Nguyễn Văn Bình cưới Lê Thị Hoa, có các con là Nguyễn Văn Nam, Nguyễn Thị Mai và Nguyễn Văn Long.",
        "Nguyễn Văn Bình là chồng của Lê Thị Hoa, có con là Nguyễn Văn Nam.",
        "Bà Lê Thị Hoa là vợ của ông Nguyễn Văn Bình, sinh được Nguyễn Văn Nam.",
    ]

    rule = SpouseChildrenRule()

    for text in tests:
        print("\nTEXT:", text)
        relations = rule.extract(text)

        for relation in relations:
            print(asdict(relation))


if __name__ == "__main__":
    main()