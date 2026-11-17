"""
Step 3: உழவனின் உரிமைக்கரம் - multilingual farmer scheme assistant.
- Left sidebar : language, sector/category browser, crop / farmer / benefit / apply-mode /
                 district / season / land-holding filters, scheme picker
- Centre       : matching schemes table, selected scheme details, RAG chat
- Right column : featured subsidy cards (poultry, goat, cattle, fish, oilseeds) with images

Run:  streamlit run 3_app.py
Needs: chroma_db/ (2_build_index.py) and data/schemes_meta.json (5_classify_schemes.py)
Images: put poultry.jpg, goat.jpg, cattle.jpg, fish.jpg, oilseeds.jpg in the assets/ folder
        (.png/.jpeg/.webp also work). Without them, an icon tile is shown.
"""
import json
import os
from pathlib import Path

import streamlit as st

APP_NAME = "உழவனின் உரிமைக்கரம்"
st.set_page_config(page_title=APP_NAME, page_icon="🌾", layout="wide")
st.title(f"🌾 {APP_NAME}")

with st.spinner("Loading libraries (first start can take ~30 seconds)..."):
    import chromadb
    from chromadb.utils import embedding_functions
    from dotenv import load_dotenv
    from openai import OpenAI
    from i18n import Translator

load_dotenv()
DB_DIR, COLLECTION = "chroma_db", "tn_schemes"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TOP_K = 8
META_FILE = Path("data/schemes_meta.json")
RAW_DIR = Path("data/raw")
ASSETS = Path("assets")

# Display name -> language name used for translation
LANGUAGES = {"English": "English", "தமிழ் (Tamil)": "Tamil", "हिन्दी (Hindi)": "Hindi",
             "తెలుగు (Telugu)": "Telugu", "മലയാളം (Malayalam)": "Malayalam", "ಕನ್ನಡ (Kannada)": "Kannada",
             "বাংলা (Bengali)": "Bengali", "मराठी (Marathi)": "Marathi", "اردو (Urdu)": "Urdu"}
SECTORS = ["Crop Farming", "Oilseeds", "Horticulture", "Cattle & Dairy", "Poultry",
           "Goat & Sheep", "Fisheries", "Other Allied"]
CROPS = ["Paddy", "Millets", "Pulses", "Groundnut", "Sesame", "Sunflower", "Coconut", "Oil Palm",
         "Sugarcane", "Cotton", "Maize", "Banana", "Vegetables", "Fruits", "Flowers", "Spices",
         "Turmeric", "Tea & Coffee"]
FARMER_GROUPS = ["Small farmers", "Marginal farmers", "SC/ST", "Women", "FPOs & Groups",
                 "Tenant farmers", "Youth & Graduates", "Fishermen"]
BENEFIT_TYPES = ["Cash / Direct transfer", "Subsidy on purchase", "Free inputs / In-kind",
                 "Loan / Interest subsidy", "Insurance", "Training / Demonstration", "Infrastructure grant"]
TYPES = ["Schemes & subsidies", "Training programmes"]
TRAINING_TOPICS = ["Crop cultivation", "Organic & natural farming", "Dairy & cattle management", "Poultry rearing",
                   "Goat & sheep rearing", "Fish farming", "Farm machinery", "Irrigation & water",
                   "Plant protection", "Value addition & marketing", "Entrepreneurship & FPO",
                   "Digital & drone technology", "Other"]
APPLY_MODES = ["Online portal", "Agriculture / Block office", "Veterinary / Fisheries office",
               "Bank / Cooperative"]
DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul",
    "Erode", "Kallakurichi", "Kancheepuram", "Kanniyakumari", "Karur", "Krishnagiri", "Madurai",
    "Mayiladuthurai", "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai",
    "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "Theni",
    "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur", "Tiruppur", "Tiruvallur",
    "Tiruvannamalai", "Tiruvarur", "Vellore", "Viluppuram", "Virudhunagar",
]
SEASONS = ["Kuruvai", "Samba", "Thaladi", "Navarai", "Kharif", "Rabi", "Summer"]

# Featured cards on the right: (sector, English title, Tamil title, icon, image file stem, tile colour)
# Cards are shown in this order, only for sectors that have schemes, up to MAX_FEATURED.
MAX_FEATURED = 5
FEATURED = [
    ("Poultry", "Poultry farming subsidies", "கோழி வளர்ப்பு", "🐔", "poultry", "#F4A261"),
    ("Goat & Sheep", "Goat & sheep farming", "ஆடு வளர்ப்பு", "🐐", "goat", "#8AB17D"),
    ("Cattle & Dairy", "Cattle & dairy farming", "கால்நடை / பால் பண்ணை", "🐄", "cattle", "#E9C46A"),
    ("Fisheries", "Fish farming", "மீன் வளர்ப்பு", "🐟", "fish", "#4DA3C7"),
    ("Oilseeds", "Oilseed cultivation", "எண்ணெய் வித்துக்கள்", "🌻", "oilseeds", "#E76F51"),
    ("Crop Farming", "Crop farming support", "பயிர் சாகுபடி", "🌾", "crops", "#A7C957"),
    ("Horticulture", "Horticulture & vegetables", "தோட்டக்கலை", "🍌", "horticulture", "#6A994E"),
    ("Other Allied", "Machinery & allied support", "இயந்திரங்கள் / இதர", "🚜", "allied", "#BC6C25"),
]

ALL = "All"
NO_PICK = "— Select a scheme —"
FILTER_KEYS = ["f_type", "f_ttopic", "f_sector", "f_category", "f_crop", "f_group", "f_benefit", "f_apply",
               "f_district", "f_season"]


# ---------------------------------------------------------------- data loading
@st.cache_data
def load_meta(_mtime: float) -> list[dict]:
    return json.loads(META_FILE.read_text(encoding="utf-8")) if META_FILE.exists() else []


@st.cache_data
def load_full_text(_mtime: float) -> dict:
    out = {}
    for p in Path("data/manual").glob("**/*.txt"):
        out[str(p)] = p.read_text(encoding="utf-8", errors="ignore")
    for raw in RAW_DIR.glob("*.jsonl"):
        for l in raw.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                out[r["url"]] = r["text"]
    return out


def raw_mtime() -> float:
    return max((p.stat().st_mtime for p in RAW_DIR.glob("*.jsonl")), default=0)


@st.cache_resource(show_spinner="Loading search index...")
def get_collection():
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    return chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION, embedding_function=ef)


@st.cache_data
def get_catalogue(_mtime: float) -> str:
    meta = load_meta(_mtime)
    if meta:  # names + sector + benefit from the classifier
        lines = [f"- {name_of(m)} [{m.get('sector', '')}]" + (f": {m['benefit']}" if m.get("benefit") else "")
                 for m in sorted(meta, key=name_of)]
    else:
        titles = {m["title"] for m in get_collection().get(include=["metadatas"])["metadatas"]} - {"Scheme list"}
        lines = [f"- {t}" for t in sorted(titles)]
    return f"FULL SCHEME LIST ({len(lines)} schemes):\n" + "\n".join(lines)


@st.cache_resource
def get_llm():
    return OpenAI()


# ---------------------------------------------------------------- filtering
def name_of(m) -> str:
    return m.get("name") or m["title"]


def is_training(m) -> bool:
    if "is_training" in m:
        return bool(m["is_training"])
    return ("Training & Extension" in m.get("categories", [])
            or "Training / Demonstration" in m.get("benefit_types", []))


def matches_list(values, wanted, wildcard=None) -> bool:
    values = values or []
    return wanted in values or (wildcard is not None and wildcard in values)


def filter_schemes(meta, f: dict, acres: float = 0.0):
    out = []
    for m in meta:
        if f.get("type", ALL) == "Training programmes" and not is_training(m):
            continue
        if f.get("type", ALL) == "Schemes & subsidies" and is_training(m):
            continue
        if f.get("ttopic", ALL) != ALL and m.get("training_topic") != f["ttopic"]:
            continue
        if f.get("sector", ALL) != ALL and m.get("sector") != f["sector"]:
            continue
        if f.get("category", ALL) != ALL and f["category"] not in m.get("categories", []):
            continue
        if f.get("crop", ALL) != ALL and not matches_list(m.get("crops"), f["crop"], "All crops"):
            continue
        if f.get("group", ALL) != ALL and not matches_list(m.get("farmer_groups", ["All farmers"]), f["group"], "All farmers"):
            continue
        if f.get("benefit", ALL) != ALL and f["benefit"] not in m.get("benefit_types", []):
            continue
        if f.get("apply", ALL) != ALL and f["apply"] not in m.get("apply_mode", []):
            continue
        if f.get("district", ALL) != ALL and not matches_list(m.get("districts"), f["district"], "All Districts"):
            continue
        if f.get("season", ALL) != ALL and not matches_list(m.get("seasons"), f["season"], "All Seasons"):
            continue
        if acres > 0:
            if m.get("min_acres") is not None and acres < m["min_acres"]:
                continue
            if m.get("max_acres") is not None and acres > m["max_acres"]:
                continue
        out.append(m)
    return sorted(out, key=name_of)


def land_text(m, T=lambda s: s) -> str:
    lo, hi = m.get("min_acres"), m.get("max_acres")
    if lo is not None and hi is not None:
        return f"{lo:g}–{hi:g} {T('acres')}"
    if hi is not None:
        return f"{T('Up to')} {hi:g} {T('acres')}"
    if lo is not None:
        return f"{T('At least')} {lo:g} {T('acres')}"
    return T("No limit stated")


def best_benefit(schemes) -> str:
    """Pick the most eye-catching benefit line (prefers ones with % or ₹)."""
    lines = [s.get("subsidy_amount") or s.get("benefit", "") for s in schemes
             if s.get("subsidy_amount") or s.get("benefit")]
    lines.sort(key=lambda b: (("100%" in b) * 3 + ("%" in b) * 2 + ("₹" in b or "Rs" in b)), reverse=True)
    return lines[0] if lines else ""


def find_image(stem: str):
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = ASSETS / f"{stem}{ext}"
        if p.exists():
            return str(p)
    return None


# ---------------------------------------------------------------- filter callbacks
def reset_filters():
    for k in FILTER_KEYS:
        st.session_state[k] = ALL
    st.session_state["f_acres"] = 0.0
    st.session_state["f_scheme"] = NO_PICK


def show_sector(sector: str):
    reset_filters()
    st.session_state["f_sector"] = sector


# ---------------------------------------------------------------- RAG
def system_prompt(lang: str) -> str:
    lang_rule = ("Reply in the same language the user writes in." if lang == "English"
                 else f"Always reply in {lang}, whatever language the question is in.")
    return f"""You are an assistant that answers questions about Tamil Nadu Government schemes for farmers,
livestock rearers and fish farmers.
Use ONLY the context provided. If the answer is not in the context, say you couldn't find it
in the scheme information available. Do not guess.
When relevant, structure answers as: Scheme name, Objective, Eligibility, Benefits, How to apply, Contact.
Keep scheme names, amounts and dates exactly as in the context.
For questions asking to list, count or find schemes, use the FULL SCHEME LIST given in the context.
{lang_rule}"""


def to_english(text: str) -> str:
    r = get_llm().chat.completions.create(
        model=MODEL, temperature=0,
        messages=[{"role": "system", "content": "Translate the user's text to English. "
                   "If it is already English, return it unchanged. Output only the translation."},
                  {"role": "user", "content": text}])
    return r.choices[0].message.content.strip()


def retrieve(question: str, only_url: str | None = None):
    kwargs = {"where": {"url": only_url}} if only_url else {}
    res = get_collection().query(query_texts=[question], n_results=TOP_K, **kwargs)
    return list(zip(res["documents"][0], res["metadatas"][0], res["distances"][0]))


def answer(question: str, history: list[dict], lang: str, only_url: str | None = None):
    hits = retrieve(to_english(question), only_url)
    context = "\n\n---\n\n".join(f"[Source {i+1}: {m['title']}]\n{d}" for i, (d, m, _) in enumerate(hits))
    catalogue = "" if only_url else get_catalogue(META_FILE.stat().st_mtime if META_FILE.exists() else 0) + "\n\n"
    messages = [{"role": "system", "content": system_prompt(lang)}] + history[-6:]
    messages.append({"role": "user", "content": f"Context:\n{catalogue}{context}\n\nQuestion: {question}"})
    resp = get_llm().chat.completions.create(model=MODEL, messages=messages, temperature=0.1)
    return resp.choices[0].message.content, hits


# ---------------------------------------------------------------- startup checks
if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY not found. Create a .env file in this folder with:  OPENAI_API_KEY=sk-...")
    st.stop()
if not os.path.isdir(DB_DIR):
    st.error("Search index not found. In the terminal run:  python 2_build_index.py")
    st.stop()

meta = load_meta(META_FILE.stat().st_mtime if META_FILE.exists() else 0)
full_text = load_full_text(raw_mtime())
for k in FILTER_KEYS:
    st.session_state.setdefault(k, ALL)
st.session_state.setdefault("f_acres", 0.0)
st.session_state.setdefault("f_scheme", NO_PICK)
st.session_state.setdefault("tried_translate", set())

# ---------------------------------------------------------------- language
sb = st.sidebar
lang_label = sb.selectbox("🌐 மொழி / Language", list(LANGUAGES), key="lang_ui")
lang = LANGUAGES[lang_label]


@st.cache_resource
def get_translator(lang: str, _mtime: float) -> Translator:
    return Translator(lang)


i18n_file = Path("data/i18n") / f"{lang}.json"
tr = get_translator(lang, i18n_file.stat().st_mtime if i18n_file.exists() else 0)
asked: set = set()  # every string the page asks to translate on this run


def T(s: str) -> str:
    if s and lang != "English":
        asked.add(s)
    return tr.t(s)


def TL(values) -> str:
    return ", ".join(T(v) for v in (values or []))


# One-time bulk translation of all scheme details + filter options for a new language
if lang != "English" and meta:
    bulk = set(SECTORS + CROPS + FARMER_GROUPS + BENEFIT_TYPES + APPLY_MODES + DISTRICTS + SEASONS
               + TRAINING_TOPICS + TYPES + ["All Districts", "All Seasons", "All farmers", "All crops"])
    for m in meta:
        bulk.update(m.get("categories", []))
        bulk.update(m.get("documents_required", []))
        for k in ("name", "title", "benefit", "subsidy_amount", "summary", "eligibility", "how_to_apply",
                  "unit_cost", "deadline", "contact", "training_duration", "training_venue", "training_fee"):
            if isinstance(m.get(k), str):
                bulk.add(m[k])
    bulk.update(c[1] for c in FEATURED)
    todo = tr.missing(bulk)
    if todo:
        bar = st.progress(0.0, text=f"Translating schemes into {lang} - first time only, about a minute...")
        tr.ensure(todo, get_llm(), MODEL, progress=lambda p: bar.progress(p, text=f"Translating into {lang}... {int(p*100)}%"))
        bar.empty()

st.caption(T("Tamil Nadu Government welfare schemes and training programmes for farmers, from tn.gov.in"))


def label_all(word):
    return lambda v: T(f"All {word}") if v == ALL else T(v)


# Widgets can come back empty (None) when their labels change language.
# Restore the last value the farmer chose (kept in _last), or "All".
_last = st.session_state.setdefault("_last_filters", {})
_VALID = {"f_type": TYPES, "f_ttopic": TRAINING_TOPICS, "f_sector": SECTORS, "f_crop": CROPS,
          "f_group": FARMER_GROUPS, "f_benefit": BENEFIT_TYPES, "f_apply": APPLY_MODES,
          "f_district": DISTRICTS, "f_season": SEASONS}
for _k in FILTER_KEYS:
    _v = st.session_state.get(_k)
    if _v is None or (_k in _VALID and _v != ALL and _v not in _VALID[_k]):
        st.session_state[_k] = _last.get(_k, ALL)
if st.session_state.get("f_acres") is None:
    st.session_state["f_acres"] = _last.get("f_acres", 0.0)
if st.session_state.get("f_scheme") is None:
    st.session_state["f_scheme"] = _last.get("f_scheme", NO_PICK)

# ---------------------------------------------------------------- sidebar
sb.divider()
sb.header("🔎 " + T("Browse schemes"))

selected, matches = None, []
if not meta:
    sb.info(T("To enable browsing and filters, run in the terminal:") + "\n\n`python 5_classify_schemes.py`")
else:
    n_train = sum(1 for m in meta if is_training(m))
    type_counts = {"Schemes & subsidies": len(meta) - n_train, "Training programmes": n_train}
    sb.radio(T("Show"), [ALL] + TYPES, key="f_type",
             format_func=lambda t: f"{T('Everything')} ({len(meta)})" if t == ALL
             else f"{'💰' if t == TYPES[0] else '🎓'} {T(t)} ({type_counts[t]})")
    if st.session_state.f_type == "Training programmes":
        topic_counts = {}
        for m in meta:
            if is_training(m) and m.get("training_topic"):
                topic_counts[m["training_topic"]] = topic_counts.get(m["training_topic"], 0) + 1
        if st.session_state.f_ttopic not in [ALL] + list(topic_counts):
            st.session_state.f_ttopic = ALL
        sb.selectbox(T("Training topic"), [ALL] + [t for t in TRAINING_TOPICS if t in topic_counts], key="f_ttopic",
                     format_func=lambda t: T("All topics") if t == ALL else f"{T(t)} ({topic_counts[t]})")
    else:
        st.session_state.f_ttopic = ALL

    sec_counts = {s: sum(1 for m in meta if m.get("sector") == s) for s in SECTORS}
    sb.selectbox(T("Sector"), [ALL] + SECTORS, key="f_sector",
                 format_func=lambda s: f"{T('All sectors')} ({len(meta)})" if s == ALL else f"{T(s)} ({sec_counts[s]})")

    in_sector = [m for m in meta if st.session_state.f_sector in (ALL, m.get("sector"))]
    cat_counts = {}
    for m in in_sector:
        for c in m.get("categories", []):
            cat_counts[c] = cat_counts.get(c, 0) + 1
    if st.session_state.f_category not in [ALL] + list(cat_counts):
        st.session_state.f_category = ALL
    sb.selectbox(T("Category"), [ALL] + sorted(cat_counts), key="f_category",
                 format_func=lambda c: T("All categories") if c == ALL else f"{T(c)} ({cat_counts[c]})")

    with sb.expander(T("Who & what"), expanded=False):
        st.selectbox(T("Crop"), [ALL] + CROPS, key="f_crop", format_func=label_all("crops"))
        st.selectbox(T("Farmer type"), [ALL] + FARMER_GROUPS, key="f_group", format_func=label_all("farmer types"))
        st.selectbox(T("Benefit type"), [ALL] + BENEFIT_TYPES, key="f_benefit", format_func=label_all("benefit types"))
        st.selectbox(T("How to apply"), [ALL] + APPLY_MODES, key="f_apply", format_func=label_all("modes"))

    with sb.expander(T("Where, when & land size"), expanded=False):
        st.selectbox(T("District"), [ALL] + DISTRICTS, key="f_district", format_func=label_all("districts"))
        st.selectbox(T("Season"), [ALL] + SEASONS, key="f_season", format_func=label_all("seasons"))
        st.number_input(T("My land holding (acres)"), min_value=0.0, max_value=500.0, step=0.5, key="f_acres",
                        help=T("0 = don't filter by land size. Marginal < 2.5 acres, Small 2.5–5 acres."))

    f = {k[2:]: (st.session_state[k] if st.session_state[k] is not None else ALL) for k in FILTER_KEYS}
    matches = filter_schemes(meta, f, st.session_state.f_acres or 0.0)
    sb.caption(f"**{len(matches)}** {T('scheme(s) match')}")
    by_label = {name_of(m): m for m in matches}
    if st.session_state.f_scheme not in [NO_PICK] + list(by_label):
        st.session_state.f_scheme = NO_PICK
    sb.selectbox(T("Scheme"), [NO_PICK] + list(by_label), key="f_scheme",
                 format_func=lambda v: "— " + T("Select a scheme") + " —" if v == NO_PICK else T(v))
    if st.session_state.f_scheme != NO_PICK:
        selected = by_label[st.session_state.f_scheme]
    sb.button("↺ " + T("Reset filters"), on_click=reset_filters, width="stretch")

_last.update({k: st.session_state[k] for k in FILTER_KEYS + ["f_acres", "f_scheme"]
              if st.session_state.get(k) is not None})

filters_active = bool(meta) and (any(st.session_state[k] not in (ALL, None) for k in FILTER_KEYS)
                                 or (st.session_state.f_acres or 0) > 0)

# ---------------------------------------------------------------- featured cards: one horizontal row
shown = [c for c in FEATURED if any(m.get("sector") == c[0] for m in meta)][:MAX_FEATURED]
if shown:
    st.markdown("### ⭐ " + T("Featured subsidies"))
    cols = st.columns(len(shown), gap="small")
    for col, (sector, title, title_ta, icon, stem, colour) in zip(cols, shown):
        in_sec = [m for m in meta if m.get("sector") == sector]
        with col, st.container(border=True, height=330):
            img = find_image(stem)
            if img:
                st.image(img, width="stretch")
            else:
                st.markdown(
                    f"<div style='background:{colour};border-radius:12px;height:90px;display:flex;"
                    f"align-items:center;justify-content:center;font-size:52px'>{icon}</div>",
                    unsafe_allow_html=True)
            st.markdown(f"**{T(title)}**")
            hl = best_benefit(in_sec)
            if hl:
                st.caption(T(hl)[:110])
            st.button(f"{T('View')} {len(in_sec)} →", key=f"feat_{stem}",
                      on_click=show_sector, args=(sector,), width="stretch")
    st.divider()

# ---------------------------------------------------------------- matches table
if filters_active and not selected:
    with st.expander(f"📋 {T('Matching schemes')} ({len(matches)})", expanded=True):
        if matches:
            st.dataframe(
                [{T("Scheme"): T(name_of(m)),
                  T("Type"): "🎓 " + T("Training") if is_training(m) else "💰 " + T("Scheme"),
                  T("Sector"): T(m.get("sector", "")),
                  T("Subsidy / benefit"): T(m.get("subsidy_amount") or m.get("benefit", "")),
                  T("Who can apply"): TL(m.get("farmer_groups")),
                  T("Land holding"): land_text(m, T)} for m in matches],
                hide_index=True, width="stretch")
            st.caption(T("Pick a scheme in the left sidebar to see full details."))
        else:
            st.info(T("No scheme matches these filters. Try removing one, or press Reset filters."))

# ---------------------------------------------------------------- scheme details
scope_url = None
if selected:
    g = selected.get
    with st.container(border=True):
        st.subheader(("🎓 " if is_training(selected) else "") + T(name_of(selected)))
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**{T('Sector')}**\n\n{T(g('sector', '—'))}")
        c2.markdown(f"**{T('Districts')}**\n\n{TL(g('districts'))}")
        c3.markdown(f"**{T('Seasons')}**\n\n{TL(g('seasons'))}")
        c4.markdown(f"**{T('Land holding')}**\n\n{land_text(selected, T)}")
        money = g("subsidy_amount") or g("benefit")
        if money:
            st.success(f"**💰 {T('Subsidy / benefit')}:** {T(money)}")
        if g("benefit") and g("subsidy_amount") and g("benefit") != money:
            st.markdown(f"**{T('What you get')}:** {T(g('benefit'))}")
        if g("unit_cost"):
            st.markdown(f"**{T('Unit / project cost')}:** {T(g('unit_cost'))}")
        if g("deadline"):
            st.warning(f"**📅 {T('Last date / validity')}:** {T(g('deadline'))}")
        if is_training(selected):
            t1, t2, t3, t4 = st.columns(4)
            t1.markdown(f"**🎓 {T('Topic')}**\n\n{T(g('training_topic') or '—')}")
            t2.markdown(f"**⏱ {T('Duration')}**\n\n{T(g('training_duration') or 'Not stated')}")
            t3.markdown(f"**📍 {T('Venue')}**\n\n{T(g('training_venue') or 'Not stated')}")
            t4.markdown(f"**💵 {T('Fee / stipend')}**\n\n{T(g('training_fee') or 'Not stated')}")
        if g("summary"):
            st.markdown(T(g("summary")))
        for label, val in [("Category", g("categories")), ("Who can apply", g("farmer_groups")),
                           ("Crops", g("crops")), ("Benefit type", g("benefit_types"))]:
            if val:
                st.markdown(f"**{T(label)}:** {TL(val)}")
        if g("eligibility"):
            st.markdown(f"**✅ {T('Eligibility')}:** {T(g('eligibility'))}")

        d1, d2 = st.columns(2)
        with d1:
            st.markdown(f"**📄 {T('Documents to keep ready')}**")
            docs = g("documents_required") or []
            if docs:
                for i, doc in enumerate(docs):
                    st.checkbox(T(doc), key=f"doc_{selected['url']}_{i}")
            else:
                st.caption(T("Not listed on the official page - check with the office below."))
        with d2:
            st.markdown(f"**📝 {T('How to apply')}**")
            st.markdown(T(g("how_to_apply")) or TL(g("apply_mode")) or T("Not stated"))
            if g("contact"):
                st.markdown(f"**📞 {T('Contact')}:** {T(g('contact'))}")
            if (g("apply_link") or "").startswith("http"):
                st.link_button(T("Apply online") + " ↗", g("apply_link"))
        st.markdown(f"[{T('Official page')} ↗]({selected['url']})")
        with st.expander(T("Full text from the website (original language)")):
            st.text(full_text.get(selected["url"], "Not available"))
        if st.toggle(T("Limit chat answers to this scheme"), value=True):
            scope_url = selected["url"]

# ---------------------------------------------------------------- chat
st.markdown("#### 💬 " + T("Ask a question"))
if "history" not in st.session_state:
    st.session_state.history = []
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

hint = (T("Ask about this scheme...") if scope_url
        else T("Ask about schemes, eligibility, benefits... (any language)"))
if q := st.chat_input(hint):
    st.chat_message("user").markdown(q)
    with st.chat_message("assistant"):
        try:
            with st.spinner(T("Searching schemes...")):
                ans, hits = answer(q, st.session_state.history, lang, scope_url)
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()
        st.markdown(ans)
        with st.expander(T("Sources")):
            seen = set()
            for d, m, dist in hits:
                if m["url"] in seen:
                    continue
                seen.add(m["url"])
                st.markdown(f"- **{m['title']}** — {m['url']}  (similarity {1 - dist:.2f})")
    st.session_state.history += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]

# ---------------------------------------------------------------- translate any labels still in English
new = [s for s in tr.missing(asked) if s not in st.session_state.tried_translate]
if new:
    st.session_state.tried_translate.update(new)
    with st.spinner(f"Translating {len(new)} labels into {lang}..."):
        tr.ensure(new, get_llm(), MODEL)
    st.rerun()
