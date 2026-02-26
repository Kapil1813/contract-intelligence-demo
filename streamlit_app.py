# streamlit_app.py
import streamlit as st
import pandas as pd
import json
import re
from fpdf import FPDF
from datetime import datetime
import time
from openai import OpenAI

# -----------------------------
# 🔐 Password Protection
# -----------------------------
PASSWORD = st.secrets.get("app_password", "demo123")  # set this in Streamlit Secrets
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("Enter password to access the dashboard", type="password")
    if st.button("Login"):
        if pwd == PASSWORD:
            st.session_state.authenticated = True
            st.success("✅ Access granted!")
        else:
            st.error("❌ Incorrect password")
    st.stop()

# -----------------------------
# ✅ OpenAI Client Setup
# -----------------------------
try:
    OPENAI_API_KEY = st.secrets["openai"]["api_key"]
except KeyError:
    st.error("❌ OpenAI API key not found in Streamlit secrets!")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# Page Setup
# -----------------------------
st.set_page_config(page_title="GenAI Rights Conflict Dashboard", layout="wide")
st.title("📺 GenAI Rights & Conflict Intelligence Dashboard")

MAX_CHARS = 8000

# -----------------------------
# Sample Contracts
# -----------------------------
sample_contracts = [
    {
        "filename": "EU_TVOD_Exclusive.pdf",
        "text": """Distributor grants Apple exclusive TVOD rights in the European Union
from January 1, 2024 through December 31, 2026.

A 6-month SVOD holdback applies following the end of the TVOD window.

Music synchronization rights are excluded and require separate clearance.

Apple may extend the TVOD window by 12 months upon written notice 90 days prior to expiration."""
    },
    {
        "filename": "US_SVOD_Holdback.docx",
        "text": """Distributor grants Apple non-exclusive SVOD rights in the United States
from February 1, 2024 through January 31, 2025.

EST window of 3 months applies before SVOD.

No music rights are included.

Apple may extend SVOD by 6 months upon mutual agreement."""
    },
    {
        "filename": "Movie_A_Rights.docx",
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
        "text": """Contract Title: Movie C Distribution Agreement

Rights Type: SVOD
Territory: United States
Exclusivity: Non-exclusive
License Start Date: 2024-02-01
License End Date: 2025-01-31
Holdbacks: EST window of 3 months applies
Music Clearance: Not included
Options: Apple may extend SVOD by 6 months upon mutual agreement"""
    }
]

# -----------------------------
# 1️⃣ Select Contracts
# -----------------------------
st.header("1️⃣ Select Sample Contracts")
all_files = [c["filename"] for c in sample_contracts]
selected_files = st.multiselect("Choose contracts to analyze", options=all_files, default=all_files)
contracts_data = [c for c in sample_contracts if c["filename"] in selected_files]

if not contracts_data:
    st.info("Select at least one contract to continue.")
    st.stop()

# -----------------------------
# 2️⃣ Structured Rights Extraction
# -----------------------------
st.header("2️⃣ Structured Rights Extraction")

rights_list = []
progress = st.progress(0)

for i, contract in enumerate(contracts_data):
    st.info(f"Extracting rights from {contract['filename']}…")
    prompt = f"""
Extract rights attributes from this contract as JSON ONLY.

Use EXACT keys:
Rights Type, Territory, Exclusivity, License Start Date, License End Date, Holdbacks, Music Clearance, Options

Contract:
{contract['text']}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        raw_output = response.choices[0].message.content.strip()

        # Attempt to parse JSON
        match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            parsed = {}
        
        # Ensure all keys
        keys = ["Rights Type","Territory","Exclusivity",
                "License Start Date","License End Date",
                "Holdbacks","Music Clearance","Options"]
        for key in keys:
            if key not in parsed:
                parsed[key] = None

        parsed["Contract"] = contract["filename"]
        rights_list.append(parsed)
    except Exception as e:
        st.error(f"Failed extraction for {contract['filename']}: {str(e)}")
    progress.progress((i+1)/len(contracts_data))
    time.sleep(0.5)

if not rights_list:
    st.warning("⚠️ No structured rights extracted.")
    st.stop()

df = pd.DataFrame(rights_list)
df["License Start Date"] = pd.to_datetime(df["License Start Date"], errors="coerce")
df["License End Date"] = pd.to_datetime(df["License End Date"], errors="coerce")

# -----------------------------
# 3️⃣ Conflict Detection
# -----------------------------
st.header("3️⃣ Conflict & Holdback Intelligence")
conflicts = []
for i in range(len(df)):
    for j in range(i+1, len(df)):
        r1, r2 = df.iloc[i], df.iloc[j]
        territory_conflict = str(r1["Territory"]).lower() == str(r2["Territory"]).lower()
        date_conflict = pd.notna(r1["License Start Date"]) and pd.notna(r2["License Start Date"]) and \
                        r1["License Start Date"] <= r2["License End Date"] and \
                        r2["License Start Date"] <= r1["License End Date"]
        exclusive_conflict = str(r1["Exclusivity"]).lower() == "exclusive" or str(r2["Exclusivity"]).lower() == "exclusive"
        if territory_conflict and date_conflict and exclusive_conflict:
            conflicts.append(f"{r1['Contract']} ↔ {r2['Contract']} (Exclusive overlap in {r1['Territory']})")

# -----------------------------
# KPI Summary
# -----------------------------
st.subheader("📊 Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Contracts", len(df))
col2.metric("Exclusive Deals", df["Exclusivity"].astype(str).str.lower().eq("exclusive").sum())
col3.metric("Contracts with Holdbacks", df["Holdbacks"].astype(str).str.lower().ne("none").sum())
col4.metric("Detected Conflicts", len(conflicts))

# -----------------------------
# 4️⃣ Table with Highlights
# -----------------------------
def highlight(row):
    holdback_flag = str(row["Holdbacks"]).strip().lower() not in ["none","", "nan"]
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

st.subheader("Combined Rights Table (Legend: Green = All clear, Red = Conflict, Yellow = Holdbacks)")
st.dataframe(df.style.apply(highlight, axis=1), width=1400)

# -----------------------------
# 5️⃣ CSV Export
# -----------------------------
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download CSV", csv_data, "combined_rights.csv", "text/csv")

# -----------------------------
# 6️⃣ PDF Export
# -----------------------------
def generate_pdf(dataframe):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "GenAI Rights Conflict Dashboard Report", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", size=8)

    columns = dataframe.columns.tolist()
    page_width = pdf.w - 20
    col_width = page_width / len(columns)
    
    # Header
    pdf.set_font("Arial", "B", 8)
    for col in columns:
        pdf.cell(col_width, 6, str(col), border=1)
    pdf.ln()
    pdf.set_font("Arial", size=8)

    # Rows
    for _, row in dataframe.iterrows():
        max_lines = 1
        for i, col in enumerate(columns):
            cell_text = str(row[col])
            # Multi-cell for long text
            pdf.multi_cell(col_width, 5, cell_text, border=1)
            pdf.set_xy(pdf.get_x() + col_width, pdf.get_y() - 5)
        pdf.ln(5)
    
    return pdf.output(dest="S").encode("latin1")

pdf_bytes = generate_pdf(df)
st.download_button("📥 Download PDF", pdf_bytes, "combined_rights_report.pdf", "application/pdf")