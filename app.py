import streamlit as st
import pandas as pd

from exctractors.pdf_reader import extract_text_from_pdf
from exctractors.topic_blocks import extract_topic_blocks
from exctractors.metadata import extract_metadata_blocks
from exctractors.fields import extract_data_fields
from utils.converters import convert_dataframe_types
from ui.filters import render_filters_tab
from ui.display import render_search_tab, render_full_table_tab
from ui.download import render_download_button

st.set_page_config(page_title="Horizon Topic Extractor", layout="wide")
st.title("📄 Horizon Topic Extractor")
uploaded_file = st.file_uploader("Upload a Horizon Europe PDF", type=["pdf"])

if uploaded_file:
    raw_text = extract_text_from_pdf(uploaded_file)
    topic_blocks = extract_topic_blocks(raw_text)
    metadata = extract_metadata_blocks(raw_text)

    enriched = []
    for topic in topic_blocks:
        fields = extract_data_fields(topic)
        metadata_fields = metadata.get(topic["code"], {})
        enriched.append({
            "Code": topic["code"],
            "Title": topic["title"],
            "Opening Date": metadata_fields.get("opening_date"),
            "Deadline": metadata_fields.get("deadline"),
            "Destination": metadata_fields.get("destination"),
            "Budget Per Project": fields.get("budget_per_project"),
            "Total Budget": fields.get("indicative_total_budget"),
            "Number of Projects": (fields["indicative_total_budget"] / fields["budget_per_project"])
                if fields.get("budget_per_project") and fields.get("indicative_total_budget") else None,
            "Type of Action": fields.get("type_of_action"),
            "TRL": fields.get("trl"),
            "Call Name": fields.get("call"),
            "Expected Outcome": fields.get("expected_outcome"),
            "Scope": fields.get("scope"),
            "Description": topic["full_text"]
        })

    df = pd.DataFrame(enriched)
    df = convert_dataframe_types(df)

    tab1, tab2, tab3 = st.tabs(["🔍 Search", "📊 Dashboard", "📋 Full Data"])
    render_search_tab(df, tab1)
    render_filters_tab(df, tab2)
    render_full_table_tab(df, tab3)
    render_download_button(df)
