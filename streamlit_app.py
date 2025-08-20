# streamlit_app.py (top)
import streamlit as st, json
from datetime import datetime
import pandas as pd, altair as alt
from io import StringIO
from streamlit_cookies_manager import EncryptedCookieManager
from firebase_config import auth, db, firebase_app  # uses @st.cache_resource inside



if not all(k in st.secrets for k in ["FIREBASE_API_KEY", "FIREBASE_APP_ID"]):
    st.stop()  # prevents half-initialized app from running

st.set_page_config(
    page_title="🚛 Real Balls Logistics",
    layout="wide",                       # better use of space on desktop/tablet
    initial_sidebar_state="collapsed"    # mobile-friendly default
)

# ---------- Responsive helpers & CSS ----------
# ---------- Routing helpers ----------
def _set_qp(**kwargs):
    # robust across Streamlit versions
    try:
        st.query_params.update(kwargs)
    except Exception:
        st.experimental_set_query_params(**kwargs)

def switch_page(page_id: str):
    st.session_state.page = page_id
    _set_qp(page=page_id)


def setup_responsive_and_route():
    # Read ?page= from URL on first load
    qp = st.query_params
    if "page" in qp:
        st.session_state.page = qp["page"]

    # CSS: layout, bottom nav (mobile), hide/show blocks per breakpoint
    st.markdown("""
    <style>
      /* Container width & gutters */
      .block-container {
        max-width: 980px; padding: 0.75rem 1rem 5.5rem; /* bottom pad for bottom nav */
      }
      @media (min-width: 1100px) {
        .block-container { max-width: 1120px; }
      }
      @media (max-width: 768px) {
        .block-container { padding: 0.5rem 0.75rem calc(5.5rem + env(safe-area-inset-bottom)); }
      }

      /* Touch targets & compact inputs */
      .stButton button, .stDownloadButton button {
        min-height: 44px; border-radius: 12px; padding: 0.7rem 1rem;
      }
      .stSelectbox, .stNumberInput, .stTextInput {
        --bl-font: 16px;
      }
      .stNumberInput label, .stTextInput label, .stSelectbox label { font-weight: 600; }
      @media (max-width: 768px) {
        .stNumberInput label, .stTextInput label, .stSelectbox label { font-size: 0.95rem; }
        .stNumberInput input, .stTextInput input { font-size: 1rem; }
      }

      /* Desktop top nav vs. Mobile bottom nav */
      .bl-desktop-nav { display: block; }
      .bl-bottom-nav  { display: none; }
      @media (max-width: 768px) {
        .bl-desktop-nav { display: none !important; }
        .bl-bottom-nav  { display: flex; }
      }

      /* Sticky bottom nav (mobile) */
      .bl-bottom-nav {
        position: fixed; left: 0; right: 0; bottom: 0;
        z-index: 1000;
        justify-content: space-around; gap: 0;
        padding: 0.4rem calc(8px + env(safe-area-inset-left)) calc(8px + env(safe-area-inset-bottom)) calc(8px + env(safe-area-inset-right));
        backdrop-filter: blur(6px);
        border-top: 1px solid rgba(0,0,0,.08);
        background-color: rgba(255,255,255,.85);
      }
      .bl-bottom-nav a {
        flex: 1; text-align: center; text-decoration: none;
        padding: 0.45rem 0; font-size: 0.80rem; line-height: 1.1;
        border-radius: 10px;
        display: flex; flex-direction: column; align-items: center; gap: 2px;
        color: inherit;
      }
      .bl-bottom-nav a .icon { font-size: 1.15rem; }
      .bl-bottom-nav a.active { font-weight: 700; background: rgba(0,0,0,.05); }
      @media (prefers-color-scheme: dark) {
        .bl-bottom-nav { background-color: rgba(30,30,30,.85); border-top-color: rgba(255,255,255,.1); }
        .bl-bottom-nav a.active { background: rgba(255,255,255,.06); }
      }

      /* Tables & charts: edge-to-edge on mobile */
      @media (max-width: 768px) {
        div[data-testid="stDataFrame"] { margin-left: -4px; margin-right: -4px; }
      }

      /* Compact metrics tiles on mobile */
      @media (max-width: 768px) {
        div[data-testid="stMetricValue"] { font-size: 1.1rem; }
        div[data-testid="stMetricLabel"] { font-size: 0.85rem; }
      }
    </style>
    """, unsafe_allow_html=True)

def mobile_bottom_nav(current: str):
    # Sticky wrapper the buttons live in
    st.markdown("""
    <style>
      #bl-bottom-holder {
        position: fixed; left: 0; right: 0; bottom: 0;
        z-index: 1000;
        padding: 0.35rem calc(8px + env(safe-area-inset-left)) calc(8px + env(safe-area-inset-bottom)) calc(8px + env(safe-area-inset-right));
        backdrop-filter: blur(6px);
        border-top: 1px solid rgba(0,0,0,.08);
        background-color: rgba(255,255,255,.85);
      }
      @media (min-width: 769px) { #bl-bottom-holder { display: none; } }
      @media (prefers-color-scheme: dark) {
        #bl-bottom-holder { background-color: rgba(30,30,30,.85); border-top-color: rgba(255,255,255,.1); }
      }
      #bl-bottom-holder .stButton > button {
        min-height: 40px; font-size: 0.82rem; line-height: 1.1;
        border-radius: 12px; padding: 0.45rem 0.25rem;
      }
      #bl-bottom-holder .active > button { font-weight: 800; background: rgba(0,0,0,.06); }
      @media (prefers-color-scheme: dark) {
        #bl-bottom-holder .active > button { background: rgba(255,255,255,.06); }
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div id="bl-bottom-holder">', unsafe_allow_html=True)
    cols = st.columns(6)
    items = [
        ("mileage",  "⛽ Fuel"),
        ("expenses", "💸 Expenses"),
        ("earnings", "💰 Income"),
        ("log",      "📜 Log"),
        ("upload",   "📁 Upload"),
        ("settings", "⚙️ Settings"),
    ]
    for (pid, label), col in zip(items, cols):
        with col:
            # highlight current page
            container_class = "active" if current == pid else ""
            st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
            if st.button(label, key=f"mnav_{pid}", use_container_width=True):
                switch_page(pid)   # <-- soft nav: rerun only, no full reload
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


setup_responsive_and_route()



# --- Auth debug + hard logout helpers ---
def _force_logout():
    st.session_state.user = None
    try:
        _forget_persisted_user_in_browser()
    except Exception:
        pass
    st.success("Forced logout. Reloading…")
    rerun()

# Allow URL-based logout: add ?logout=1 to the URL
qs = st.query_params           # dict-like
if "logout" in qs:             # open with ?logout=1 to force the login screen
    _force_logout()


# Sidebar debug (you can remove later)
with st.sidebar.expander("🛠 Auth debug"):
    st.write({
        "cookie_ready": "yes" if 'cookies' in globals() and cookies.ready() else "no",
        "allow_cookie_fallback": st.session_state.get("allow_cookie_fallback"),
        "has_user": bool(st.session_state.get("user")),
    })
    if st.button("Force logout (debug)"):
        _force_logout()

def rerun():
    fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if callable(fn):
        fn()




# --- Cookie Manager ---
cookies = EncryptedCookieManager(
    prefix="bl_",
    password=st.secrets["cookie_password"]
)

# Graceful fallback if cookies are blocked (iOS Safari / private mode / embedded)
if "allow_cookie_fallback" not in st.session_state:
    st.session_state.allow_cookie_fallback = False

if not cookies.ready() and not st.session_state.allow_cookie_fallback:
    st.info("We use a small cookie to keep you signed in. On iPhone, Safari may block it.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔁 Retry cookies"):
            rerun()
    with c2:
        if st.button("➡️ Continue without cookies"):
            st.session_state.allow_cookie_fallback = True
            rerun()
    st.stop()


COOKIE_KEY = "auth"

def _persist_user_to_browser(user_dict: dict):
    if st.session_state.get("allow_cookie_fallback"):
        # No cookies in fallback; we rely on session_state only
        return
    payload = {
        "refreshToken": user_dict.get("refreshToken"),
        "localId": user_dict.get("localId"),
        "email": user_dict.get("email"),
    }
    cookies[COOKIE_KEY] = json.dumps(payload)
    cookies.save()

def _read_persisted_user_from_browser():
    if st.session_state.get("allow_cookie_fallback"):
        return {}
    raw = cookies.get(COOKIE_KEY)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}

def _forget_persisted_user_in_browser():
    if st.session_state.get("allow_cookie_fallback"):
        return
    cookies[COOKIE_KEY] = ""
    cookies.save()


def _refresh_id_token():
    try:
        u = st.session_state.get("user")
        if u and u.get("refreshToken"):
            refreshed = auth.refresh(u["refreshToken"])
            u["idToken"] = refreshed.get("idToken", u["idToken"])
            if refreshed.get("refreshToken"):
                u["refreshToken"] = refreshed["refreshToken"]
            _persist_user_to_browser(u)
    except Exception:
        st.session_state.user = None
        _forget_persisted_user_in_browser()

# Restore session on first load
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    persisted = _read_persisted_user_from_browser()
    if persisted and persisted.get("refreshToken"):
        try:
            refreshed = auth.refresh(persisted["refreshToken"])
            st.session_state.user = {
                "localId": persisted.get("localId"),
                "idToken": refreshed.get("idToken"),
                "refreshToken": refreshed.get("refreshToken", persisted["refreshToken"]),
                "email": persisted.get("email"),
            }
            _persist_user_to_browser(st.session_state.user)
        except Exception:
            _forget_persisted_user_in_browser()

# ------------------- AUTH UI -------------------
if st.session_state.user is None:
    st.markdown("### 🔐 Login to Real Balls Logistics")

    if hasattr(st, "segmented_control"):
        auth_mode = st.segmented_control(
            "Choose",
            options=["Login", "Register", "Reset Password"],
            default="Login",
            key="auth_mode_seg",
        )
    else:
        auth_mode = st.radio(
            "Choose",
            ["Login", "Register", "Reset Password"],
            index=0,
            key="auth_mode_seg",
        )

    if auth_mode == "Login":
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                st.session_state.user = {
                    "localId": user["localId"],
                    "idToken": user["idToken"],
                    "refreshToken": user["refreshToken"],
                    "email": email
                }
                _persist_user_to_browser(st.session_state.user)
                st.success("✅ Logged in successfully!")
                rerun()
            except Exception as e:
                st.error("❌ " + str(e))

    elif auth_mode == "Register":
        with st.form("register_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account")
        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    auth.create_user_with_email_and_password(email, password)
                    user = auth.sign_in_with_email_and_password(email, password)
                    st.session_state.user = {
                        "localId": user["localId"],
                        "idToken": user["idToken"],
                        "refreshToken": user["refreshToken"],
                        "email": email
                    }
                    _persist_user_to_browser(st.session_state.user)
                    st.success("✅ Registration successful!")
                    rerun()
                except Exception as e:
                    st.error("❌ " + str(e))

    else:  # Reset Password
        with st.form("reset_form"):
            reset_email = st.text_input("Email to reset")
            submitted = st.form_submit_button("Send Reset Email")
        if submitted:
            try:
                auth.send_password_reset_email(reset_email)
                st.success("✅ Password reset email sent!")
            except Exception as e:
                st.error("❌ " + str(e))

    st.stop()

# ✅ If we reached here, user is authenticated
st.success(f"✅ Logged in as {st.session_state.user.get('email')}")

def logout():
    st.session_state.user = None
    _forget_persisted_user_in_browser()
    rerun()

with st.sidebar:
    st.button("🚪 Logout", use_container_width=True, on_click=logout)

if st.session_state.get("allow_cookie_fallback"):
    st.warning("Cookie fallback mode: you’ll stay signed in only until you reload/close this tab. On Safari, allow cookies or open the app in a non-private tab to remember your session.")


# Put a visible Logout button in the main area (mobile-safe and full width)
st.button("🚪 Logout", key="logout_main", use_container_width=True, on_click=logout)
st.caption("Session active")


# ----------------------- Device Profile Detection -----------------------
if "device_profile" not in st.session_state:
    st.session_state.device_profile = "desktop"  # simple default

# ----------------------- Firebase Persistence Functions -----------------------
def save_data():
    uid = st.session_state.user['localId']
    data = {
        "baseline": st.session_state.baseline,
        "last_mileage": st.session_state.last_mileage,
        "total_miles": st.session_state.total_miles,
        "total_cost": st.session_state.total_cost,
        "total_gallons": st.session_state.total_gallons,
        "last_trip_summary": st.session_state.last_trip_summary,
        "log": st.session_state.log,
        "expenses": st.session_state.expenses,
        "earnings": st.session_state.earnings
    }
    db.child("users").child(uid).set(data, st.session_state.user['idToken'])


def load_data():
    uid = st.session_state.user['localId']
    try:
        data = db.child("users").child(uid).get(st.session_state.user['idToken']).val()
        if data:
            st.session_state.baseline = data.get("baseline")
            st.session_state.last_mileage = data.get("last_mileage")
            st.session_state.total_miles = data.get("total_miles", 0.0)
            st.session_state.total_cost = data.get("total_cost", 0.0)
            st.session_state.total_gallons = data.get("total_gallons", 0.0)
            st.session_state.last_trip_summary = data.get("last_trip_summary", {})
            st.session_state.log = data.get("log", [])
            st.session_state.expenses = data.get("expenses", [])
            st.session_state.earnings = data.get("earnings", [])
    except:
        st.warning("No data found for user. Starting fresh.")

# ----------------------- Load on First App Run -----------------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    load_data()

# ----------------------- Auto-save Logic -----------------------
if st.session_state.get("pending_changes", False):
    save_data()
    st.session_state.pending_changes = False

# ----------------------- Layout Mode Notification -----------------------
layout = st.session_state.device_profile
if layout == "mobile":
    st.info("📱 Mobile layout detected")
elif layout == "tablet":
    st.info("📲 Tablet layout detected")
else:
    st.info("💻 Desktop layout detected")

# Now the rest of your app logic should go below
# Be sure to include this line after any state change:
# st.session_state.pending_changes = True

# ----------------------- Export/Import Functions -----------------------

def export_data():
    data = {
        "baseline": st.session_state.baseline,
        "last_mileage": st.session_state.last_mileage,
        "total_miles": st.session_state.total_miles,
        "total_cost": st.session_state.total_cost,
        "total_gallons": st.session_state.total_gallons,
        "last_trip_summary": st.session_state.last_trip_summary,
        "log": st.session_state.log,
        "expenses": st.session_state.expenses,
        "earnings": st.session_state.earnings
    }
    return json.dumps(data, indent=4).encode("utf-8")

def import_data(uploaded_file):
    content = uploaded_file.read()
    data = json.loads(content)
    st.session_state.baseline = data.get("baseline")
    st.session_state.last_mileage = data.get("last_mileage")
    st.session_state.total_miles = data.get("total_miles", 0.0)
    st.session_state.total_cost = data.get("total_cost", 0.0)
    st.session_state.total_gallons = data.get("total_gallons", 0.0)
    st.session_state.last_trip_summary = data.get("last_trip_summary", {})
    st.session_state.log = data.get("log", [])
    st.session_state.expenses = data.get("expenses", [])
    st.session_state.earnings = data.get("earnings", [])
    save_data()
    st.success("Data imported and saved successfully!")

# ----------------------- Session State Initialization -----------------------
def init_session():
    defaults = {
        "edit_expense_index": None,
        "baseline": None,
        "log": [],
        "total_miles": 0.0,
        "total_cost": 0.0,
        "total_gallons": 0.0,
        "last_mileage": None,
        "page": "mileage",
        "last_trip_summary": {},
        "expenses": [],
        "earnings": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    load_data()

init_session()

# ----------------------- Dashboard Summary -----------------------
st.markdown("### 🌐 Dashboard Overview")

col1, col2 = st.columns(2)

with col1:
    st.metric("Total Miles Driven", f"{st.session_state.total_miles:.2f} mi")
    st.metric("Total Fuel Used", f"{st.session_state.total_gallons:.2f} gal")
    st.metric("Total Fuel Cost", f"${st.session_state.total_cost:.2f}")

with col2:
    total_exp = sum(e["amount"] for e in st.session_state.expenses)
    total_earn = sum(e["owner"] for e in st.session_state.earnings)
    net_income = total_earn - total_exp
    st.metric("Total Expenses", f"${total_exp:.2f}")
    st.metric("Total Owner Earnings", f"${total_earn:.2f}")
    st.metric("Net Income", f"${net_income:.2f}")

# ----------------------- Ensure Save After Edits -----------------------

# Example placeholder save hooks (expand in full code):
if "new_expense_added" in st.session_state and st.session_state.new_expense_added:
    save_data()
    st.session_state.new_expense_added = False

if "new_trip_added" in st.session_state and st.session_state.new_trip_added:
    save_data()
    st.session_state.new_trip_added = False

if "new_earning_added" in st.session_state and st.session_state.new_earning_added:
    save_data()
    st.session_state.new_earning_added = False



# ----------------------- Backup & Restore UI -----------------------
st.markdown("### 📁 Backup & Restore")

exported = export_data()
st.download_button(
    label="📥 Download Backup JSON",
    data=exported,
    file_name="balls_logistics_backup.json",
    mime="application/json"
)

uploaded_file = st.file_uploader("📂 Upload Backup JSON", type="json")
if uploaded_file:
    import_data(uploaded_file)
    st.session_state.pending_changes = True

st.info("✅ Data is saved to your Firebase account. You can also backup/restore via JSON.")

# ----------------------- Statistics Page -----------------------
st.markdown("---")
st.markdown("### 📊 Statistics")

if st.session_state.total_miles > 0 and st.session_state.total_gallons > 0:
    avg_mpg = st.session_state.total_miles / st.session_state.total_gallons
    avg_cost_per_mile = st.session_state.total_cost / st.session_state.total_miles

    st.metric("Average MPG", f"{avg_mpg:.2f} mpg")
    st.metric("Average Cost per Mile", f"${avg_cost_per_mile:.2f}")

    mpg_data = [
        {"Date": e["timestamp"], "MPG": e["mpg"]}
        for e in st.session_state.log if e.get("type") == "Trip"
    ]
    if mpg_data:
        mpg_df = pd.DataFrame(mpg_data)
        st.altair_chart(
            alt.Chart(mpg_df).mark_line(point=True).encode(
                x="Date:T",
                y="MPG:Q"
            ).properties(
                title="MPG Per Trip"
            ),
            use_container_width=True
        )

    if st.session_state.expenses:
        df_exp = pd.DataFrame(st.session_state.expenses)
        df_exp = df_exp.groupby("type")["amount"].sum().reset_index()
        st.altair_chart(
            alt.Chart(df_exp).mark_arc().encode(
                theta="amount",
                color="type",
                tooltip=["type", "amount"]
            ).properties(
                title="Expenses by Category"
            ),
            use_container_width=True
        )
else:
    st.info("Add trip and fuel data to see statistics.")

# ----------------------- PDF Report Generator -----------------------

st.markdown("---")
st.markdown("### 📄 Generate Printable Report")

if st.button("🖨️ Generate Report Text"):
    report = StringIO()
    report.write(" Real Balls Logistics Report\n")
    report.write("=====================\n")
    report.write(f"Baseline Mileage: {st.session_state.baseline}\n")
    report.write(f"Last Mileage: {st.session_state.last_mileage}\n")
    report.write(f"Total Distance: {st.session_state.total_miles:.2f} miles\n")
    report.write(f"Total Fuel Used: {st.session_state.total_gallons:.2f} gal\n")
    report.write(f"Total Fuel Cost: ${st.session_state.total_cost:.2f}\n")
    if st.session_state.total_gallons > 0:
        mpg = st.session_state.total_miles / st.session_state.total_gallons
        report.write(f"Average MPG: {mpg:.2f}\n")
    if st.session_state.total_miles > 0:
        cost_mile = st.session_state.total_cost / st.session_state.total_miles
        report.write(f"Average Cost/Mile: ${cost_mile:.2f}\n")

    report.write("\nEarnings Summary:\n")
    for e in st.session_state.earnings:
        report.write(f"- {e['date']}: Worker ${e['worker']}, Owner ${e['owner']}, Net ${e['net_owner']:.2f}\n")

    report_text = report.getvalue()
    st.text_area("Printable Report", report_text, height=400)
    st.download_button("💾 Download as .txt", report_text, file_name="balls_logistics_report.txt")

# ----------------------- UI Enhancements -----------------------
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 800px;
    }
    @media screen and (max-width: 600px) {
        .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        .stButton button {
            font-size: 1rem;
            padding: 0.4rem 0.8rem;
        }
    }
    input[type=number]::-webkit-outer-spin-button,
    input[type=number]::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    input[type=number] {
        appearance: textfield;
    }
    .stButton button {
        border-radius: 0.5rem;
        padding: 0.6rem 1.2rem;
    }
    </style>
""", unsafe_allow_html=True)


# ----------------------- Session State Initialization -----------------------
if "edit_expense_index" not in st.session_state:
    st.session_state.edit_expense_index = None

if "baseline" not in st.session_state:
    st.session_state.baseline = None

if "log" not in st.session_state:
    st.session_state.log = []

if "total_miles" not in st.session_state:
    st.session_state.total_miles = 0.0

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

if "total_gallons" not in st.session_state:
    st.session_state.total_gallons = 0.0

if "last_mileage" not in st.session_state:
    st.session_state.last_mileage = None

if "page" not in st.session_state:
    st.session_state.page = "mileage"

if "last_trip_summary" not in st.session_state:
    st.session_state.last_trip_summary = {}

if "expenses" not in st.session_state:
    st.session_state.expenses = []

if "earnings" not in st.session_state:
    st.session_state.earnings = []

# ---------------------------- Navigation Bar ----------------------------
st.markdown("""
    <style>
        div[data-testid=\"stHorizontalBlock\"] > div {
            
        }
        button[kind=\"secondary\"] {
            padding: 1.5em 2em;
            font-size: 1.2em;
            width: 100%;
            white-space: nowrap;
        }
        input[type=\"number\"]:focus::placeholder {
            color: transparent;
        }
        .input-invalid input {
            border: 2px solid red;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- Adaptive Navigation ----------
# Desktop/Tablet: classic top nav (buttons in columns)
with st.container():
    st.markdown('<div class="bl-desktop-nav">', unsafe_allow_html=True)
    nav_cols = st.columns([1,1,1,1,1,1])
    top_items = [
        ("⛽ Fuel", "mileage"),
        ("💸 Expenses", "expenses"),
        ("💰 Income", "earnings"),
        ("📜 Data Log", "log"),
        ("📁 Upload", "upload"),
        ("⚙️ Settings", "settings"),
    ]
    for col, (label, pid) in zip(nav_cols, top_items):
        with col:
            if st.button(label, use_container_width=True, key=f"top_{pid}"):
                switch_page(pid)
    st.markdown('</div>', unsafe_allow_html=True)

# Mobile: sticky bottom nav (HTML links)
page_name = st.session_state.get("page", "mileage")
mobile_bottom_nav(page_name)


# Default page
page_name = st.session_state.page

st.markdown("### 🚛 Real Balls Logistics Management")

# ---------------------------- PAGE 1: Mileage + Fuel ----------------------------
if page_name == "mileage":
    with st.container():
        st.subheader("📍 Baseline Mileage")

        if st.session_state.baseline is None:
            baseline_input = st.number_input("Enter starting mileage (baseline):", min_value=0.0, step=0.1, placeholder="e.g., 150000")
            if st.button("✅ Save Baseline", disabled=baseline_input <= 0):
                st.session_state.baseline = baseline_input
                st.session_state.last_mileage = baseline_input
                st.success("Baseline mileage saved.")
                st.session_state.pending_changes = True
        else:
            st.write(f"Baseline mileage: **{st.session_state.baseline}**")
            st.write(f"Current mileage: **{st.session_state.last_mileage}**")

        st.subheader("📈 Enter Trip Data")
        mileage_col, gallons_col, cost_col = st.columns(3)
        with mileage_col:
            new_mileage = st.number_input("Enter current mileage (odometer):", min_value=0.0, step=0.1, placeholder="e.g., 150350", key="mileage")
        with gallons_col:
            gallons = st.number_input("Enter gallons used:", min_value=0.0, step=0.1, placeholder="e.g., 20.5", key="gallons")
        with cost_col:
            total_fuel_cost = st.number_input("Enter total fuel cost:", min_value=0.0, step=0.01, placeholder="e.g., 85.00", key="fuel_cost")

        is_valid = True
        if st.session_state.baseline is not None and st.session_state.last_mileage is not None:
            if new_mileage <= st.session_state.last_mileage:
                st.warning("New mileage must be greater than the previous recorded mileage.")
                is_valid = False

        confirm_disabled = not is_valid

        if st.button("✅ Confirm Trip Entry", disabled=confirm_disabled):
            if st.session_state.last_mileage is not None:
                try:
                    distance = new_mileage - st.session_state.last_mileage
                    if distance == 0:
                        st.error("Trip distance is zero. Please enter a higher odometer value.")
                    else:
                        mpg = distance / gallons if gallons > 0 else 0
                        cost_per_mile = total_fuel_cost / distance if distance > 0 else 0

                        st.session_state.total_miles += distance
                        st.session_state.total_cost += total_fuel_cost
                        st.session_state.total_gallons += gallons
                        st.session_state.last_mileage = new_mileage

                        overall_cost_per_mile = (
                            st.session_state.total_cost / st.session_state.total_miles
                            if st.session_state.total_miles > 0 else 0
                        )

                        log_entry = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "Trip",
                            "distance": distance,
                            "gallons": gallons,
                            "mpg": mpg,
                            "total_cost": total_fuel_cost,
                            "cost_per_mile": cost_per_mile,
                            "note": "Mileage + Fuel"
                        }

                        st.session_state.log.append(log_entry)
                        st.session_state.last_trip_summary = log_entry
                        st.session_state.pending_changes = True
                        rerun()

                        st.session_state.pending_changes = True

                except ZeroDivisionError:
                    st.error("Calculation error: Make sure gallons used is not zero.")
            else:
                st.error("Baseline mileage must be set before entering trip data.")

        if st.session_state.last_trip_summary:
            entry = st.session_state.last_trip_summary
            st.subheader("🧶 Trip Summary")

            st.markdown("**📊 Last Trip:**")
            st.write(f"**Distance Driven:** {entry['distance']:.2f} miles")
            st.write(f"**Gallons Used:** {entry['gallons']:.2f} gal")
            st.write(f"**MPG:** {entry['mpg']:.2f}")
            st.write(f"**Total Fuel Cost:** ${entry['total_cost']:.2f}")
            st.write(f"**Cost per Mile (Last Trip):** ${entry['cost_per_mile']:.2f}")

            st.markdown("**📈 Overall Since Baseline:**")
            st.write(f"**Total Distance:** {st.session_state.total_miles:.2f} miles")
            st.write(f"**Total Gallons Used:** {st.session_state.total_gallons:.2f} gal")
            st.write(f"**Total Fuel Cost:** ${st.session_state.total_cost:.2f}")
            overall_cost_per_mile = (
                st.session_state.total_cost / st.session_state.total_miles
                if st.session_state.total_miles > 0 else 0
            )
            st.write(f"**Cost per Mile (Overall):** ${overall_cost_per_mile:.2f}")

# ---------------------------- PAGE 2: Expenses ----------------------------
elif page_name == "expenses":
    st.subheader("💸 Expense Logging")

    expense_options = [
        "Fuel",
        "Repair",
        "Certificates",
        "Insurance",
        "Trailer Rent",
        "IFTA",
        "Reefer Fuel",
        "Other"
    ]

    today = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.edit_expense_index is None:
        expense_type = st.selectbox("Expense Type", expense_options, key="new_expense_type")
        description = st.text_input("Description", key="new_expense_description")
        amount = st.number_input("Amount ($)", min_value=0.0, step=0.01, key="new_expense_amount")

        if st.button("➕ Add Expense"):
            expense = {
                "date": today,
                "type": expense_type,
                "description": description,
                "amount": amount
            }
            st.session_state.expenses.append(expense)
            st.session_state.log.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "Expense",
                "amount": amount,
                "note": f"{expense_type}: {description}"
            })
            st.success("Expense added.")
            st.session_state.pending_changes = True
            rerun()

    if "edit_expense_index" not in st.session_state:
        st.session_state.edit_expense_index = None

    # Show edit form if index is set and still valid
    if st.session_state.edit_expense_index is not None:
        idx = st.session_state.edit_expense_index
        if 0 <= idx < len(st.session_state.expenses):
            expense = st.session_state.expenses[idx]

            st.info(f"Editing expense from {expense['date']}")
            new_type = st.selectbox(
                "Expense Type",
                expense_options,
                index=expense_options.index(expense["type"]) if expense["type"] in expense_options else len(
                    expense_options) - 1,
                key=f"edit_type_{idx}"
            )

            new_description = st.text_input("Description", value=expense["description"], key=f"edit_description_{idx}")
            new_amount = st.number_input("Amount ($)", min_value=0.0, step=0.01, value=expense["amount"])

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Changes"):
                    st.session_state.expenses[idx] = {
                        "date": expense["date"],
                        "type": new_type,
                        "description": new_description,
                        "amount": new_amount
                    }
                    st.session_state.pending_changes = True
                    st.session_state.edit_expense_index = None
                    st.success("Expense updated.")
                    rerun()
            with col2:
                if st.button("❌ Cancel Edit"):
                    st.session_state.edit_expense_index = None
                    rerun()
        else:
            # Reset if somehow invalid index remains
            st.session_state.edit_expense_index = None

    if st.session_state.expenses:
        st.markdown("### 📋 Logged Expenses")
        for i, entry in enumerate(reversed(st.session_state.expenses)):
            idx = len(st.session_state.expenses) - 1 - i
            label = f"{entry['date']} – ${entry['amount']:.2f} – {entry['type']} ({entry['description']})"
            col1, col2, col3 = st.columns([0.8, 0.05, 0.05])
            with col1:
                st.write(label)
            with col2:
                if st.button("✏️", key=f"edit_expense_{i}"):
                    st.session_state.edit_expense_index = idx
                    rerun()
            with col3:
                if st.button("🗑", key=f"delete_expense_{i}"):
                    del st.session_state.expenses[idx]
                    st.session_state.pending_changes = True
                    st.success("Expense deleted.")
                    rerun()
    else:
        st.info("No expenses recorded yet.")

    # Show total expenses
    total_expense_amount = sum(entry["amount"] for entry in st.session_state.expenses)
    st.markdown(f"### 💵 Total Expenses: **${total_expense_amount:.2f}**")


# ---------------------------- PAGE 3: Income ----------------------------
elif page_name == "earnings":
    st.subheader("💰 Income Tracking")

    worker_earning = st.number_input("Worker Earnings:", min_value=0.0, step=0.01)
    owner_earning = st.number_input("Owner Earnings:", min_value=0.0, step=0.01)
    today = datetime.now().strftime("%Y-%m-%d")
    total_expenses = sum(e["amount"] for e in st.session_state.expenses)
    owner_net = owner_earning - total_expenses

    if st.button("✅ Confirm Earning"):
        earning = {
            "date": today,
            "worker": worker_earning,
            "owner": owner_earning,
            "net_owner": owner_net
        }
        st.session_state.earnings.append(earning)
        st.session_state.log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "Income",
            "amount": owner_earning,
            "note": f"Worker: ${worker_earning:.2f}, Owner Net: ${owner_net:.2f}"
        })
        st.success("Earning recorded!")
        st.session_state.pending_changes = True

    if st.session_state.earnings:
        st.markdown("### 📒 Income History")
        df = pd.DataFrame(st.session_state.earnings)

        if "net_owner" not in df.columns:
            df["net_owner"] = df["owner"] - total_expenses

        st.dataframe(df, use_container_width=True)

        # Income chart
        chart = alt.Chart(df).mark_line(point=True).encode(
            x="date:T",
            y=alt.Y("net_owner:Q", title="Net Owner Income"),
            tooltip=["date", "net_owner"]
        ).properties(
            title="Net Owner Income Over Time",
            width=600
        )
        st.altair_chart(chart, use_container_width=True)

        # CSV Export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Income Data (CSV)", csv, "income_data.csv", "text/csv")

        total_worker = df["worker"].sum()
        total_owner = df["owner"].sum()
        total_net = df["net_owner"].sum()
        st.markdown(f"**Total Worker Earnings:** ${total_worker:.2f}")
        st.markdown(f"**Total Owner Earnings:** ${total_owner:.2f}")
        st.markdown(f"**Owner Net After Expenses:** ${total_net:.2f}")
    else:
        st.info("No earnings recorded yet.")




# ---------------------------- PAGE 4: Data Log ----------------------------
elif page_name == "log":
    st.subheader("📜 All Input Records")
    if st.session_state.log:
        for entry in reversed(st.session_state.log):
            entry_type = entry.get("type")
            if entry_type == "Trip":
                st.write(
                    f"🕒 {entry['timestamp']} — 🚛 **Trip**: {entry['distance']:.2f} mi, "
                    f"{entry['mpg']:.2f} MPG, ${entry['total_cost']:.2f}, "
                    f"${entry['cost_per_mile']:.2f}/mi ({entry['note']})"
                )
            else:
                st.write(
                    f"🕒 {entry['timestamp']} — **{entry_type}**: ${entry['amount']:.2f} ({entry['note']})"
                )
    else:
        st.info("No data recorded yet.")

# ---------------------------- PAGE 5: Upload ----------------------------
elif page_name == "upload":
    st.subheader("📁 Upload Files")
    uploaded_files = st.file_uploader("Upload any file(s):", accept_multiple_files=True)
    if uploaded_files:
        for f in uploaded_files:
            st.success(f"Uploaded: {f.name}")

# ---------------------------- PAGE 6: Settings ----------------------------
elif page_name == "settings":
    st.subheader("⚙️ App Settings")

    if st.session_state.get("allow_cookie_fallback"):
        if st.button("Try enabling cookies again"):
            st.session_state.allow_cookie_fallback = False
            rerun()

    st.divider()
    if "reset_requested" not in st.session_state:
        st.session_state.reset_requested = False

    if not st.session_state.reset_requested:
        if st.button("❌ Reset App Data"):
            st.session_state.reset_requested = True
            st.warning("Click again to confirm reset. This will erase all saved data.")
    else:
        if st.button("⚠️ Confirm Reset"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            _forget_persisted_user_in_browser()
            st.markdown("<script>window.location.reload();</script>", unsafe_allow_html=True)


