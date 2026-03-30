import re


def validate_output(text: str, person) -> bool:
    # kiểm tra năm lạ
    years_in_text = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)
    allowed_years = {str(person.birth_year), str(person.death_year)}

    for y in years_in_text:
        if y not in allowed_years:
            return False

    return True