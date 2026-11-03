from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from secquery.config import Settings  
from secquery.pipeline import SecQuery 


@st.cache_resource
def get_engine() -> SecQuery:
    return SecQuery(Settings.load())


def main() -> None:
    st.set_page_config(page_title="SecQuery", page_icon="🛡️", layout="wide")
    st.title(" SecurityQuery")
    st.caption("Evidence-grounded cybersecurity document intelligence")
    st.warning
    (
        "Prototype notice: results are limited to uploaded documents and verified quotes. "
        "This is not a live vulnerability scanner or a substitute for security review. Treat uploads as untrusted."
    )
    try:
        engine = get_engine()
    except Exception as exc:
        st.error(f"SecQuery could not initialize: {exc}")
        st.info("Check .env, install requirements, and start Ollama with the configured model.")
        return

    pages = st.tabs(["Library", "Ask", "Extract", "Compare"])
    with pages[0]:
        from tabs.library import render

        render(engine)
    with pages[1]:
        from tabs.ask import render

        render(engine)
    with pages[2]:
        from tabs.extract import render

        render(engine)
    with pages[3]:
        from tabs.compare import render

        render(engine)


if __name__ == "__main__":
    main()