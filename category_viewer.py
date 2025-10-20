
import streamlit as st
import json
from datetime import datetime
from typing import List, Dict, Any

st.set_page_config(page_title="Chat Folders Viewer", layout="wide")
st.title("🗂️ Chat Folders Viewer")
st.caption("Open your *categorized_chats.json* export and browse by category like folders.")

# ---- Utilities ----

def parse_datetime(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    # Epoch fallback
    try:
        return datetime.fromtimestamp(int(float(s)))
    except Exception:
        return None

def load_export(file_bytes: bytes) -> Dict[str, Any]:
    try:
        data = json.loads(file_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        data = json.loads(file_bytes.decode("utf-16"))
    # Expect structure: {"chats": [...], "categories": [...]}
    chats = data.get("chats", [])
    # Normalize categories field
    for c in chats:
        cats = c.get("categories") or []
        if isinstance(cats, str):
            cats = [x.strip() for x in cats.split(",") if x.strip()]
        c["categories"] = cats
    # Build category counts
    cat_counts = {}
    for c in chats:
        for cat in c.get("categories", []):
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    all_cats = sorted(cat_counts.keys(), key=str.lower)
    data["_cat_counts"] = cat_counts
    data["_all_cats"] = all_cats
    return data

def filter_chats(chats, selected_cats: List[str], mode: str, query: str):
    def matches(c):
        cats = set(c.get("categories") or [])
        text = (c.get("title","") + " " + c.get("content","")).lower()
        ok_query = (query.strip().lower() in text) if query.strip() else True
        if not selected_cats:
            return ok_query
        sc = set(selected_cats)
        if mode == "AND":
            return ok_query and sc.issubset(cats)
        else:
            return ok_query and bool(sc & cats)
    return [c for c in chats if matches(c)]

# ---- Sidebar: file + folders ----

with st.sidebar:
    file = st.file_uploader("Open your categorized JSON", type=["json"], accept_multiple_files=False)
    mode = st.radio("Category filter mode", ["AND","OR"], help="AND: chat must have all selected categories. OR: chat may have any of them.")
    st.divider()
    st.caption("Tip: Click a folder name to filter by that single category.")

if "data" not in st.session_state:
    st.session_state.data = None
if file is not None:
    st.session_state.data = load_export(file.getvalue())

data = st.session_state.data

if not data:
    st.info("Upload your **categorized_chats.json** export to begin.")
    st.stop()

chats = data.get("chats", [])
cat_counts = data.get("_cat_counts", {})
all_cats = data.get("_all_cats", [])

left, right = st.columns([0.26, 0.74])

with left:
    st.subheader("Folders")
    # Render "All" at top
    if st.button(f"All ({len(chats)})"):
        st.session_state["selected_cats"] = []
    # Folder list
    for cat in all_cats:
        if st.button(f"{cat} ({cat_counts.get(cat,0)})", key=f"catbtn_{cat}"):
            st.session_state["selected_cats"] = [cat]

    st.divider()
    # Multi-select filter
    selected_cats = st.session_state.get("selected_cats", [])
    selected_cats = st.multiselect("Filter by multiple folders", options=all_cats, default=selected_cats)
    st.session_state["selected_cats"] = selected_cats

    query = st.text_input("Search title/content")
    sort = st.selectbox("Sort", ["Newest", "Oldest", "Title A→Z"])
    page_size = st.selectbox("Page size", [10, 20, 50, 100], index=1)

with right:
    # Apply filters
    display = filter_chats(chats, selected_cats, mode, query)

    # Sorting
    if sort == "Newest":
        display.sort(key=lambda c: parse_datetime(c.get("created_at")) or datetime.min, reverse=True)
    elif sort == "Oldest":
        display.sort(key=lambda c: parse_datetime(c.get("created_at")) or datetime.min)
    else:
        display.sort(key=lambda c: (c.get("title") or "").lower())

    # Pagination
    total = len(display)
    if "page" not in st.session_state: st.session_state.page = 0
    max_page = max(0, (total - 1)//page_size)
    n1, n2, n3 = st.columns([0.15, 0.7, 0.15])
    with n1:
        if st.button("⟵ Prev", disabled=(st.session_state.page<=0)):
            st.session_state.page = max(0, st.session_state.page-1)
    with n2:
        st.write(f"Page {st.session_state.page+1} / {max_page+1} • {total} chats")
    with n3:
        if st.button("Next ⟶", disabled=(st.session_state.page>=max_page)):
            st.session_state.page = min(max_page, st.session_state.page+1)

    start = st.session_state.page*page_size
    end = start+page_size
    subset = display[start:end]

    # Header
    st.markdown("### Conversations")
    h = st.columns([0.5, 0.2, 0.3])
    h[0].markdown("**Title**")
    h[1].markdown("**Date**")
    h[2].markdown("**Folders**")

    # Rows
    for c in subset:
        cols = st.columns([0.5, 0.2, 0.3])
        title = c.get("title") or "(untitled)"
        cols[0].markdown(f"**{title}**")
        cols[1].caption(c.get("created_at") or "—")
        cats = c.get("categories") or []
        if cats:
            cols[2].markdown(", ".join([f"`{x}`" for x in cats]))
        else:
            cols[2].caption("—")

        with st.expander("Open conversation"):
            st.text_area("Content", c.get("content",""), height=220, label_visibility="collapsed")

    st.markdown("---")
    # Download filtered subset
    filtered_json = json.dumps({"chats": display}, ensure_ascii=False, indent=2)
    st.download_button("Download filtered result (JSON)", data=filtered_json, file_name="filtered_chats.json", mime="application/json")
