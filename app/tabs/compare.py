from __future__ import annotations
from typing import Any
import pandas as pd
import streamlit as st


def render(engine: Any) -> None:
    st.subheader("Compare documents")
    documents = engine.store.list_documents()
    if len(documents) < 2:
        st.info("Index at least two documents to compare them.")
        return
    choices = {f"{item['document_name']} · {item['document_id']}": item["document_id"] for item in documents}
    selected = st.multiselect("Documents", list(choices), max_selections=8)
    fields_text = st.text_input("Fields to compare", "affected versions, fixed version, CVSS score, mitigation")
    if st.button("Compare", type="primary", disabled=len(selected) < 2):
        fields = [field.strip() for field in fields_text.split(",") if field.strip()]
        with st.spinner("Extracting and comparing fields…"):
            try:
                result = engine.compare([choices[name] for name in selected], fields)
            except Exception as exc:
                st.error(f"Comparison failed: {exc}")
                return
        rows = []
        for field_name, data in result.items():
            values = data.get("values", {})
            rows.append({"Field": field_name, **values, "Gaps": ", ".join(data.get("gaps", [])), "Possible conflict": bool(data.get("conflicts"))})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        for field_name, data in result.items():
            if data.get("conflicts"):
                st.warning(f"{field_name}: {data.get('summary', 'Potential mismatch')}")
