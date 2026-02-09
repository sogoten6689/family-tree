from src.models import Person, Relationship
from src.validator import validate_data


def test_self_parent_invalid():
    people = [Person(id="P1", full_name="A", birth_year=1990)]
    rels = [Relationship(from_id="P1", to_id="P1", type="parent_of")]
    errors = validate_data(people, rels)
    assert any("Self relationship" in e for e in errors)
