from __future__ import annotations
from typing import Any
import streamlit as st

def render(engine: Any) -> None:
    st.subheader("Extract a vulnerability or advisory record")
    documents = engine.store.list_documents()
    if not documents:
        st.info("Upload a PDF in the Library tab first.")
        return
    choices = {f"{item['document_name']} · {item['document_id']}": item["document_id"] for item in documents}
    selected = st.selectbox("Document", list(choices))
    default_fields = "CVE ID, affected versions, fixed version, CVSS score, mitigation, publication date"
    fields_text = st.text_input("Fields to extract (comma-separated)", default_fields)
    if st.button("Extract fields", type="primary"):
        fields = [field.strip() for field in fields_text.split(",") if field.strip()]
        with st.spinner("Extracting fields and verifying supporting quotes…"):
            try:
                results = engine.extract_document(choices[selected], fields)
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
                return
        for field_name, item in results.items():
            label = "Verified quote" if item.verified else "Not verified / not stated"
            with st.container(border=True):
                st.markdown(f"**{field_name}** — `{label}`")
                st.write(item.value)
                if item.quote:
                    st.caption(f"{item.document_name}, page {item.page_number}")
                    st.code(item.quote)
