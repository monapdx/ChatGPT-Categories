<h1 align="center">📁 ChatGPT-Categories</h1>
<p align="center">
  <b>Organize, label, and browse your ChatGPT conversations like an email inbox.</b><br>
  Categorize by topic, filter, and revisit your ideas with ease.
</p>

<p align="center">
  <a href="https://github.com/monapdx/ChatGPT-Categories/stargazers"><img src="https://img.shields.io/github/stars/monapdx/ChatGPT-Categories?style=flat-square&color=gold" alt="stars"></a>
  <a href="https://github.com/monapdx/ChatGPT-Categories/issues"><img src="https://img.shields.io/github/issues/monapdx/ChatGPT-Categories?style=flat-square" alt="issues"></a>
  <a href="https://github.com/monapdx/ChatGPT-Categories/blob/main/LICENSE"><img src="https://img.shields.io/github/license/monapdx/ChatGPT-Categories?style=flat-square&color=blue" alt="license"></a>
  <img src="https://img.shields.io/badge/built%20with-Python%20%26%20Streamlit-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python & Streamlit">
</p>

---

### ✨ Overview
**ChatGPT-Categories** is a pair of lightweight Streamlit apps designed to help you **sort and revisit your ChatGPT chat history**.  
Think of it like Gmail for your conversations — every chat becomes a message, and you can label it with multiple categories (Coding, Health, Writing, etc.).  

- 🧭 **Chat Categorizer** (`app.py`) — an editor for tagging, filtering, and exporting your chats  
- 🗂️ **Folders Viewer** (`category_viewer.py`) — a read-only browser that lets you navigate by folder, search, and preview messages  

Both apps run **locally**, keep data in **SQLite**, and use a simple, portable `messages.json` format so you can round-trip your progress at any time.

---

### 🖼️ Screenshots

| Categorizer | Folders Viewer |
|--------------|----------------|
| <img src="screenshots/categorizer.png" width="460" alt="Chat Categorizer Screenshot"> | <img src="screenshots/viewer.png" width="460" alt="Chat Folders Viewer Screenshot"> |

*(add your actual screenshot filenames here — e.g. `assets/` or `/screenshots` folders work great)*

---

### ⚙️ Stack
- **Python 3.9+**
- **Streamlit** for the reactive interface  
- **SQLite** for lightweight local persistence  
- **JSON** for portable exports/imports  

---

### 🚀 Quick Start
```bash
# Clone and enter
git clone https://github.com/monapdx/ChatGPT-Categories.git
cd ChatGPT-Categories

# (Optional) Create a virtual environment
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
