# streamlit_app.py — iPhone-optimized (compact, responsive)
import json
from datetime import datetime
from io import StringIO

import altair as alt
import pandas as pd
import streamlit as st


# ------------------------- Page & Global Styles -------------------------
st.set_page_config(
    page_title="🚛 Real Balls Logistics Management",
    page_icon="🚛",
    layout="wide",  # use full width; we'll constrain with CSS
    initial_sidebar_state="collapsed",
)
# Now it's safe to import things that might use st.*
from firebase_config import get_firebase_clients     # <-- changed
from streamlit_cookies_manager import EncryptedCookieManager

# Initialize Firebase clients after page_config is set
firebase_app, auth, db = get_firebase_clients()


st.markdown(
    """
    <style>
      /* Global reset to avoid sideways overflow on iPhone */
      * { box-sizing: border-box; }
      html, body { max-width: 100%; overflow-x: hidden; touch-action: pan-y; }
      [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stToolbar"] { overflow-x: hidden; }

      /* Base scale down; tighten paddings; mobile-first tweaks */
      :root { --scale: .90; }
      html, body, [data-testid="stAppViewContainer"] { font-size: calc(16px * var(--scale)); }

      .block-container { padding: .6rem .6rem 2rem; max-width: 720px; width: 100%; margin: 0 auto; }
      .stButton button, .stDownloadButton button { padding: .45rem .7rem; font-size: .92rem; border-radius: .6rem; }
      .stTextInput input, .stNumberInput input { height: 36px; font-size: .95rem; }
      [data-testid="stMetric"] { padding: .25rem .5rem; }
      [data-testid="stMetricLabel"] p { font-size: .78rem; margin-bottom: 0; }
      [data-testid="stMetricValue"] div { font-size: 1.05rem; }
      [data-testid="stMetricDelta"] { font-size: .75rem; }

      /* Horizontal nav: compact chips */
      .nav-chip { display:inline-flex; align-items:center; gap:.35rem; padding:.45rem .6rem; border:1px solid var(--accent,#ddd); border-radius:.75rem; margin-right:.4rem; cursor:pointer; font-size:.95rem; background: white; }
      .nav-chip.active { background: #eff6ff; border-color:#93c5fd; }
      .nav-bar { overflow-x:auto; white-space:nowrap; padding-bottom:.25rem; margin-bottom:.35rem; }

      /* Media elements & charts never overflow */
      img, svg, canvas, video { max-width: 100%; height: auto; display: block; }
      [data-testid="stHorizontalBlock"], [data-testid="stColumns"], .element-container { overflow-x: hidden; max-width: 100%; }

      /* Inputs: remove number spinners */
      input[type=number]::-webkit-outer-spin-button,
      input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
      input[type=number] { appearance: textfield; }

      /* Headings smaller */
      h1 { font-size: 1.6rem; margin:.45rem 0 .35rem; }
      h2 { font-size: 1.05rem; margin:.45rem 0 .3rem; }
      h3 { font-size: .95rem; margin:.4rem 0 .25rem; }

      /* Mobile breakpoint */
      @media (max-width: 430px) {
        :root { --scale: .84; }
        .block-container { max-width: 520px; padding:.5rem .5rem 2rem; }
        .stButton button, .stDownloadButton button { padding:.4rem .55rem; font-size:.88rem; }
        .stTextInput input, .stNumberInput input { height: 34px; font-size:.9rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Account bar styles (email without parentheses + wide Logout) ---
st.markdown(
    """
    <style>
      .account-row { display:flex; align-items:center; justify-content:space-between; gap:.5rem; margin:.25rem 0 .35rem 0; }
      .account-row .email { font-size:.95rem; font-weight:500; overflow-wrap:anywhere; }
      .account-row .logout-link { display:inline-flex; align-items:center; padding:.35rem .6rem; border:1px solid #e5e7eb; border-radius:10px; text-decoration:none; }
      @media (prefers-color-scheme: dark){ .account-row .logout-link { border-color:#374151; color:#e5e7eb; } }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------- Secrets Check -------------------------
if not all(k in st.secrets for k in ["FIREBASE_API_KEY", "FIREBASE_APP_ID", "cookie_password"]):
    st.stop()


# ------------------------- Rerun Helper -------------------------

def rerun():
    fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if callable(fn):
        fn()


# ------------------------- Cookie Manager -------------------------
cookies = EncryptedCookieManager(prefix="bl_", password=st.secrets["cookie_password"])
if "allow_cookie_fallback" not in st.session_state:
    st.session_state.allow_cookie_fallback = False

if not cookies.ready() and not st.session_state.allow_cookie_fallback:
    st.info("iOS may block cookies in Private Mode. Continue without cookies or retry.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔁 Retry cookies"):
            rerun()
    with c2:
        if st.button("➡️ Continue (no cookies)"):
            st.session_state.allow_cookie_fallback = True
            rerun()
    st.stop()

COOKIE_KEY = "auth"


def _persist_user_to_browser(user_dict: dict):
    if st.session_state.get("allow_cookie_fallback"):
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


# ------------------------- Auth -------------------------
qs = st.query_params


def _force_logout():
    st.session_state.user = None
    try:
        _forget_persisted_user_in_browser()
    except Exception:
        pass
    st.success("Logged out.")
    rerun()


if "logout" in qs:
    _force_logout()

if "user" not in st.session_state:
    st.session_state.user = None

# Restore persisted session
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

# Login / Register / Reset (compact)
if st.session_state.user is None:
    st.title("🔐 Login to Real Balls Logistics Management")

    mode = (
        st.segmented_control("", options=["Login", "Register", "Reset"], default="Login", key="auth_mode")
        if hasattr(st, "segmented_control")
        else st.radio("", ["Login", "Register", "Reset"], horizontal=True)
    )

    if mode == "Login":

        with st.form("login_form", border=False):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                st.session_state.user = {
                    "localId": user["localId"],
                    "idToken": user["idToken"],
                    "refreshToken": user["refreshToken"],
                    "email": email,
                }
                _persist_user_to_browser(st.session_state.user)
                rerun()
            except Exception as e:
                st.error("❌ " + str(e))

    elif mode == "Register":
        with st.form("register_form", border=False):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
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
                        "email": email,
                    }
                    _persist_user_to_browser(st.session_state.user)
                    rerun()
                except Exception as e:
                    st.error("❌ " + str(e))
    else:  # Reset
        with st.form("reset_form", border=False):
            reset_email = st.text_input("Email to reset")
            submitted = st.form_submit_button("Send Reset Email", use_container_width=True)
        if submitted:
            try:
                auth.send_password_reset_email(reset_email)
                st.success("Email sent.")
            except Exception as e:
                st.error("❌ " + str(e))

    st.stop()


# ------------------------- Authenticated -------------------------
# Account bar: "Logged in: email" (no parentheses) + wide Logout button

def render_account_bar(email: str | None):
    st.markdown(
        f'''<div class="account-row"><div class="email">Logged in: {email or "—"}</div><a class="logout-link" href="?logout=1">Logout</a></div>''',
        unsafe_allow_html=True)


if st.session_state.get("allow_cookie_fallback"):
    st.caption("Cookie fallback: you'll stay signed in until you close this tab.")


# ------------------------- Session Init -------------------------

def init_session():
    defaults = {
        "trip_reset": 0,
        "exp_reset": 0,
        "earn_reset": 0,
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
        "earnings": [],
        "pending_changes": False,
        # input buffers for Trip form
        "mileage": "",
        "gallons": "",
        "fuel_cost": "",
        # log-page editing index
        "log_edit_expense_index": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ------------------------- Persistence -------------------------
def _to_float(s: str):
    try:
        return float(str(s or "").replace(",", ".").strip())
    except Exception:
        return None


def save_data():
    uid = st.session_state.user['localId']
    data = {k: st.session_state[k] for k in [
        "baseline", "last_mileage", "total_miles", "total_cost", "total_gallons",
        "last_trip_summary", "log", "expenses", "earnings"
    ]}
    db.child("users").child(uid).set(data, st.session_state.user['idToken'])


def load_data():
    uid = st.session_state.user['localId']
    try:
        data = db.child("users").child(uid).get(st.session_state.user['idToken']).val()
        if data:
            for k, v in data.items():
                st.session_state[k] = v
    except Exception:
        pass


if "initialized" not in st.session_state:
    st.session_state.initialized = True
    load_data()

if st.session_state.get("pending_changes"):
    save_data()
    st.session_state.pending_changes = False

# ------------------------- Navigation (compact) -------------------------
NAV = [
    ("mileage", "⛽ Fuel"),
    ("expenses", "💸 Expenses"),
    ("earnings", "💰 Income"),
    ("log", "📜 Log"),
    ("upload", "📁 Files"),
    ("settings", "⚙️ Settings"),
]

# Radio-based nav (robust on iPhone). Renders as a 3×2 grid via CSS.
NAV_KEYS = [k for k, _ in NAV]
NAV_LABELS = {k: v for k, v in NAV}

# Style the radio as a 3×2 button grid and highlight the active choice
st.markdown(
    '''
    <style>
      [data-testid="stRadio"] > label{ display:none !important; }
      [data-testid="stRadio"] [role="radiogroup"]{
        display:grid !important;
        grid-template-columns: repeat(3, 1fr) !important;
        gap:.4rem !important;
      }
      [data-testid="stRadio"] label{
        border:1px solid #e5e7eb; border-radius:.8rem; padding:.6rem .7rem; min-height:44px;
        display:flex; align-items:center; justify-content:center; text-align:center; margin:0 !important;
        background:#fff; color:inherit;
      }
      [data-testid="stRadio"] input{ position:absolute; opacity:0; width:0; height:0; }
      [data-testid="stRadio"] label:has(input:checked){
        background:#2563eb; color:#fff; border-color:#2563eb;
      }
      @media (prefers-color-scheme: dark){
        [data-testid="stRadio"] label{ background:#111827; border-color:#374151; color:#e5e7eb; }
        [data-testid="stRadio"] label:has(input:checked){ background:#3b82f6; border-color:#3b82f6; color:#fff; }
      }
    </style>
    '''
    ,
    unsafe_allow_html=True,
)

# Keep the radio in sync with session_state.page
if "nav_page_sel" not in st.session_state:
    st.session_state.nav_page_sel = st.session_state.page if st.session_state.page in NAV_KEYS else NAV_KEYS[0]


def _on_nav_change():
    st.session_state.page = st.session_state.nav_page_sel


st.title("🚛 Real Balls Logistics Management")

st.radio(
    label="",
    options=NAV_KEYS,
    format_func=lambda k: NAV_LABELS[k],
    index=NAV_KEYS.index(st.session_state.nav_page_sel) if st.session_state.nav_page_sel in NAV_KEYS else 0,
    horizontal=False,
    label_visibility="collapsed",
    key="nav_page_sel",
    on_change=_on_nav_change,
)

page = st.session_state.page

# ------------------------- PAGE: Mileage (Fuel) -------------------------
if page == "mileage":
    # ---- Dashboard (Fuel page: top tiles) ----
    # Last-trip gallons
    last_trip_gallons = 0.0
    if st.session_state.get("last_trip_summary"):
        last_trip_gallons = float(st.session_state["last_trip_summary"].get("gallons", 0.0) or 0.0)

    # Most recent Fuel expense (as "last trip's" fuel cost)
    last_fuel_cost = 0.0
    if st.session_state.get("expenses"):
        for _e in sorted(
                st.session_state.expenses,
                key=lambda x: (x.get("date", ""), x.get("id", 0)),
                reverse=True,
        ):
            if _e.get("type") == "Fuel":
                last_fuel_cost = float(_e.get("amount", 0.0) or 0.0)
                break

    # Owner / Worker totals and Owner's net
    total_worker_income = sum(float(e.get("worker", 0.0) or 0.0) for e in st.session_state.earnings)
    total_owner_gross = sum(float(e.get("owner", 0.0) or 0.0) for e in st.session_state.earnings)
    total_expenses_amt = sum(float(e.get("amount", 0.0) or 0.0) for e in st.session_state.expenses)
    total_owner_net = total_owner_gross - total_expenses_amt

    st.markdown(f"""
    <div class="metric-grid">
      <div class="metric"><div class="metric-label">Total Miles</div><div class="metric-value">{st.session_state.total_miles:.2f} mi</div></div>
      <div class="metric"><div class="metric-label">Fuel Used (last)</div><div class="metric-value">{last_trip_gallons:.2f} gal</div></div>
      <div class="metric"><div class="metric-label">Fuel Cost (last)</div><div class="metric-value">${last_fuel_cost:.2f}</div></div>
      <div class="metric"><div class="metric-label">Owner's gross</div><div class="metric-value">${total_owner_gross:.2f}</div></div>
      <div class="metric"><div class="metric-label">Worker</div><div class="metric-value">${total_worker_income:.2f}</div></div>
      <div class="metric"><div class="metric-label">Owner's net</div><div class="metric-value">${total_owner_net:.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        """
        <style>
          .metric-grid{
            display:grid;
            grid-template-columns:repeat(3,1fr);  /* 3 columns now */
            gap:.5rem;
          }
          .metric{
            border:1px solid var(--border-color, #e5e7eb);
            border-radius:.6rem;
            padding:.55rem .7rem;
            background: var(--metric-bg, #ffffff);
          }
          .metric-label{ font-size:.78rem; opacity:.75; margin-bottom:.15rem; }
          .metric-value{ font-size:1.05rem; font-weight:600; }
          @media (prefers-color-scheme: dark){
            .metric{ background:#0b1220; border-color:#2a3342; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---- Baseline & Trip ----
    st.subheader("📍 Baseline & Trip")

    # default so names always exist
    odometer_str = ""
    gallons_str = ""

    if st.session_state.baseline is None:
        # --- Baseline input only ---
        def _save_baseline_from_input():
            val = _to_float(st.session_state.get("baseline_input", ""))
            if val and val > 0:
                st.session_state.baseline = val
                st.session_state.last_mileage = val
                st.session_state.pending_changes = True
                st.session_state["baseline_input"] = ""
                st.session_state.trip_reset += 1
                rerun()


        st.text_input("Starting mileage (baseline)",
                      key="baseline_input",
                      placeholder="",
                      value=st.session_state.get("baseline_input", ""),
                      on_change=_save_baseline_from_input)
        if st.button("✅ Save Baseline", use_container_width=True):
            _save_baseline_from_input()


    else:

        # --- Show Baseline & Current odometer ---

        bc1, bc2 = st.columns(2, gap="small")

        with bc1:

            st.caption(f"Baseline: **{st.session_state.baseline:,.2f}**")

        with bc2:

            cur = st.session_state.last_mileage

            st.caption(f"Current: **{(cur if cur is not None else 0):,.2f}**")

        # --- Trip inputs ---

        c1, c2 = st.columns(2, gap="small")

        with c1:

            odometer_str = st.text_input("Odometer", placeholder="", key=f"mileage_{st.session_state.trip_reset}")

        with c2:

            gallons_str = st.text_input("Gallons", placeholder="", key=f"gallons_{st.session_state.trip_reset}")

        new_mileage = _to_float(odometer_str)
        gallons = _to_float(gallons_str)

        is_valid = True
        if new_mileage is None or gallons is None:
            is_valid = False
        elif st.session_state.last_mileage is None:
            is_valid = False
        elif new_mileage <= (st.session_state.last_mileage or 0):
            st.warning("Odometer must increase.")
            is_valid = False

        confirm_click = st.button("✅ Confirm Trip", disabled=not is_valid, use_container_width=True)

        if confirm_click:
            distance = new_mileage - st.session_state.last_mileage
            if distance <= 0:
                st.error("Trip distance is zero. Enter a higher odometer value.")
            else:
                mpg = distance / gallons if gallons and gallons > 0 else 0
                st.session_state.total_miles += distance
                st.session_state.total_gallons += (gallons or 0)
                st.session_state.last_mileage = new_mileage

                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Trip",
                    "distance": distance,
                    "gallons": gallons or 0,
                    "mpg": mpg,
                    "note": "Mileage + Fuel",
                }
                st.session_state.log.append(entry)
                st.session_state.last_trip_summary = entry
                st.session_state.pending_changes = True
                st.session_state.trip_reset += 1
                rerun()

        if st.session_state.last_trip_summary:
            e = st.session_state.last_trip_summary
            total_mi = float(st.session_state.total_miles or 0)
            total_gal = float(st.session_state.total_gallons or 0)
            overall_mpg = (total_mi / total_gal) if total_gal > 0 else 0.0

            col1, col2 = st.columns(2, gap="small")
            with col1:
                st.markdown("**🧶 Last Trip**")
                st.write(f"Distance: {e['distance']:.2f} mi")
                st.write(f"Gallons: {e['gallons']:.2f} gal")
                st.write(f"MPG: {e['mpg']:.2f}")
            with col2:
                st.markdown("**🗂️ All Trips**")
                st.write(f"Miles: {total_mi:.2f}")
                st.write(f"Gallons: {total_gal:.2f}")
                st.write(f"MPG: {overall_mpg:.2f}")



# ------------------------- PAGE: Expenses -------------------------
elif page == "expenses":
    st.subheader("💸 Expenses")

    # --- Add (or edit) form ---
    options = ["Fuel", "Repair", "Certificates", "Insurance", "Trailer Rent", "IFTA", "Reefer Fuel", "Other"]
    today = datetime.now().strftime("%Y-%m-%d")

    if st.session_state.edit_expense_index is None:
        c1, c2 = st.columns([.6, .4], gap="small")
        with c1:
            expense_type = st.selectbox("Type", options, index=0, key="new_expense_type")
            description = st.text_input("Description", key=f"new_expense_description_{st.session_state.exp_reset}",
                                        placeholder="")
        with c2:
            amount_str = st.text_input("Amount $", key=f"new_expense_amount_str_{st.session_state.exp_reset}",
                                       placeholder="")
        # parse & validate like Fuel page
        amount = _to_float(amount_str)
        add_disabled = (amount is None) or (amount < 0)

        if st.button("✅ Confirm", use_container_width=True, disabled=add_disabled):
            exp_id = int(datetime.now().timestamp() * 1000)
            exp = {"id": exp_id, "date": today, "type": expense_type,
                   "description": description, "amount": amount or 0.0}
            st.session_state.expenses.append(exp)
            st.session_state.log.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "Expense", "amount": amount or 0.0,
                "note": f"{expense_type}: {description}", "expense_id": exp_id
            })
            st.session_state.pending_changes = True
            # clear inputs like Fuel page
            st.session_state.exp_reset += 1  # rebuilds inputs blank
            rerun()


    else:
        # If user navigated here while editing (e.g., started from Log)
        idx = st.session_state.edit_expense_index
        if idx is not None and 0 <= idx < len(st.session_state.expenses):
            exp = st.session_state.expenses[idx]
            st.info(f"Editing {exp.get('date', today)}")
            new_type = st.selectbox("Type", options,
                                    index=options.index(exp.get("type", "Other")) if exp.get("type") in options else 0)
            new_desc = st.text_input("Description", value=exp.get("description", ""))
            new_amt = st.number_input("Amount $", min_value=0.0, step=0.01, value=float(exp.get("amount", 0.0)))
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("💾 Save", use_container_width=True):
                    # preserve id & date
                    exp_id = exp.get("id")
                    st.session_state.expenses[idx] = {"id": exp_id, "date": exp.get("date", today), "type": new_type,
                                                      "description": new_desc, "amount": new_amt}
                    # update linked log entry if exists
                    if exp_id:
                        for le in reversed(st.session_state.log):
                            if le.get("type") == "Expense" and le.get("expense_id") == exp_id:
                                le["amount"] = new_amt
                                le["note"] = f"{new_type}: {new_desc}"
                                break
                    st.session_state.edit_expense_index = None
                    st.session_state.pending_changes = True
                    rerun()
            with c2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.edit_expense_index = None
                    rerun()

    # --- Statistics (ONLY Expenses by Category), placed below +Add ---
    st.markdown("### 📊 Statistics")
    if st.session_state.expenses:
        df_exp = pd.DataFrame(st.session_state.expenses)
        # guard for legacy entries without amount/type
        if not df_exp.empty and set(["type", "amount"]).issubset(df_exp.columns):
            df_grp = df_exp.groupby("type")["amount"].sum().reset_index()
            st.altair_chart(
                alt.Chart(df_grp).mark_arc().encode(theta="amount", color="type",
                                                    tooltip=["type", "amount"]).properties(title="Expenses by Category",
                                                                                           height=180),
                use_container_width=True,
            )
        total_expense_amount = float(df_exp.get("amount", pd.Series(dtype=float)).sum())
        st.markdown(f"**Total:** ${total_expense_amount:.2f}")

        # --- Recent → Older expense table (Cost / Type / Date) ---
        st.markdown("### 📋 Recent Expenses")  # ← Make sure this says “Recent”, not “Resent”

        if st.session_state.expenses:
            entries = sorted(
                st.session_state.expenses,
                key=lambda e: (e.get("date", ""), e.get("id", 0)),
                reverse=True,
            )

            df_recent = pd.DataFrame(entries)[["amount", "type", "date"]]
            df_recent = df_recent.rename(columns={"amount": "Cost", "type": "Type", "date": "Date"})

            # SHOW ONLY TOP 20 (newest first)
            df_recent = df_recent.head(20)

            # Format cost column as currency
            df_recent["Cost"] = df_recent["Cost"].map(lambda x: f"${x:,.2f}")

            # Reset index to remove 0,1,2...
            df_recent = df_recent.reset_index(drop=True)

            st.table(df_recent.style.hide(axis="index"))
        else:
            st.caption("No expenses yet.")




    else:
        st.info("No expenses yet.")

# ------------------------- PAGE: Earnings -------------------------
elif page == "earnings":
    st.subheader("💰 Income")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        worker_str = st.text_input("Worker's $", key=f"earn_worker_str_{st.session_state.earn_reset}", placeholder="")
    with c2:
        owner_str = st.text_input("Owner's gross $", key=f"earn_owner_str_{st.session_state.earn_reset}", placeholder="")

    worker = _to_float(worker_str)
    owner = _to_float(owner_str)

    today = datetime.now().strftime("%Y-%m-%d")
    total_expenses = sum(e.get("amount", 0.0) for e in st.session_state.expenses)
    owner_net = (owner or 0.0) - total_expenses

    confirm_disabled = (
            worker is None or owner is None or worker < 0 or owner < 0
    )

    if st.button("✅ Confirm", use_container_width=True, disabled=confirm_disabled):
        earning = {"date": today, "worker": worker or 0.0, "owner": owner or 0.0, "net_owner": owner_net}
        st.session_state.earnings.append(earning)
        st.session_state.log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "Income",
            "amount": owner or 0.0,
            "note": f"Worker ${(worker or 0.0):.2f}, Owner Net ${owner_net:.2f}",
        })
        st.session_state.pending_changes = True
        st.session_state.earn_reset += 1
        rerun()

    if st.session_state.earnings:
        # Sort newest first (by date string)
        entries = sorted(st.session_state.earnings, key=lambda e: e.get("date", ""), reverse=True)
        df = pd.DataFrame(entries)

        # Always recompute Owner's net using CURRENT total expenses
        current_total_expenses = sum(float(e.get("amount", 0.0) or 0.0) for e in st.session_state.expenses)
        df["owner"] = pd.to_numeric(df["owner"], errors="coerce").fillna(0.0)
        df["worker"] = pd.to_numeric(df["worker"], errors="coerce").fillna(0.0)
        df["net_owner"] = df["owner"] - float(current_total_expenses)

        st.markdown("### 📋 Recent Income")  # ← Title

        # Build display table: Worker's | Owner's gross | Owner's net | Date
        df_recent = df[["worker", "owner", "net_owner", "date"]].copy()
        df_recent = df_recent.rename(columns={
            "worker": "Worker",
            "owner": "Owner's gross",
            "net_owner": "Owner's net",
            "date": "Date",
        })

        # SHOW ONLY TOP 20 (newest first)
        df_recent = df_recent.head(20)

        # Ensure numeric then format as currency for the three money columns (guarded)
        for col in ["Worker", "Owner's gross", "Owner's net"]:
            if col in df_recent.columns:
                df_recent[col] = pd.to_numeric(df_recent[col], errors="coerce").fillna(0.0)
                df_recent[col] = df_recent[col].map(lambda x: f"${x:,.2f}")

        # Reset index and render without the index column
        df_recent = df_recent.reset_index(drop=True)
        st.table(df_recent.style.hide(axis="index"))

        # CSV (all rows, raw numbers)
        df_csv = df[["worker", "owner", "net_owner", "date"]]
        csv = df_csv.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "income.csv", "text/csv", use_container_width=True)

        # Totals (all rows)
        st.caption(
            f"Totals — Worker: ${df['worker'].sum():.2f} | Owner's gross: ${df['owner'].sum():.2f} | Owner's net: ${df['net_owner'].sum():.2f}"
        )
    else:
        st.info("No income yet.")



# ------------------------- PAGE: Log -------------------------
elif page == "log":
    st.subheader("📜 Log")


    # Helper: delete expense along with its linked log record if present
    def _delete_expense_at(idx: int):
        if 0 <= idx < len(st.session_state.expenses):
            exp = st.session_state.expenses[idx]
            exp_id = exp.get("id")
            # remove expense
            del st.session_state.expenses[idx]
            # remove matching log entry (prefer by id; otherwise best-effort by note+amount)
            for j in range(len(st.session_state.log) - 1, -1, -1):
                le = st.session_state.log[j]
                if le.get("type") == "Expense":
                    if (exp_id and le.get("expense_id") == exp_id) or (
                            le.get("amount") == exp.get("amount") and le.get(
                        "note") == f"{exp.get('type')}: {exp.get('description')}"):
                        del st.session_state.log[j]
                        break
            st.session_state.pending_changes = True


    # --- Timeline for Trips & Income (exclude Expenses to avoid duplication) ---
    if st.session_state.log:
        st.markdown("### 🕒 Timeline (Trips & Income)")
        timeline = [e for e in st.session_state.log if e.get("type") != "Expense"]
        if timeline:
            for entry in reversed(timeline):
                if entry.get("type") == "Trip":
                    st.write(
                        f"🕒 {entry['timestamp']} — 🚛 Trip: {entry['distance']:.2f} mi, "
                        f"{entry['gallons']:.2f} gal, {entry['mpg']:.2f} MPG"
                    )

                else:
                    st.write(
                        f"🕒 {entry['timestamp']} — {entry.get('type')}: ${entry.get('amount', 0.0):.2f} ({entry.get('note', '')})")
        else:
            st.caption("No trip/income events yet.")
    else:
        st.info("Empty log.")

    st.markdown("---")
    # --- Expenses management now lives here (edit/delete mechanics moved from Expenses page) ---
    st.markdown("### 💸 Expenses — edit here")
    if st.session_state.expenses:
        for i, entry in enumerate(reversed(st.session_state.expenses)):
            idx = len(st.session_state.expenses) - 1 - i
            label = f"{entry.get('date', '')} – ${entry.get('amount', 0.0):.2f} – {entry.get('type', '')} ({entry.get('description', '')})"
            c1, c2, c3 = st.columns([0.75, 0.125, 0.125], gap="small")
            with c1:
                st.write(label)
            with c2:
                if st.button("✏️", key=f"log_edit_expense_{i}"):
                    st.session_state.log_edit_expense_index = idx
                    st.session_state.edit_expense_index = None  # avoid conflicts
                    rerun()
            with c3:
                if st.button("🗑", key=f"log_del_expense_{i}"):
                    _delete_expense_at(idx)
                    rerun()

            # Inline editor under the row
            if st.session_state.get("log_edit_expense_index") == idx:
                with st.container(border=True):
                    opts = ["Fuel", "Repair", "Certificates", "Insurance", "Trailer Rent", "IFTA", "Reefer Fuel",
                            "Other"]
                    new_type = st.selectbox("Type", opts, index=opts.index(entry.get("type", "Other")) if entry.get(
                        "type") in opts else 0, key=f"log_edit_type_{i}")
                    new_desc = st.text_input("Description", value=entry.get("description", ""),
                                             key=f"log_edit_desc_{i}")
                    new_amt = st.number_input("Amount $", min_value=0.0, step=0.01,
                                              value=float(entry.get("amount", 0.0)), key=f"log_edit_amt_{i}")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("💾 Save", key=f"log_save_{i}", use_container_width=True):
                            exp = st.session_state.expenses[idx]
                            exp_id = exp.get("id")
                            st.session_state.expenses[idx] = {"id": exp_id, "date": entry.get("date"), "type": new_type,
                                                              "description": new_desc, "amount": new_amt}
                            # update linked log entry
                            if exp_id:
                                for le in reversed(st.session_state.log):
                                    if le.get("type") == "Expense" and le.get("expense_id") == exp_id:
                                        le["amount"] = new_amt
                                        le["note"] = f"{new_type}: {new_desc}"
                                        break
                            st.session_state.log_edit_expense_index = None
                            st.session_state.pending_changes = True
                            rerun()
                    with cc2:
                        if st.button("❌ Cancel", key=f"log_cancel_{i}", use_container_width=True):
                            st.session_state.log_edit_expense_index = None
                            rerun()
    else:
        st.caption("No expenses yet — add some on the Expenses page.")

# ------------------------- PAGE: Upload -------------------------
elif page == "upload":
    st.subheader("📁 Upload Files")
    files = st.file_uploader("Select file(s)", accept_multiple_files=True)
    if files:
        for f in files:
            st.success(f"Uploaded: {f.name}")

# ------------------------- PAGE: Settings -------------------------
elif page == "settings":
    st.subheader("⚙️ Settings")

    render_account_bar(st.session_state.user.get('email'))

    # inside the "settings" page, under render_account_bar(...)
    if st.button("🔄 Force reload from cloud", use_container_width=True):
        try:
            load_data()
            st.success("Data reloaded from Firebase.")
            rerun()
        except Exception as e:
            st.error(f"Reload failed: {e}")

    if st.session_state.get("allow_cookie_fallback"):
        if st.button("Try enabling cookies again", use_container_width=True):
            st.session_state.allow_cookie_fallback = False
            rerun()

    st.divider()
    if "reset_requested" not in st.session_state:
        st.session_state.reset_requested = False

    if not st.session_state.reset_requested:
        if st.button("❌ Reset App Data", use_container_width=True):
            st.session_state.reset_requested = True
            st.warning("Tap again to confirm. This erases all your saved data.")
    else:
        if st.button("⚠️ Confirm Reset", use_container_width=True):
            try:
                uid = st.session_state.user.get('localId') if st.session_state.get('user') else None
                token = st.session_state.user.get('idToken') if st.session_state.get('user') else None
                # remove data from Firebase (best-effort)
                if uid and token:
                    try:
                        db.child("users").child(uid).remove(token)
                    except Exception:
                        pass
                # reset in-memory state to defaults (preserve auth)
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
                    "earnings": [],
                    "pending_changes": False,
                    "mileage": "",
                    "gallons": "",
                    "fuel_cost": "",
                    "log_edit_expense_index": None,
                    "reset_requested": False,
                }
                for k, v in defaults.items():
                    st.session_state[k] = v
                # persist cleared payload
                if uid and token:
                    try:
                        save_data()
                    except Exception:
                        pass
                st.success("All app data cleared.")
            except Exception as e:
                st.error(f"Reset failed: {e}")
            finally:
                rerun()

    # --------------------- Backup & Restore (Settings only) ---------------------
    st.divider()
    st.markdown("### 📁 Backup & Restore")


    def _export_data_bytes():
        data = {k: st.session_state[k] for k in [
            "baseline", "last_mileage", "total_miles", "total_cost", "total_gallons",
            "last_trip_summary", "log", "expenses", "earnings"
        ]}
        return json.dumps(data, indent=2).encode("utf-8")


    st.download_button(
        label="📥 Download JSON",
        data=_export_data_bytes(),
        file_name="balls_logistics_backup.json",
        mime="application/json",
        use_container_width=True,
    )

    up = st.file_uploader("Upload backup JSON", type="json")
    if up:
        try:
            content = up.read()
            data = json.loads(content)
            for k, v in data.items():
                st.session_state[k] = v
            save_data()
            st.success("Imported & saved.")
        except Exception as e:
            st.error(f"Import failed: {e}")

    # --------------------- Quick Report (Settings only) ---------------------
    st.divider()
    st.markdown("### 📄 Quick Report")


    def _build_quick_report() -> str:
        lines = []
        lines.append("Real Balls Logistics Management — Report")
        lines.append("=====================")
        lines.append(f"Baseline: {st.session_state.baseline}")
        lines.append(f"Current: {st.session_state.last_mileage}")
        lines.append(f"Miles: {st.session_state.total_miles:.2f}")
        lines.append(f"Gallons: {st.session_state.total_gallons:.2f}")
        fuel_total = sum(
            e.get("amount", 0.0)
            for e in st.session_state.expenses
            if e.get("type") == "Fuel"
        )
        lines.append(f"Fuel $: ${fuel_total:.2f}")  # CHANGED
        if st.session_state.total_gallons > 0:
            lines.append(f"Avg MPG: {st.session_state.total_miles / st.session_state.total_gallons:.2f}")
        lines.append("")
        lines.append("Earnings:")
        for e in st.session_state.earnings:
            lines.append(
                f"- {e['date']}: Worker ${e['worker']}, Owner ${e['owner']}, Net ${e.get('net_owner', e['owner']):.2f}")
        return "\n".join(lines)

if page == "settings":
    if st.button("🖨️ Generate Text", use_container_width=True, key="gen_report_settings"):
        txt = _build_quick_report()
        st.text_area("Report", txt, height=260, key="report_txt_settings")
        st.download_button("💾 Download .txt", txt, file_name="balls_logistics_report.txt", use_container_width=True,
                           key="dl_report_settings")

# NOTE: Former Mileage statistics block removed per request.
# Statistics now lives on the Expenses page and shows ONLY "Expenses by Category".
