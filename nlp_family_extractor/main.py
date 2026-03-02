import json
from pathlib import Path

from app.extractor import FamilyExtractor
from app.validate import (
    validate_no_self_relationship,
    validate_no_duplicate_edges,
    validate_parent_age_gap,
)

def main():
    data_path = Path(__file__).parent / "data" / "samples.txt"
    text = data_path.read_text(encoding="utf-8")

    extractor = FamilyExtractor()
    out = extractor.parse(text)

    # validations (optional)
    errors = []
    errors += validate_no_self_relationship(out)
    errors += validate_no_duplicate_edges(out)
    errors += validate_parent_age_gap(out)

    output_path = Path(__file__).parent / "output_family.json"
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Wrote: {output_path}")
    if errors:
        print("\n⚠️ Validation warnings:")
        for e in errors:
            print("-", e)
    else:
        print("✅ No validation warnings.")

if __name__ == "__main__":
    main()