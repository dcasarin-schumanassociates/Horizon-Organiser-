import streamlit as st
import pandas as pd

def render_filters_tab(df, tab):
    with tab:
        st.subheader("📊 Interactive Filters")

        col1, col2, col3 = st.columns(3)
        with col1:
            type_filter = st.multiselect("Type of Action", df["Type of Action"].dropna().unique())
        with col2:
            call_filter = st.multiselect("Call Name", df["Call Name"].dropna().unique())
        with col3:
            trl_filter = st.multiselect("TRL", df["TRL"].dropna().unique())

        max_budget = df["Budget Per Project"].max(skipna=True)
        max_budget_int = int(max_budget) if pd.notna(max_budget) else 100_000_000
        budget_range = st.slider("Budget Per Project (EUR)", 0, max_budget_int, (0, max_budget_int), step=100000)

        filtered = df.copy()
        if type_filter:
            filtered = filtered[filtered["Type of Action"].isin(type_filter)]
        if call_filter:
            filtered = filtered[filtered["Call Name"].isin(call_filter)]
        if trl_filter:
            filtered = filtered[filtered["TRL"].isin(trl_filter)]
        filtered = filtered[
            (filtered["Budget Per Project"].fillna(0) >= budget_range[0]) &
            (filtered["Budget Per Project"].fillna(0) <= budget_range[1])
        ]

        st.markdown(f"📌 Showing {len(filtered)} topics")
        st.dataframe(filtered.drop(columns=["Description"]), use_container_width=True)
