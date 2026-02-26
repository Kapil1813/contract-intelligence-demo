import streamlit as st
import pandas as pd
import json
import re
import time
from fpdf import FPDF
from openai import OpenAI

# -----------------------------
# 🔐 Password Protection
# -----------------------------
PASSWORD = st.secrets.get("app_password", "demo123")  # Streamlit Cloud secret
st.set_page_config(page_title="GenAI Rights & Conflict Dashboard", layout="wide")

st.title("📺 GenAI Rights & Conflict Intelligence Dashboard")

entered_password = st.text_input("Enter password to access dashboard:", type="password")
if entered_password != PASSWORD:
    st.warning("🔒 Enter correct password to continue.")
    st.stop()

# -----------------------------
# 🔑 OpenAI API Client Setup
# -----------------------------
try:
    OPENAI_API_KEY = st.secrets["openai"]["api_key"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets. Please add it under [openai].")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

MAX_CHARS = 8000

# -----------------------------
# Sample Contracts
# -----------------------------
sample_contracts = [
    {
        "filename": "EU_TVOD_Exclusive.pdf",
        "type": "pdf",
        "text": """Distributor grants Apple exclusive TVOD rights in the European Union
from January 1, 2024 through December 31, 2026.

A 6-month SVOD holdback applies following the end of the TVOD window.

Music synchronization rights are excluded and require separate clearance.

Apple may extend the TVOD window by 12 months upon written notice 90 days prior to expiration."""
    },
    {
        "filename": "US_SVOD_Holdback.docx",
        "type": "docx",
        "text": """Distributor grants Apple non-exclusive SVOD rights in the United States
from February 1, 2024 through January 31, 2025.

EST window of 3 months applies before SVOD.

No music rights are included.

Apple may extend SVOD by 6 months upon mutual agreement."""
    },
    {
        "filename": "Movie_A_Rights.docx",
        "type": "docx",
        "text": """Contract Title: Movie A Distribution Agreement

Rights Type: Streaming
Territory: United States
Exclusivity: Exclusive
License Start Date: 2026-01-01
License End Date: 2026-12-31
Holdbacks: None
Music Clearance: Cleared
Options: Renewal for 1 year"""
    },
    {
        "filename": "Movie_B_Rights.docx",
        "type": "docx",
        "text": """Contract Title: Movie B Distribution Agreement

Rights Type: Streaming
Territory: United States
Exclusivity: Exclusive
License Start Date: 2026-06-01
License End Date: 2027-05-31
Holdbacks: None
Music Clearance: Cleared
Options: None"""
    },
    {
        "filename": "Movie_C_Rights.docx",
        "type": "docx",
        "text": """Contract Title: Movie C Distribution Agreement

Rights Type: SVOD
Territory: United States
Exclusivity: Non-exclusive
License Start Date: 2024-02-01
License End Date: 2025-01-31
Holdbacks: EST window of 3 months applies
Music Clearance: No music rights included
Options: Apple may extend SVOD by 6 months upon mutual agreement"""
    }
]

# -----------------------------
# 1️⃣ Contract Selection
# -----------------------------
st.header("1️⃣ Select Sample Contracts")
all_files = [c["filename"] for c in sample_contracts]
selected_files = st.multiselect(
    "Select one or more sample contracts",
    options=all_files,
    default=all_files
)

contracts_data = []
for fname in selected_files:
    contract = next(c for c in sample_contracts if c["filename"] == fname)
    contracts_data.append({"filename": contract["filename"], "text": contract["text"]})

if not contracts_data:
    st.warning("Select contracts to start analysis.")
    st.stop()

# -----------------------------
# 2️⃣ Structured Rights Extraction (Simulated)
# -----------------------------
st.header("2️⃣ Structured Rights Extraction")
rights_dfs = []

progress = st.progress(0)
total = len(contracts_data)

for i, contract in enumerate(contracts_data):
    st.info(f"Extracting rights from {contract['filename']}…")
    prompt = f"""
Extract rights attributes from this contract.

Return a SINGLE JSON object with EXACT keys:
{{
  "Rights Type": "",
  "Territory": "",
  "Exclusivity": "",
  "License Start Date": "",
  "License End Date": "",
  "Holdbacks": "",
  "Music Clearance": "",
  "Options": ""
}}

No markdown. No explanation.

Contract:
{contract['text']}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        try:
            parsed = json.loads(raw_output)
        except:
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            parsed = json.loads(match.group()) if match else {}
        # Ensure all keys exist
        for key in ["Rights Type","Territory","Exclusivity","License Start Date",
                    "License End Date","Holdbacks","Music Clearance","Options"]:
            if key not in parsed:
                parsed[key] = None
        df = pd.DataFrame([parsed])
        df["Contract"] = contract["filename"]
        rights_dfs.append(df)
    except Exception as e:
        st.error(f"Error extracting rights: {e}")
    progress.progress((i+1)/total)
    time.sleep(0.5)

combined_df = pd.concat(rights_dfs, ignore_index=True)
combined_df["License Start Date"] = pd.to_datetime(combined_df["License Start Date"], errors="coerce")
combined_df["License End Date"] = pd.to_datetime(combined_df["License End Date"], errors="coerce")

# -----------------------------
# 3️⃣ Conflict & Holdback Detection
# -----------------------------
st.header("3️⃣ Conflict & Holdback Intelligence")
conflicts = []
for i in range(len(combined_df)):
    for j in range(i+1, len(combined_df)):
        r1 = combined_df.iloc[i]
        r2 = combined_df.iloc[j]
        territory_conflict = str(r1["Territory"]).lower() == str(r2["Territory"]).lower()
        date_conflict = pd.notna(r1["License Start Date"]) and pd.notna(r2["License Start Date"]) and \
                        r1["License Start Date"] <= r2["License End Date"] and \
                        r2["License Start Date"] <= r1["License End Date"]
        exclusive_conflict = str(r1["Exclusivity"]).lower() == "exclusive" or \
                             str(r2["Exclusivity"]).lower() == "exclusive"
        if territory_conflict and date_conflict and exclusive_conflict:
            conflicts.append(f"{r1['Contract']} ↔ {r2['Contract']} (Exclusive overlap in {r1['Territory']})")

# -----------------------------
# KPI Summary
# -----------------------------
st.subheader("📊 Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Contracts", len(combined_df))
col2.metric("Exclusive Deals", combined_df["Exclusivity"].str.lower().eq("exclusive").sum())
col3.metric("Contracts with Holdbacks", combined_df["Holdbacks"].str.lower().ne("none").sum())
col4.metric("Detected Conflicts", len(conflicts))

# -----------------------------
# Combined Rights Table with Highlights
# -----------------------------
def highlight(row):
    holdback_flag = str(row["Holdbacks"]).strip().lower() not in ["none",""]
    conflict_flag = any(row["Contract"] in c for c in conflicts)
    colors = []
    for col in row.index:
        if conflict_flag:
            colors.append("background-color: #f28b82; color: black")  # Red
        elif holdback_flag:
            colors.append("background-color: #fff475; color: black")  # Yellow
        else:
            colors.append("background-color: #ccff90; color: black")  # Green
    return colors

st.subheader("Combined Rights Table (Legend: Green=All clear, Yellow=Holdbacks, Red=Conflicts)")
st.dataframe(combined_df.style.apply(highlight, axis=1), width=1400)

# -----------------------------
# CSV Export
# -----------------------------
csv_data = combined_df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download CSV", csv_data, "combined_rights.csv", "text/csv")

# -----------------------------
# PDF Export (Improved)
# -----------------------------
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=10)
pdf.add_page()
pdf.set_font("Arial", "B", 14)
pdf.cell(0, 10, "GenAI Rights Conflict Dashboard", ln=True)
pdf.ln(5)

cols = combined_df.columns.tolist()
page_width = pdf.w - 20
col_widths = [page_width / len(cols)] * len(cols)
pdf.set_font("Arial", "B", 8)

# Header
for i, col_name in enumerate(cols):
    pdf.cell(col_widths[i], 8, str(col_name), border=1, align="C")
pdf.ln()
pdf.set_font("Arial", "", 8)

# Row height helper
def get_row_height(row):
    max_lines = 1
    for i, col in enumerate(cols):
        text = str(row[col])
        lines = pdf.multi_cell(col_widths[i], 5, text, border=0, split_only=True)
        max_lines = max(max_lines, len(lines))
    return max_lines * 5

# Draw rows
for _, row in combined_df.iterrows():
    row_height = get_row_height(row)
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    for i, col in enumerate(cols):
        pdf.set_xy(x_start + sum(col_widths[:i]), y_start)
        pdf.multi_cell(col_widths[i], 5, str(row[col]), border=1)
    pdf.ln(row_height)

pdf_bytes = pdf.output(dest="S").encode("latin1")
st.download_button(
    "📥 Download PDF (Improved Table)",
    pdf_bytes,
    "combined_rights_report.pdf",
    "application/pdf"
)

# -----------------------------
# Auto-generated User Stories
# -----------------------------
st.header("4️⃣ Backlog User Stories")
progress_story = st.progress(0)
for i, contract in enumerate(contracts_data):
    story_prompt = f"""
Create an Agile user story for a Product Owner.

Include ONLY:
- User Story
- Acceptance Criteria
- Test Notes

Contract:
{contract['text']}
"""
    try:
        story_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":story_prompt}]
        )
        story = story_response.choices[0].message.content
    except:
        story = "Error generating story"
    st.subheader(contract["filename"])
    st.text_area(f"User Story - {contract['filename']}", story, height=200)
    progress_story.progress((i+1)/len(contracts_data))
    time.sleep(0.5)

st.success("🎉 Dashboard ready! CSV and PDF exports available above.")