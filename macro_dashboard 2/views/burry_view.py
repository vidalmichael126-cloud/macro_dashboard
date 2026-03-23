"""views/burry_view.py — Burry playbook reference tab (embeds the HTML infographic)."""
import streamlit as st
import streamlit.components.v1 as components
import os


def render():
    st.markdown("### Burry playbook — reference guide")
    st.caption("Methodology, trade structure, iron rules, and sizing. Opens from repo — burry_playbook.html")

    # Attempt to embed the HTML file directly
    playbook_path = os.path.join(os.path.dirname(__file__), "..", "burry_playbook.html")
    if os.path.exists(playbook_path):
        with open(playbook_path, "r") as f:
            html = f.read()
        components.html(html, height=2800, scrolling=True)
    else:
        st.warning("burry_playbook.html not found in repo root. Make sure it's committed.")
        st.markdown("[View raw file on GitHub](burry_playbook.html)")
