"""
Step 2b: Read every scraped scheme page and tag it with structured details:
category, districts, seasons, land-holding limits, benefit, eligibility, how to apply.
Output: data/schemes_meta.json  (used by the sidebar filters in 3_app.py)

Run once after 1_scrape.py (and again whenever you re-scrape):
    python 5_classify_schemes.py
Cost: one small LLM call per scheme (~55 calls).
"""
import json
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
RAW_DIR = Path("data/raw")
OUT = Path("data/schemes_meta.json")
EXCLUDED = Path("data/schemes_excluded.json")  # dropped as not for farmers - review if needed
MAX_CHARS = 12000  # text sent per call
MAX_WINDOWS = 6    # long PDFs are read in up to 6 windows of MAX_CHARS

CATEGORIES = [
    "Seeds & Planting Material",
    "Fertilizers & Soil Health",
    "Oilseeds & Edible Oil",
    "Electricity & Pumpsets",
    "Irrigation & Water Management",
    "Farm Machinery & Equipment",
    "Plant Protection & Pesticides",
    "Crop Insurance",
    "Credit, Loans & Interest Subsidy",
    "Horticulture",
    "Organic & Natural Farming",
    "Marketing, Storage & Post-Harvest",
    "Income Support & Relief",
    "Training & Extension",
    "Cattle & Dairy Farming",
    "Poultry Farming",
    "Goat & Sheep Farming",
    "Fisheries & Aquaculture",
    "Other",
]

SECTORS = [
    "Crop Farming", "Oilseeds", "Horticulture", "Cattle & Dairy", "Poultry",
    "Goat & Sheep", "Fisheries", "Other Allied",
]
CROPS = [
    "Paddy", "Millets", "Pulses", "Groundnut", "Sesame", "Sunflower", "Coconut", "Oil Palm",
    "Sugarcane", "Cotton", "Maize", "Banana", "Vegetables", "Fruits", "Flowers", "Spices",
    "Turmeric", "Tea & Coffee", "All crops",
]
FARMER_GROUPS = [
    "All farmers", "Small farmers", "Marginal farmers", "SC/ST", "Women", "FPOs & Groups",
    "Tenant farmers", "Youth & Graduates", "Fishermen",
]
BENEFIT_TYPES = [
    "Cash / Direct transfer", "Subsidy on purchase", "Free inputs / In-kind",
    "Loan / Interest subsidy", "Insurance", "Training / Demonstration", "Infrastructure grant",
]
TRAINING_TOPICS = [
    "Crop cultivation", "Organic & natural farming", "Dairy & cattle management", "Poultry rearing",
    "Goat & sheep rearing", "Fish farming", "Farm machinery", "Irrigation & water", "Plant protection",
    "Value addition & marketing", "Entrepreneurship & FPO", "Digital & drone technology", "Other",
]
APPLY_MODES = [
    "Online portal", "Agriculture / Block office", "Veterinary / Fisheries office", "Bank / Cooperative",
    "Not stated",
]

DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul",
    "Erode", "Kallakurichi", "Kancheepuram", "Kanniyakumari", "Karur", "Krishnagiri", "Madurai",
    "Mayiladuthurai", "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai",
    "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "Theni",
    "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur", "Tiruppur", "Tiruvallur",
    "Tiruvannamalai", "Tiruvarur", "Vellore", "Viluppuram", "Virudhunagar",
]

SEASONS = ["Kuruvai", "Samba", "Thaladi", "Navarai", "Kharif", "Rabi", "Summer"]

PROMPT = f"""You extract structured facts about Tamil Nadu Government schemes for farmers, livestock rearers
and fish farmers. The text may describe ONE scheme, SEVERAL schemes (e.g. a PDF listing many), or NONE
(e.g. an About Us, contact or news page). Use ONLY the text given.
Return JSON: {{"schemes": [ ... ]}} with one object per distinct scheme / subsidy / assistance programme,
or {{"schemes": []}} if there is none. Each object has exactly these keys:
- "for_farmers": true if individual farmers, livestock / poultry rearers, fish farmers or fishers, or their
  groups (FPOs, SHGs, cooperatives) can apply for or receive this benefit; false if it is only for
  government offices, staff, students, traders, industry, research or general public works
- "name": scheme name (short, as written in the text)
- "sector": ONE item chosen ONLY from {SECTORS} (Crop Farming = field crops; Oilseeds = groundnut, sesame, sunflower, oil palm etc.)
- "categories": 1-3 items chosen ONLY from {CATEGORIES}
- "districts": list chosen ONLY from {DISTRICTS}; use ["All Districts"] if the scheme is state-wide or no district is mentioned
- "seasons": list chosen ONLY from {SEASONS}; use ["All Seasons"] if no season is mentioned
- "min_acres": minimum land holding in ACRES if stated, else null (convert hectares: 1 ha = 2.47 acres)
- "max_acres": maximum land holding in ACRES if stated, else null. "Small and marginal farmers" only => 5
- "crops": list chosen ONLY from {CROPS}; ["All crops"] if it is a crop scheme not tied to one crop; [] for livestock/fisheries
- "farmer_groups": list chosen ONLY from {FARMER_GROUPS}; ["All farmers"] if no group restriction is stated
- "benefit_types": 1-3 items chosen ONLY from {BENEFIT_TYPES}
- "apply_mode": list chosen ONLY from {APPLY_MODES}
- "benefit": one sentence on the subsidy/assistance amount or %, "" if not stated
- "summary": 2 sentences on what the scheme does
- "eligibility": short text, "" if not stated
- "how_to_apply": short step-by-step text incl. office/portal, "" if not stated
- "subsidy_amount": exact amount / % / ceiling as written (e.g. "50% up to Rs.25,000 per ha"), "" if not stated
- "unit_cost": unit cost or project cost if stated, else ""
- "documents_required": list of documents to submit (e.g. "Aadhaar", "Chitta / Adangal", "Bank passbook"), [] if not stated
- "contact": office / officer / phone to contact, "" if not stated
- "apply_link": full web address to apply online if written in the text, else ""
- "deadline": last date or validity period if stated, else ""
- "is_training": true if the programme is MAINLY training, demonstration, exposure visit, farmer field
  school or capacity building for farmers; false for subsidies / inputs / loans / insurance
- "training_topic": if is_training, ONE item chosen ONLY from {TRAINING_TOPICS}; else ""
- "training_duration": e.g. "3 days", "1 month", "" if not stated
- "training_venue": e.g. "KVK / Training centre / Village", "" if not stated
- "training_fee": e.g. "Free", "Rs.500 with stipend Rs.200/day", "" if not stated
Do not guess values that are not in the text."""


def clean(data: dict) -> dict:
    """Keep values inside the allowed lists so the sidebar stays clean."""
    data["categories"] = [c for c in data.get("categories", []) if c in CATEGORIES] or ["Other"]
    data["districts"] = [x for x in data.get("districts", []) if x in DISTRICTS] or ["All Districts"]
    data["seasons"] = [x for x in data.get("seasons", []) if x in SEASONS] or ["All Seasons"]
    data["sector"] = data.get("sector") if data.get("sector") in SECTORS else "Other Allied"
    data["crops"] = [x for x in data.get("crops", []) if x in CROPS]
    data["farmer_groups"] = [x for x in data.get("farmer_groups", []) if x in FARMER_GROUPS] or ["All farmers"]
    data["benefit_types"] = [x for x in data.get("benefit_types", []) if x in BENEFIT_TYPES]
    data["apply_mode"] = [x for x in data.get("apply_mode", []) if x in APPLY_MODES] or ["Not stated"]
    data["for_farmers"] = data.get("for_farmers") is not False
    data["is_training"] = bool(data.get("is_training"))
    tt = data.get("training_topic")
    data["training_topic"] = (tt if tt in TRAINING_TOPICS else "Other") if data["is_training"] else ""
    for k in ("training_duration", "training_venue", "training_fee"):
        data[k] = str(data.get(k) or "")
    docs = data.get("documents_required") or []
    data["documents_required"] = [str(d) for d in docs] if isinstance(docs, list) else [str(docs)]
    for k in ("subsidy_amount", "unit_cost", "contact", "apply_link", "deadline", "benefit", "summary",
              "eligibility", "how_to_apply"):
        data[k] = str(data.get(k) or "")
    for k in ("min_acres", "max_acres"):
        try:
            data[k] = float(data[k]) if data.get(k) not in (None, "") else None
        except (TypeError, ValueError):
            data[k] = None
    return data


def classify(llm: OpenAI, title: str, text: str) -> list[dict]:
    found = []
    for start in range(0, min(len(text), MAX_CHARS * MAX_WINDOWS), MAX_CHARS):
        resp = llm.chat.completions.create(
            model=MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": PROMPT},
                      {"role": "user", "content": f"Title: {title}\n\n{text[start:start + MAX_CHARS]}"}],
        )
        items = json.loads(resp.choices[0].message.content).get("schemes", [])
        found += [clean(x) for x in items if isinstance(x, dict) and (x.get("name") or "").strip()]
    return found


def load_records() -> list[dict]:
    records = []
    for raw in sorted(RAW_DIR.glob("*.jsonl")):
        records += [json.loads(l) for l in raw.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in records if r["title"] != "Scheme list" and len(r["text"]) > 100]


def main():
    records = load_records()
    if not records:
        raise SystemExit("No data in data/raw/ - run 1_scrape.py and/or 6_crawl_sites.py first")

    llm = OpenAI()
    meta, excluded, names = [], [], set()
    for i, r in enumerate(records, 1):
        try:
            items = classify(llm, r["title"], r["text"])
        except Exception as e:
            print(f"  [{i}] FAILED {r['title'][:60]}: {e}")
            continue
        if not items:
            print(f"  [{i}/{len(records)}] {r['title'][:55]:55s} -> (no scheme on this page)")
        for m in items:
            key = m["name"].strip().lower()
            if key in names:  # same scheme found on another page / window
                continue
            names.add(key)
            m["title"] = m["name"].strip()
            m["url"], m["department"] = r["url"], r.get("department", "Agriculture")
            if not m["for_farmers"]:
                excluded.append(m)
                print(f"  [{i}/{len(records)}] {m['title'][:55]:55s} -> skipped (not for farmers)")
                continue
            meta.append(m)
            print(f"  [{i}/{len(records)}] {m['title'][:55]:55s} -> {m['sector']} | {', '.join(m['categories'])}")

    OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    EXCLUDED.write_text(json.dumps(excluded, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nKept {len(meta)} farmer schemes; skipped {len(excluded)} not meant for farmers -> {EXCLUDED}")

    # Summary so you can see what the data actually contains
    sec = Counter(m["sector"] for m in meta)
    print("Schemes per sector:")
    for k, v in sec.most_common():
        print(f"  {v:3d}  {k}")
    print()
    cat = Counter(c for m in meta for c in m["categories"])
    dist = Counter(d for m in meta for d in m["districts"])
    seas = Counter(s for m in meta for s in m["seasons"])
    print(f"\nSaved {len(meta)} schemes -> {OUT}\n")
    print("Schemes per category:")
    for k, v in cat.most_common():
        print(f"  {v:3d}  {k}")
    print("\nDistrict tags:", ", ".join(f"{k} ({v})" for k, v in dist.most_common()))
    print("Season tags:  ", ", ".join(f"{k} ({v})" for k, v in seas.most_common()))
    print("With land-size limits:", sum(1 for m in meta if m["min_acres"] or m["max_acres"]))
    print("Training programmes:  ", sum(1 for m in meta if m["is_training"]))
    print("With subsidy amount:  ", sum(1 for m in meta if m["subsidy_amount"]))
    print("With documents list:  ", sum(1 for m in meta if m["documents_required"]))
    print("With contact details: ", sum(1 for m in meta if m["contact"]))


if __name__ == "__main__":
    main()
