import re
from utils.cleaning import clean_section_text

def extract_data_fields(topic):
    text = topic["full_text"]

    def extract_budget(text):
        m = re.search(r"around\s+eur\s+([\d.,]+)", text.lower())
        if m:
            return float(m.group(1).replace(",", "")) * 1_000_000
        m = re.search(r"between\s+eur\s+[\d.,]+\s+and\s+([\d.,]+)", text.lower())
        if m:
            return float(m.group(1).replace(",", "")) * 1_000_000
        return None

    def extract_total_budget(text):
        m = re.search(r"indicative budget.*?eur\s?([\d.,]+)", text.lower())
        return float(m.group(1).replace(",", "")) * 1_000_000 if m else None

    def extract_trl(text):
        m = re.search(r"TRL\s*(\d+)[^\d]*(\d+)?", text, re.IGNORECASE)
        return f"{m.group(1)}-{m.group(2)}" if m and m.group(2) else m.group(1) if m else None

    def extract_type(text, keyword):
        for line in text.splitlines():
            if keyword.lower() in line.lower():
                return line.split(":", 1)[-1].strip()
        return None

    def get_section(keyword, stops):
        lines = text.splitlines()
        collecting = False
        section = []
        for line in lines:
            if not collecting and keyword.lower() in line.lower():
                collecting = True
                section.append(line.split(":", 1)[-1].strip())
            elif collecting and any(line.lower().startswith(k) for k in stops):
                break
            elif collecting:
                section.append(line)
        return clean_section_text("\n".join(section)) if section else None

    return {
        "budget_per_project": extract_budget(text),
        "indicative_total_budget": extract_total_budget(text),
        "type_of_action": extract_type(text, "type of action"),
        "expected_outcome": get_section("expected outcome:", ["scope", "objective"]),
        "scope": get_section("scope:", ["objective", "expected outcome"]),
        "call": extract_type(text, "call"),
        "trl": extract_trl(text)
    }

