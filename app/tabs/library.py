from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
import streamlit as st

def render(engine: Any) -> None:
    st.subheader("Document library")
    settings = engine.settings
    upload = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)
    trust = st.selectbox("Trust label", ["unreviewed", "official", "vendor", "internal", "synthetic"])
    if upload and st.button("Ingest PDF", type="primary"):
        if trust == "synthetic" and not settings.allow_synthetic:
            st.error("Synthetic document ingestion is disabled by SECQUERY_ALLOW_SYNTHETIC.")
            return
        content = upload.getvalue()
        if len(content) > min(settings.max_upload_bytes, settings.max_pdf_bytes):
            st.error("This PDF is larger than the configured upload limit.")
        elif not content.startswith(b"%PDF"):
            st.error("The uploaded file does not look like a PDF.")
        else:
            name = Path(upload.name).name
            digest = hashlib.sha256(content).hexdigest()[:12]
            destination_dir = settings.data_dir / ("synthetic" if trust == "synthetic" else "pdfs")
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / f"{digest}_{name}"
            destination.write_bytes(content)
            try:
                doc_id = engine.add_document(destination, trust_level=trust)
                st.success(f"Indexed {name} (document ID: {doc_id}).")
                st.rerun()
            except Exception as exc:
                destination.unlink(missing_ok=True)
                st.error(f"Could not ingest this PDF: {exc}")

    documents = engine.store.list_documents()
    if not documents:
        st.info("No documents indexed yet. Upload a text-based PDF to get started.")
        return
    st.dataframe(
        [
            {
                "Name": item["document_name"],
                "Trust label": item["trust_level"],
                "Pages": item["page_count"],
                "Chunks": item["chunk_count"],
                "Document ID": item["document_id"],
            }
            for item in documents
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.caption("PDFs and the local index are ignored by Git by default; retain permission to process source documents.")