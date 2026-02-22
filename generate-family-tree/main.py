import json
from app.models import Person
from app.generator import FamilyTreeGenerator
from app.extractor import NaturalLanguageExtractor


def main():
    print("🔹 Generate Family Tree AI 🔹\n")

    natural_input = input("Nhập dữ liệu tự nhiên:\n")

    extractor = NaturalLanguageExtractor()
    structured_data = extractor.extract_person(natural_input)

    person = Person(**structured_data)

    generator = FamilyTreeGenerator()
    result = generator.generate_biography(person)

    print("\n===== GIA PHẢ =====\n")
    print(result)


if __name__ == "__main__":
    main()