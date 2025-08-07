import re

def extract_metadata_blocks(text):
    lines = text.splitlines()
    metadata_map = {}
    current_metadata = {"opening_date": None, "deadline": None, "destination": None}
    topic_pattern = re.compile(r"^(HORIZON-[A-Z0-9\-]+):")
    collecting = False

    for line in lines:
        lower = line.lower()
        if lower.startswith("opening:"):
            match = re.search(r"(\d{1,2} \w+ \d{4})", line)
            current_metadata["opening_date"] = match.group(1) if match else None
            current_metadata["deadline"] = None
            collecting = True
        elif collecting and lower.startswith("deadline"):
            match = re.search(r"(\d{1,2} \w+ \d{4})", line)
            current_metadata["deadline"] = match.group(1) if match else None
        elif collecting and lower.startswith("destination"):
            current_metadata["destination"] = line.split(":", 1)[-1].strip()
        elif collecting:
            match = topic_pattern.match(line)
            if match:
                code = match.group(1)
                metadata_map[code] = current_metadata.copy()

    return metadata_map
