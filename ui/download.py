import streamlit as st
from io import BytesIO

def render_download_button(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    st.download_button(
        label="⬇️ Download Excel File",
        data=output,
        file_name="horizon_topics.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
