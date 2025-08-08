import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
from io import BytesIO

import html

def highlight_keyword(text, keyword):
    if not text or not keyword:
        return html.escape(str(text))
    escaped_text = html.escape(str(text))
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped_text)

st.set_page_config(page_title="Horizon Explorer Tool", layout="wide")
st.title("📄 Horizon Explorer Tool")
st.write("Upload a Horizon Europe PDF file and get an Excel sheet with parsed topics.")

# ========== File Upload ==========
uploaded_file = st.file_uploader("Upload a Horizon PDF", type=["pdf"])

# ========== PDF Parsing ==========
def extract_text_from_pdf(file):
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)

# ========== Utility ==========
def normalize_text(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r"\xa0", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()

# ========== Topic Extraction ==========
def extract_topic_blocks(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    fixed_lines = []
    i = 0
    while i < len(lines):
        if re.match(r"^HORIZON-[A-Z0-9\-]+:?$", lines[i]) and i + 1 < len(lines):
            fixed_lines.append(f"{lines[i]} {lines[i + 1]}")
            i += 2
        else:
            fixed_lines.append(lines[i])
            i += 1

    topic_pattern = r"^(HORIZON-[A-Za-z0-9\-]+):\s*(.*)$"
    candidate_topics = []
    for i, line in enumerate(fixed_lines):
        match = re.match(topic_pattern, line)
        if match:
            lookahead_text = "\n".join(fixed_lines[i+1:i+20]).lower()
            if any(key in lookahead_text for key in ["call:", "type of action"]):
                candidate_topics.append({
                    "code": match.group(1),
                    "title": match.group(2).strip(),
                    "start_line": i
                })

    topic_blocks = []
    for idx, topic in enumerate(candidate_topics):
        start = topic["start_line"]
        end = candidate_topics[idx + 1]["start_line"] if idx + 1 < len(candidate_topics) else len(fixed_lines)
        for j in range(start + 1, end):
            if fixed_lines[j].lower().startswith("this destination"):
                end = j
                break
        topic_blocks.append({
            "code": topic["code"],
            "title": topic["title"],
            "full_text": "\n".join(fixed_lines[start:end]).strip()
        })

    return topic_blocks

# ========== Field Extraction ==========
def extract_data_fields(topic):
    text = normalize_text(topic["full_text"])

    def extract_budget(text):
        match = re.search(r"around\s+eur\s+([\d.,]+)", text.lower())
        if match:
            return int(float(match.group(1).replace(",", "")) * 1_000_000)
        match = re.search(r"between\s+eur\s+[\d.,]+\s+and\s+([\d.,]+)", text.lower())
        if match:
            return int(float(match.group(1).replace(",", "")) * 1_000_000)
        return None

    def extract_total_budget(text):
        match = re.search(r"indicative budget.*?eur\s?([\d.,]+)", text.lower())
        return int(float(match.group(1).replace(",", "")) * 1_000_000) if match else None

    def get_section(keyword, stop_keywords):
        lines = text.splitlines()
        collecting = False
        section = []
        for line in lines:
            l = line.lower()
            if not collecting and keyword in l:
                collecting = True
                section.append(line.split(":", 1)[-1].strip())
            elif collecting and any(l.startswith(k) for k in stop_keywords):
                break
            elif collecting:
                section.append(line)
        return "\n".join(section).strip() if section else None

    def extract_type_of_action(text):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "type of action" in line.lower():
                for j in range(i + 1, len(lines)):
                    if lines[j].strip():
                        return lines[j].strip()
        return None

    def extract_topic_title(text):
        lines = text.strip().splitlines()
        title_lines = []
        found = False
        for line in lines:
            if not found:
                match = re.match(r"^(HORIZON-[A-Za-z0-9-]+):\s*(.*)", line)
                if match:
                    found = True
                    title_lines.append(match.group(2).strip())
            else:
                if re.match(r"^\s*Call[:\-]", line, re.IGNORECASE):
                    break
                elif line.strip():
                    title_lines.append(line.strip())
        return " ".join(title_lines) if title_lines else None

    def extract_call_name_topic(text):
        text = normalize_text(text)
        match = re.search(r"(?i)^\s*Call:\s*(.+)$", text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    return {
        "title": extract_topic_title(text),
        "budget_per_project": extract_budget(text),
        "indicative_total_budget": extract_total_budget(text),
        "type_of_action": extract_type_of_action(text),
        "expected_outcome": get_section("expected outcome:", ["scope:", "objective:", "expected impact:", "eligibility:", "budget"]),
        "scope": get_section("scope:", ["objective:", "expected outcome:", "expected impact:", "budget"]),
        "call": extract_call_name_topic(text),
        "trl": (m := re.search(r"TRL\s*(\d+)[^\d]*(\d+)?", text, re.IGNORECASE)) and (
            f"{m.group(1)}-{m.group(2)}" if m.group(2) else m.group(1)
        )
    }

def extract_metadata_blocks(text):
    lines = normalize_text(text).splitlines()

    metadata_map = {}
    current_metadata = {
        "opening_date": None,
        "deadline": None,
        "destination": None
    }

    topic_pattern = re.compile(r"^(HORIZON-[A-Z0-9\-]+):")

    collecting = False
    for i, line in enumerate(lines):
        lower = line.lower()

        if lower.startswith("opening:"):
            date_match = re.search(r"(\d{1,2} \w+ \d{4})", line)
            current_metadata["opening_date"] = date_match.group(1) if date_match else None
            current_metadata["deadline"] = None
            collecting = True

        elif collecting and lower.startswith("deadline"):
            date_match = re.search(r"(\d{1,2} \w+ \d{4})", line)
            current_metadata["deadline"] = date_match.group(1) if date_match else None

        elif collecting and lower.startswith("destination"):
            current_metadata["destination"] = line.split(":", 1)[-1].strip()

        elif collecting:
            match = topic_pattern.match(line)
            if match:
                code = match.group(1)
                metadata_map[code] = current_metadata.copy()

    return metadata_map

# ========== Main Streamlit App ==========
if uploaded_file:
    raw_text = extract_text_from_pdf(uploaded_file)

    topic_blocks = extract_topic_blocks(raw_text)
    metadata_by_code = extract_metadata_blocks(raw_text)

    enriched = [
        {
            **topic,
            **extract_data_fields(topic),
            **metadata_by_code.get(topic["code"], {})
        }
        for topic in topic_blocks
    ]

    df = pd.DataFrame([{
        "Code": t["code"],
        "Title": t["title"],
        "Opening Date": t.get("opening_date"),
        "Deadline": t.get("deadline"),
        "Destination": t.get("destination"),
        "Budget Per Project": t.get("budget_per_project"),
        "Total Budget": t.get("indicative_total_budget"),
        "Number of Projects": int(float(t["indicative_total_budget"]) / float(t["budget_per_project"]))
            if t.get("budget_per_project") and t.get("indicative_total_budget") else None,
        "Type of Action": t.get("type_of_action"),
        "TRL": t.get("trl"),
        "Call Name": t.get("call"),
        "Expected Outcome": t.get("expected_outcome"),
        "Scope": t.get("scope"),
        "Description": t.get("full_text")
    } for t in enriched])


    # ========== 🔧 Clean and Convert Columns ==========

    # Dates — allow abbreviated and full month names
    for col in ["Opening Date", "Deadline"]:
        df[col] = df[col].astype(str).str.strip().replace("None", "")
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')

    # ========== Preview ==========
    st.subheader("📊 Preview")
    st.dataframe(df.drop(columns=["Description"]).head(10), use_container_width=True)

    # ========== Tabs ==========
    tab1, tab2, tab3 = st.tabs(["🔍 Keyword Search", "📊 Dashboard Filters", "📋 Full Data"])
    
    # ========== 🔍 Keyword Search ==========
    with tab1:
        st.subheader("🔍 Search Topics by Keyword")
        keyword = st.text_input("Enter keyword to filter topics:")
    
        if keyword:
            keyword = keyword.lower()
            search_df = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(keyword).any(), axis=1)]
            search_df = search_df.drop_duplicates()
            st.markdown(f"**Results containing keyword: `{keyword}`**")
            st.dataframe(search_df.drop(columns=["Description"]), use_container_width=True)
            st.write(f"🔎 Found {len(search_df)} matching topics.")
    
            # 🔽 Download button for search results
            search_output = BytesIO()
            search_df.to_excel(search_output, index=False)
            search_output.seek(0)
    
            st.download_button(
                label=f"⬇️ Download {len(search_df)} keyword results",
                data=search_output,
                file_name="horizon_search_filtered.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # ========== 📊 Dashboard Filters ==========
    with tab2:
        st.subheader("📊 Interactive Dashboard Filters")
    
        col1, col2, col3 = st.columns(3)
    
        with col1:
            type_filter = st.multiselect("Type of Action", sorted(df["Type of Action"].dropna().unique()))
        with col2:
            call_filter = st.multiselect("Call Name", sorted(df["Call Name"].dropna().unique()))
        with col3:
            trl_filter = st.multiselect("TRL", sorted(df["TRL"].dropna().unique()))
    
        destination_filter = st.multiselect("Destination", sorted(df["Destination"].dropna().unique()))
    
        max_budget = df["Budget Per Project"].dropna().max()
        max_budget = int(max_budget) if pd.notna(max_budget) else 50_000_000
    
        budget_range = st.slider(
            "Budget Per Project (EUR)",
            0,
            max_budget,
            (0, max_budget),
            step=100000
        )
    
        # ✅ Parse dates properly
        df["Opening Date"] = pd.to_datetime(df["Opening Date"], errors='coerce')
        df["Deadline"] = pd.to_datetime(df["Deadline"], errors='coerce')
    
        # ✅ Get min/max for date filters
        min_open = df["Opening Date"].min()
        max_open = df["Opening Date"].max()
        min_deadline = df["Deadline"].min()
        max_deadline = df["Deadline"].max()
    
        col4, col5 = st.columns(2)
    
        with col4:
            opening_range = st.date_input(
                "Opening Date Range",
                value=(min_open, max_open),
                min_value=min_open,
                max_value=max_open
            )
        with col5:
            deadline_range = st.date_input(
                "Deadline Range",
                value=(min_deadline, max_deadline),
                min_value=min_deadline,
                max_value=max_deadline
            )
    
        # ✅ Apply filters
        dashboard_df = df.copy()
        if type_filter:
            dashboard_df = dashboard_df[dashboard_df["Type of Action"].isin(type_filter)]
        if call_filter:
            dashboard_df = dashboard_df[dashboard_df["Call Name"].isin(call_filter)]
        if trl_filter:
            dashboard_df = dashboard_df[dashboard_df["TRL"].isin(trl_filter)]
        if destination_filter:
            dashboard_df = dashboard_df[dashboard_df["Destination"].isin(destination_filter)]
        dashboard_df = dashboard_df[
            (dashboard_df["Budget Per Project"].fillna(0) >= budget_range[0]) &
            (dashboard_df["Budget Per Project"].fillna(0) <= budget_range[1])
        ]
    
        # ✅ Apply date range filters
        dashboard_df = dashboard_df[
            (dashboard_df["Opening Date"] >= pd.to_datetime(opening_range[0])) &
            (dashboard_df["Opening Date"] <= pd.to_datetime(opening_range[1])) &
            (dashboard_df["Deadline"] >= pd.to_datetime(deadline_range[0])) &
            (dashboard_df["Deadline"] <= pd.to_datetime(deadline_range[1]))
        ]
    
        st.markdown(f"📌 Showing {len(dashboard_df)} matching topics")
        st.dataframe(dashboard_df.drop(columns=["Description"]), use_container_width=True)
    
        # 💾 Download button
        dashboard_output = BytesIO()
        dashboard_df.to_excel(dashboard_output, index=False)
        dashboard_output.seek(0)
    
        st.download_button(
            label=f"⬇️ Download {len(dashboard_df)} filtered topics",
            data=dashboard_output,
            file_name="horizon_dashboard_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ========== 📋 Full Data Tab ==========
    with tab3:
        st.subheader("📋 View Full Topics Table")
    
        st.markdown("You can use keyword search and filters below to refine the view.")
    
        # --- Filters ---
        keyword_full = st.text_input("🔍 Search in full data", key="full_data_search")
    
        col1, col2, col3 = st.columns(3)
        with col1:
            full_type_filter = st.multiselect("Type of Action", sorted(df["Type of Action"].dropna().unique()), key="full_type")
        with col2:
            full_call_filter = st.multiselect("Call Name", sorted(df["Call Name"].dropna().unique()), key="full_call")
        with col3:
            full_trl_filter = st.multiselect("TRL", sorted(df["TRL"].dropna().unique()), key="full_trl")
    
        full_destination_filter = st.multiselect("Destination", sorted(df["Destination"].dropna().unique()), key="full_dest")
    
        df["Opening Date"] = pd.to_datetime(df["Opening Date"], errors='coerce')
        df["Deadline"] = pd.to_datetime(df["Deadline"], errors='coerce')
    
        col4, col5 = st.columns(2)
        with col4:
            opening_range = st.date_input(
                "Opening Date Range", 
                value=(df["Opening Date"].min(), df["Opening Date"].max()), 
                min_value=df["Opening Date"].min(), 
                max_value=df["Opening Date"].max(), 
                key="full_open"
            )
        with col5:
            deadline_range = st.date_input(
                "Deadline Range", 
                value=(df["Deadline"].min(), df["Deadline"].max()), 
                min_value=df["Deadline"].min(), 
                max_value=df["Deadline"].max(), 
                key="full_dead"
            )
    
        # Apply filters
        full_df = df.copy()
        if full_type_filter:
            full_df = full_df[full_df["Type of Action"].isin(full_type_filter)]
        if full_call_filter:
            full_df = full_df[full_df["Call Name"].isin(full_call_filter)]
        if full_trl_filter:
            full_df = full_df[full_df["TRL"].isin(full_trl_filter)]
        if full_destination_filter:
            full_df = full_df[full_df["Destination"].isin(full_destination_filter)]
        if opening_range:
            full_df = full_df[(full_df["Opening Date"] >= pd.to_datetime(opening_range[0])) & (full_df["Opening Date"] <= pd.to_datetime(opening_range[1]))]
        if deadline_range:
            full_df = full_df[(full_df["Deadline"] >= pd.to_datetime(deadline_range[0])) & (full_df["Deadline"] <= pd.to_datetime(deadline_range[1]))]
        if keyword_full:
            keyword_lower = keyword_full.lower()
            full_df = full_df[full_df.apply(lambda row: row.astype(str).str.lower().str.contains(keyword_lower).any(), axis=1)]
    
        st.markdown(f"📌 Showing {len(full_df)} matching topics")
    
        # --- Display expandable view with optional keyword highlight ---
        for _, row in full_df.iterrows():
            with st.expander(f"{row['Code']} — {row['Title']}"):
                st.markdown(f"**Type of Action:** {row['Type of Action']}")
                st.markdown(f"**Call Name:** {row['Call Name']}")
                st.markdown(f"**TRL:** {row['TRL']}")
                st.markdown(f"**Opening Date:** {row['Opening Date'].date() if pd.notna(row['Opening Date']) else '—'}")
                st.markdown(f"**Deadline:** {row['Deadline'].date() if pd.notna(row['Deadline']) else '—'}")
                st.markdown(f"**Destination:** {row['Destination']}")
                st.markdown(f"**Budget per Project:** {row['Budget Per Project']}")
                st.markdown(f"**Total Budget:** {row['Total Budget']}")
    
                st.markdown("**Expected Outcome:**", unsafe_allow_html=True)
                st.markdown(highlight_keyword(row['Expected Outcome'], keyword_full), unsafe_allow_html=True)
    
                st.markdown("**Scope:**", unsafe_allow_html=True)
                st.markdown(highlight_keyword(row['Scope'], keyword_full), unsafe_allow_html=True)
    
                st.markdown("**Full Description:**", unsafe_allow_html=True)
                st.markdown(highlight_keyword(row['Description'], keyword_full), unsafe_allow_html=True)
    
        # 🔽 Download button for filtered full data
        full_output = BytesIO()
        full_df.to_excel(full_output, index=False)
        full_output.seek(0)
    
        st.download_button(
            label=f"⬇️ Download {len(full_df)} filtered topics",
            data=full_output,
            file_name="horizon_full_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
