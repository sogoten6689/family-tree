from dataclasses import asdict

from app.domains.extraction.rules.parent_child import ParentChildRule


def main():
    tests = [
         "Nguyễn Văn An là cha của Nguyễn Văn Bình.",
    "Trần Thị Hạnh là mẹ của Nguyễn Văn Bình.",
    "Nguyễn Văn Bình là con của Nguyễn Văn An và Trần Thị Hạnh.",
    "Nguyễn Văn Bình là con trai của Nguyễn Văn An.",
    "Nguyễn Thị Lan là con gái của Trần Thị Hạnh.",
    "Nguyễn Văn Bình là trưởng nam của Nguyễn Văn An.",
    "Nguyễn Thị Lan là con út của Trần Thị Hạnh.",
    "Nguyễn Văn An và Trần Thị Hạnh có con là Nguyễn Văn Bình và Nguyễn Thị Lan.",
    "Nguyễn Văn An và Trần Thị Hạnh có các con là Nguyễn Văn Bình, Nguyễn Thị Lan và Nguyễn Văn Nam.",
    "Nguyễn Văn An và Trần Thị Hạnh có hai người con là Nguyễn Văn Bình và Nguyễn Thị Lan.",
    "Nguyễn Văn An và Trần Thị Hạnh sinh được Nguyễn Văn Bình và Nguyễn Thị Lan.",
    "Nguyễn Văn An và Trần Thị Hạnh sinh được hai người con là Nguyễn Văn Bình và Nguyễn Thị Lan.",
    "Nguyễn Văn An sinh ra Nguyễn Văn Bình.",
    ]

    rule = ParentChildRule()

    for text in tests:
        print("\nTEXT:", text)
        relations = rule.extract(text)

        for relation in relations:
            print(asdict(relation))


if __name__ == "__main__":
    main()