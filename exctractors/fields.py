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
                parts = line.split(":", 1)
                return parts[1].strip() if len(parts) > 1 else line.strip()
        return None

    def get_section(keyword, stop_keywords):
        lines = text.splitlines()
        collecting = False
        section = []
        keyword = keyword.lower()
        stop_keywords = [k.lower() for k in stop_keywords]

        for line in lines:
            clean_line = line.strip()
            lower_line = clean_line.lower()

            if not collecting and keyword in lower_line:
                collecting = True
                # Handle either "keyword: value" or "keyword" on its own line
                section.append(clean_line.split(":", 1)[-1].strip() if ":" in clean_line else clean_line)
                continue

            if collecting:
                if any(stop_kw in lower_line for stop_kw in stop_keywords):
                    break
                if clean_line:  # ignore empty lines
                    section.append(clean_line)

        return clean_section_text("\n".join(section)) if section else None

    return {
        "budget_per_project": extract_budget(text),
        "indicative_total_budget": extract_total_budget(text),
        "type_of_action": extract_type(text, "type of action"),
        "expected_outcome": get_section("expected outcome", ["scope", "objective", "expected impact", "destination", "eligibility"]),
        "scope": get_section("scope", ["objective", "expected outcome", "expected impact", "destination"]),
        "call": extract_type(text, "call"),
        "trl": extract_trl(text)
    }

