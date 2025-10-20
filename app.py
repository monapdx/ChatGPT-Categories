
import streamlit as st
import sqlite3
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = "chat_categorizer.db"

# ---------- DB LAYER ----------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT,
            model TEXT,
            content TEXT
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chat_categories (
            chat_id TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (chat_id, category_id),
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()

def upsert_chat(chat: Dict[str, Any]):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO chats (id, title, created_at, model, content)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
           title=excluded.title,
           created_at=excluded.created_at,
           model=excluded.model,
           content=excluded.content
        """,
        (chat["id"], chat.get("title"), chat.get("created_at"), chat.get("model"), chat.get("content")),
    )
    conn.commit()
    conn.close()

def list_chats(search: str = "", category_ids: Optional[List[int]] = None, sort: str = "newest"):
    conn = get_conn()
    q = """
        SELECT c.id, c.title, c.created_at, c.model,
               COALESCE(GROUP_CONCAT(cat.name, ', '), '') as categories
        FROM chats c
        LEFT JOIN chat_categories cc ON c.id = cc.chat_id
        LEFT JOIN categories cat ON cc.category_id = cat.id
    """
    params = []
    where = []
    if search:
        where.append("(LOWER(c.title) LIKE ? OR LOWER(c.content) LIKE ?)")
        s = f"%{search.lower()}%"
        params.extend([s, s])
    if category_ids:
        placeholders = ",".join("?" * len(category_ids))
        q += f"""
            JOIN (
                SELECT chat_id
                FROM chat_categories
                WHERE category_id IN ({placeholders})
                GROUP BY chat_id
                HAVING COUNT(DISTINCT category_id) = {len(category_ids)}
            ) AS must ON must.chat_id = c.id
        """
        params.extend(category_ids)

    if where:
        q += " WHERE " + " AND ".join(where)

    q += " GROUP BY c.id "

    if sort == "newest":
        q += " ORDER BY datetime(c.created_at) DESC NULLS LAST, c.title COLLATE NOCASE ASC"
    elif sort == "oldest":
        q += " ORDER BY datetime(c.created_at) ASC NULLS LAST, c.title COLLATE NOCASE ASC"
    else:
        q += " ORDER BY c.title COLLATE NOCASE ASC"

    rows = conn.execute(q, params).fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append(
            {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "model": row[3],
                "categories": row[4],
            }
        )
    return result

def get_chat(chat_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, title, created_at, model, content FROM chats WHERE id = ?", (chat_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "title": row[1], "created_at": row[2], "model": row[3], "content": row[4]}

def ensure_category(name: str) -> int:
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,))
    conn.commit()
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
    conn.close()
    return int(row[0])

def list_categories() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, (SELECT COUNT(*) FROM chat_categories WHERE category_id = categories.id) as n FROM categories ORDER BY name COLLATE NOCASE ASC"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "count": r[2]} for r in rows]

def assign_categories(chat_ids: List[str], category_names: List[str]):
    if not chat_ids or not category_names:
        return
    conn = get_conn()
    names = [n.strip() for n in category_names if n and n.strip()]
    for name in names:
        conn.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,))
    conn.commit()
    if not names:
        conn.close()
        return
    qmarks = ",".join(["?"] * len(names))
    cat_rows = conn.execute(f"SELECT id FROM categories WHERE name IN ({qmarks})", names).fetchall()
    cat_ids = [r[0] for r in cat_rows]
    for chat_id in chat_ids:
        for cid in cat_ids:
            conn.execute(
                "INSERT OR IGNORE INTO chat_categories(chat_id, category_id) VALUES (?, ?)",
                (chat_id, cid),
            )
    conn.commit()
    conn.close()

def remove_categories(chat_ids: List[str], category_names: List[str]):
    if not chat_ids or not category_names:
        return
    conn = get_conn()
    qmarks = ",".join(["?"] * len(category_names))
    cat_rows = conn.execute(f"SELECT id FROM categories WHERE name IN ({qmarks})", category_names).fetchall()
    cat_ids = [r[0] for r in cat_rows]
    for chat_id in chat_ids:
        for cid in cat_ids:
            conn.execute(
                "DELETE FROM chat_categories WHERE chat_id = ? AND category_id = ?",
                (chat_id, cid),
            )
    conn.commit()
    conn.close()

def export_categorized() -> Dict[str, Any]:
    conn = get_conn()
    chats = conn.execute("SELECT id, title, created_at, model, content FROM chats").fetchall()
    cats = conn.execute("SELECT id, name FROM categories").fetchall()
    cc = conn.execute("SELECT chat_id, category_id FROM chat_categories").fetchall()
    conn.close()
    cat_lookup = {cid: name for cid, name in cats}
    chat_map = {}
    for row in chats:
        chat_map[row[0]] = {
            "id": row[0],
            "title": row[1],
            "created_at": row[2],
            "model": row[3],
            "content": row[4],
            "categories": [],
        }
    for chat_id, cid in cc:
        if chat_id in chat_map and cid in cat_lookup:
            chat_map[chat_id]["categories"].append(cat_lookup[cid])
    return {
        "schema_version": 1,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "categories": [name for _, name in cats],
        "chats": list(chat_map.values()),
    }

# ---------- JSON PARSING & MERGE ----------

def hash_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]

def _coerce_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt).isoformat()
        except Exception:
            pass
    try:
        iv = int(float(value))
        return datetime.utcfromtimestamp(iv).isoformat()
    except Exception:
        pass
    return str(value)

def normalize_chats(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, dict):
        raw = obj.get("chats") if isinstance(obj.get("chats"), list) else obj.get("items") or [obj]
    elif isinstance(obj, list):
        raw = obj
    else:
        return []
    normalized = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        cid = (
            str(item.get("id"))
            or str(item.get("conversation_id"))
            or str(item.get("uuid"))
            or ""
        )
        title = item.get("title") or item.get("name") or item.get("summary") or f"Chat #{i+1}"
        created = item.get("created_at") or item.get("create_time") or item.get("timestamp") or item.get("date")
        model = item.get("model") or item.get("model_slug") or item.get("engine") or ""
        content = item.get("content")
        if not content:
            msgs = item.get("messages") or item.get("turns") or item.get("conversation")
            if isinstance(msgs, list):
                parts = []
                for m in msgs:
                    if isinstance(m, dict):
                        role = m.get("role") or m.get("sender") or ""
                        text = m.get("content") or m.get("text") or ""
                        parts.append(f"[{role}] {text}".strip())
                    else:
                        parts.append(str(m))
                content = "\n\n".join(parts)
            else:
                content = json.dumps(item, ensure_ascii=False)
        if not cid:
            cid = hash_id(f"{title}|{created}|{content[:80]}")
        categories = item.get("categories") or []
        if isinstance(categories, str):
            categories = [x.strip() for x in categories.split(",") if x.strip()]
        normalized.append(
            {
                "id": cid,
                "title": str(title),
                "created_at": _coerce_datetime(created),
                "model": str(model),
                "content": str(content),
                "categories": categories,
            }
        )
    return normalized

def import_json_file(json_bytes: bytes, merge_mode: str = "additive") -> int:
    try:
        obj = json.loads(json_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        obj = json.loads(json_bytes.decode("utf-16"))
    chats = normalize_chats(obj)
    for c in chats:
        upsert_chat(c)
        cats = c.get("categories") or []
        if cats:
            assign_categories([c["id"]], cats)
    return len(chats)

# ---------- UI ----------

def _tag_badge(name: str):
    st.markdown(
        f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;border:1px solid #ddd;font-size:12px;margin-right:6px'>{name}</span>",
        unsafe_allow_html=True,
    )

def _chat_row(chat: Dict[str, Any], key_prefix: str):
    cols = st.columns([0.06, 0.44, 0.22, 0.28])
    with cols[0]:
        checked = st.checkbox("", key=f"{key_prefix}_{chat['id']}")
    with cols[1]:
        title = chat["title"] or "(untitled)"
        st.markdown(f"**{title}**")
        if chat.get("created_at"):
            st.caption(chat["created_at"])
    with cols[2]:
        cats = [c.strip() for c in (chat.get("categories") or "").split(",") if c.strip()]
        if cats:
            for c in cats:
                _tag_badge(c)
        else:
            st.caption("—")
    with cols[3]:
        with st.expander("Preview"):
            details = get_chat(chat["id"])
            st.text_area("Content", details.get("content") if details else "", height=160, label_visibility="collapsed")
    return checked

def main():
    st.set_page_config(page_title="Chat Categorizer", layout="wide")
    st.title("📁 Chat Categorizer")
    st.caption("Import raw or previously categorized JSON, keep working, and export back — additive merge, local-only.")

    init_db()

    with st.sidebar:
        st.subheader("Import / Export")
        file = st.file_uploader("Import chat JSON (raw or messages.json)", type=["json"], accept_multiple_files=False)
        if file is not None:
            n = import_json_file(file.getvalue(), merge_mode="additive")
            st.success(f"Merged {n} chats from JSON. Categories present in the file were added (no removals).")

        st.divider()
        if st.button("Export as messages.json"):
            data = export_categorized()
            st.download_button(
                "Download messages.json",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name="messages.json",
                mime="application/json",
            )

        st.caption("DB: chat_categorizer.db • Export includes schema_version + exported_at")

    c1, c2, c3, c4 = st.columns([0.35, 0.25, 0.2, 0.2])
    with c1:
        search = st.text_input("Search title/content")
    with c2:
        all_cats = list_categories()
        cat_name_to_id = {c["name"]: c["id"] for c in all_cats}
        cat_filter_names = st.multiselect("Filter by category (must match all)", options=[c["name"] for c in all_cats])
        cat_filter_ids = [cat_name_to_id[name] for name in cat_filter_names] if cat_filter_names else None
    with c3:
        sort = st.selectbox("Sort", ["newest", "oldest", "title A→Z"])
    with c4:
        page_size = st.selectbox("Page size", [10, 20, 50, 100], index=1)

    chats = list_chats(search=search, category_ids=cat_filter_ids, sort={"newest":"newest","oldest":"oldest","title A→Z":"title"}[sort])

    total = len(chats)
    if "page" not in st.session_state:
        st.session_state.page = 0
    max_page = max(0, (total - 1)//page_size)
    nav1, nav2, nav3 = st.columns([0.15, 0.7, 0.15])
    with nav1:
        if st.button("⟵ Prev", disabled=(st.session_state.page <= 0)):
            st.session_state.page = max(0, st.session_state.page - 1)
    with nav2:
        st.write(f"Page {st.session_state.page + 1} / {max_page + 1} • {total} chats")
    with nav3:
        if st.button("Next ⟶", disabled=(st.session_state.page >= max_page)):
            st.session_state.page = min(max_page, st.session_state.page + 1)

    start = st.session_state.page * page_size
    end = start + page_size
    visible = chats[start:end]

    st.markdown("#### Inbox")
    header = st.columns([0.06, 0.44, 0.22, 0.28])
    header[0].markdown("**✓**")
    header[1].markdown("**Title / Date**")
    header[2].markdown("**Categories**")
    header[3].markdown("**Preview**")

    selected_ids = []
    for idx, chat in enumerate(visible):
        if _chat_row(chat, key_prefix=f"row{start+idx}"):
            selected_ids.append(chat["id"])

    st.markdown("---")

    st.markdown("### Categorize Selected")
    cat_left, cat_right = st.columns([0.6, 0.4])
    with cat_left:
        new_cat = st.text_input("Create new category (or reuse existing)", placeholder="e.g., Writing, Health, Coding")
        assign_existing = st.multiselect("Or assign existing categories", options=[c["name"] for c in all_cats])
        if st.button("Assign to selected"):
            names = []
            if new_cat.strip():
                names.append(new_cat.strip())
            names += assign_existing
            assign_categories(selected_ids, names)
            st.success(f"Assigned {', '.join(names)} to {len(selected_ids)} chat(s).")
    with cat_right:
        remove_existing = st.multiselect("Remove categories from selected", options=[c["name"] for c in all_cats])
        if st.button("Remove from selected"):
            remove_categories(selected_ids, remove_existing)
            st.warning(f"Removed {', '.join(remove_existing)} from {len(selected_ids)} chat(s).")

    st.markdown("### Category Summary")
    cols = st.columns(4)
    for i, cat in enumerate(list_categories()):
        with cols[i % 4]:
            st.metric(cat["name"], f"{cat['count']} chats")

if __name__ == "__main__":
    main()
