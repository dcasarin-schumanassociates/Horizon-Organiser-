import streamlit as st

def render_search_tab(df, tab):
    with tab:
        st.subheader("🔎 Keyword Search")
        keyword = st.text_input("Enter keyword:")
        if keyword:
            keyword = keyword.lower()
            filtered_df = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(keyword).any(), axis=1)]
            st.dataframe(filtered_df.drop(columns=["Description"]), use_container_width=True)
            st.markdown(f"🔍 Found {len(filtered_df)} matching topics.")

def render_full_table_tab(df, tab):
    with tab:
        st.subheader("📋 All Topics")
        for _, row in df.iterrows():
            with st.expander(f"{row['Code']} – {row['Title']}"):
                st.markdown(f"**Type of Action:** {row['Type of Action']}")
                st.markdown(f"**Call Name:** {row['Call Name']}")
                st.markdown(f"**TRL:** {row['TRL']}")
                st.markdown(f"**Expected Outcome:**\n\n{row['Expected Outcome']}")
                st.markdown(f"**Scope:**\n\n{row['Scope']}")
                st.markdown(f"**Full Description:**\n\n{row['Description']}")
