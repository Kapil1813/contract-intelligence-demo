# -----------------------------
# 🔐 App Config & Login
# -----------------------------
st.set_page_config(page_title="GenAI Rights Dashboard", layout="wide")

APP_PASSWORD = st.secrets.get("app_password", "demo123")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Login form
if not st.session_state.authenticated:
    st.header("Login to GenAI Rights Dashboard")
    with st.form("login_form"):
        password_input = st.text_input("Enter app password:", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if password_input == APP_PASSWORD:
                st.session_state.authenticated = True
                st.success("✅ Access granted — loading dashboard...")
            else:
                st.error("❌ Incorrect password")
    
    # Stop script if not authenticated
    if not st.session_state.authenticated:
        st.stop()