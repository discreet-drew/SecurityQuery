from __future__ import annotations
from typing import Any
import streamlit as st


def render(engine: Any) -> None:
    st.subheader("Ask the security documents")
    documents = engine.store.list_documents()
    options = {f"{item['document_name']} · {item['document_id']}": item["document_id"] for item in documents}
    selected = st.multiselect("Limit search to these documents (leave blank for all)", list(options))
    question = st.text_area(
        "Question",
        placeholder="Example: What mitigation does the advisory document state for CVE-2024-12345?",
        height=100,
    )
    if st.button("Ask", type="primary", disabled=not question.strip()):
        with st.spinner("Retrieving evidence and checking citations…"):
            try:
                result = engine.ask(question, {options[name] for name in selected} if selected else None)
            except Exception as exc:
                st.error(f"Question failed: {exc}")
                return
        if result.abstained:
            st.warning(result.answer)
            if result.reason:
                st.caption(f"Reason: {result.reason}")
        else:
            st.markdown(result.answer)
        if result.hits:
            with st.expander("Retrieved evidence", expanded=True):
                for hit in result.hits:
                    st.markdown(
                        f"**{hit.chunk.document_name} · page {hit.chunk.page_number}** "
                        f"(score {hit.score:.4f}; {hit.source})"
                    )
                    st.code(hit.chunk.text[:3000])
