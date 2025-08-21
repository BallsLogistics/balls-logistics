# streamlit_app.py — iPhone-optimized (compact, responsive)
import json
from datetime import datetime
from io import StringIO

import altair as alt
import pandas as pd
import streamlit as st
from firebase_config import auth, db, firebase_app  # uses @st.cache_resource inside
from streamlit_cookies_manager import EncryptedCookieManager

# ------------------------- Page & Global Styles -------------------------
st.set_page_config(
    page_title="🚛 Balls Logistics",
    page_icon="🚛",
    layout="wide",  # use full width; we'll constrain with CSS
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      /* Base scale down; tighten paddings; mobile-first tweaks */
      :root { --scale: .90; }
      html, body, [data-testid="stAppViewContainer"] { font-size: calc(16px * var(--scale)); }

      .block-container { padding: .6rem .6rem 2rem; max-width: 720px; }
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

      /* Inputs: remove number spinners */
      input[type=number]::-webkit-outer-spin-button,
      input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
      input[type=number] { appearance: textfield; }

      /* Headings smaller */
      h1 { font-size: 1.25rem; margin:.5rem 0 .35rem; }
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
    st.title("🔐 Login to Balls Logistics")

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
st.success(f"Logged in: {st.session_state.user.get('email')}")

# Quick logout button (mobile top)
st.button("🚪 Logout", key="logout_main", use_container_width=True, on_click=lambda: (_forget_persisted_user_in_browser(), st.session_state.update(user=None), rerun()))

if st.session_state.get("allow_cookie_fallback"):
    st.caption("Cookie fallback: you'll stay signed in until you close this tab.")

# ------------------------- Session Init -------------------------

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
        "earnings": [],
        "pending_changes": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ------------------------- Persistence -------------------------

def save_data():
    uid = st.session_state.user['localId']
    data = {k: st.session_state[k] for k in [
        "baseline","last_mileage","total_miles","total_cost","total_gallons",
        "last_trip_summary","log","expenses","earnings"
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

# ------------------------- Dashboard (compact) -------------------------
st.markdown("### 🌐 Dashboard")

# Compute totals once
total_exp = sum(e.get("amount", 0.0) for e in st.session_state.expenses)
total_earn = sum(e.get("owner", 0.0) for e in st.session_state.earnings)
net_income = total_earn - total_exp

# Strict 2×2 metrics grid using pure HTML (won't stack on iPhone)
st.markdown(f"""
<div class="metric-grid">
  <div class="metric"><div class="metric-label">Total Miles</div><div class="metric-value">{st.session_state.total_miles:.2f} mi</div></div>
  <div class="metric"><div class="metric-label">Fuel Used</div><div class="metric-value">{st.session_state.total_gallons:.2f} gal</div></div>
  <div class="metric"><div class="metric-label">Fuel Cost</div><div class="metric-value">${st.session_state.total_cost:.2f}</div></div>
  <div class="metric"><div class="metric-label">Owner Earnings</div><div class="metric-value">${total_earn:.2f}</div></div>
</div>
""", unsafe_allow_html=True)

st.caption(f"Net (Owner − Expenses): ${net_income:.2f}")

st.markdown("""
<style>
  .metric-grid{ display:grid; grid-template-columns:repeat(2,1fr); gap:.5rem; }
  .metric{ border:1px solid var(--border-color, #e5e7eb); border-radius:.6rem; padding:.55rem .7rem; background: var(--metric-bg, #ffffff); }
  .metric-label{ font-size:.78rem; opacity:.75; margin-bottom:.15rem; }
  .metric-value{ font-size:1.05rem; font-weight:600; }
  @media (prefers-color-scheme: dark){
    .metric{ background:#0b1220; border-color:#2a3342; }
  }
</style>
""", unsafe_allow_html=True)

with st.expander("📁 Backup & Restore", expanded=False):
    def export_data():
        data = {k: st.session_state[k] for k in [
            "baseline","last_mileage","total_miles","total_cost","total_gallons",
            "last_trip_summary","log","expenses","earnings"
        ]}
        return json.dumps(data, indent=2).encode("utf-8")

    st.download_button(
        label="📥 Download JSON",
        data=export_data(),
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

# ------------------------- Navigation (compact) -------------------------
NAV = [
    ("mileage", "⛽ Fuel"),
    ("expenses", "💸 Expenses"),
    ("earnings", "💰 Income"),
    ("log", "📜 Log"),
    ("upload", "📁 Files"),
    ("settings", "⚙️ Settings"),
]

# 3×2 grid of page buttons (3 columns × 2 rows) — column-based (robust on iPhone)
st.markdown("""
<style>
  .nav-3x2 .stButton button:disabled {
    background:#2563eb !important; color:#fff !important; border-color:#2563eb !important; opacity:1 !important;
  }
  .nav-3x2 .stButton button:disabled:focus { outline:none; box-shadow:0 0 0 3px rgba(37,99,235,.35) !important; }
  .nav-3x2 .stButton button:not(:disabled){ background:#fff; border:1px solid #e5e7eb; }
  @media (prefers-color-scheme: dark){
    .nav-3x2 .stButton button:not(:disabled){ background:#111827; border-color:#374151; color:#e5e7eb; }
    .nav-3x2 .stButton button:disabled{ background:#3b82f6 !important; border-color:#3b82f6 !important; color:#fff !important; }
  }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="nav-3x2">', unsafe_allow_html=True)
# Row 1
c1, c2, c3 = st.columns(3, gap="small")
for (k, label), col in zip(NAV[0:3], (c1, c2, c3)):
    with col:
        active = (st.session_state.page == k)
        if st.button(label, key=f"nav_{k}", use_container_width=True, disabled=active):
            st.session_state.page = k
# Row 2
c4, c5, c6 = st.columns(3, gap="small")
for (k, label), col in zip(NAV[3:6], (c4, c5, c6)):
    with col:
        active = (st.session_state.page == k)
        if st.button(label, key=f"nav_{k}", use_container_width=True, disabled=active):
            st.session_state.page = k
st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.page
st.title("🚛 Balls Logistics")

# ------------------------- PAGE: Mileage -------------------------
if page == "mileage":
    st.subheader("📍 Baseline & Trip")

    if st.session_state.baseline is None:
        base = st.number_input("Starting mileage (baseline)", min_value=0.0, step=0.1, placeholder="e.g., 150000")
        if st.button("✅ Save Baseline", disabled=base <= 0, use_container_width=True):
            st.session_state.baseline = base
            st.session_state.last_mileage = base
            st.session_state.pending_changes = True
            rerun()
    else:
        c1, c2 = st.columns(2, gap="small")
        with c1:
            st.caption(f"Baseline: **{st.session_state.baseline}**")
        with c2:
            st.caption(f"Current: **{st.session_state.last_mileage}**")

    st.markdown("**Enter Trip Data**")
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        new_mileage = st.number_input("Odometer", min_value=0.0, step=0.1, placeholder="150350", key="mileage")
    with c2:
        gallons = st.number_input("Gallons", min_value=0.0, step=0.1, placeholder="20.5", key="gallons")
    with c3:
        fuel_cost = st.number_input("Fuel $", min_value=0.0, step=0.01, placeholder="85.00", key="fuel_cost")

    is_valid = True
    if st.session_state.baseline is not None and st.session_state.last_mileage is not None:
        if new_mileage <= (st.session_state.last_mileage or 0):
            st.warning("Odometer must increase.")
            is_valid = False

    if st.button("✅ Confirm Trip", disabled=not is_valid, use_container_width=True):
        if st.session_state.last_mileage is None:
            st.error("Set baseline first.")
        else:
            distance = max(0.0, new_mileage - st.session_state.last_mileage)
            if distance <= 0:
                st.error("Trip distance is zero.")
            else:
                mpg = distance / gallons if gallons > 0 else 0
                cpm = fuel_cost / distance if distance > 0 else 0
                st.session_state.total_miles += distance
                st.session_state.total_cost += fuel_cost
                st.session_state.total_gallons += gallons
                st.session_state.last_mileage = new_mileage
                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Trip",
                    "distance": distance,
                    "gallons": gallons,
                    "mpg": mpg,
                    "total_cost": fuel_cost,
                    "cost_per_mile": cpm,
                    "note": "Mileage + Fuel",
                }
                st.session_state.log.append(entry)
                st.session_state.last_trip_summary = entry
                st.session_state.pending_changes = True
                rerun()

    if st.session_state.last_trip_summary:
        e = st.session_state.last_trip_summary
        st.markdown("**🧶 Last Trip**")
        c1, c2 = st.columns(2, gap="small")
        with c1:
            st.write(f"Distance: {e['distance']:.2f} mi")
            st.write(f"Gallons: {e['gallons']:.2f} gal")
            st.write(f"MPG: {e['mpg']:.2f}")
        with c2:
            st.write(f"Fuel $: ${e['total_cost']:.2f}")
            st.write(f"Cost/mi: ${e['cost_per_mile']:.2f}")
        st.markdown("**📈 Overall Since Baseline**")
        c3, c4, c5 = st.columns(3, gap="small")
        with c3:
            st.write(f"Miles: {st.session_state.total_miles:.2f}")
        with c4:
            st.write(f"Gallons: {st.session_state.total_gallons:.2f}")
        with c5:
            overall_cpm = (
                st.session_state.total_cost / st.session_state.total_miles if st.session_state.total_miles > 0 else 0
            )
            st.write(f"$/mi: ${overall_cpm:.2f}")

# ------------------------- PAGE: Expenses -------------------------
elif page == "expenses":
    st.subheader("💸 Expenses")

    options = ["Fuel","Repair","Certificates","Insurance","Trailer Rent","IFTA","Reefer Fuel","Other"]
    today = datetime.now().strftime("%Y-%m-%d")

    if st.session_state.edit_expense_index is None:
        c1, c2 = st.columns([.6, .4], gap="small")
        with c1:
            expense_type = st.selectbox("Type", options, index=0, key="new_expense_type")
            description = st.text_input("Description", key="new_expense_description")
        with c2:
            amount = st.number_input("Amount $", min_value=0.0, step=0.01, key="new_expense_amount")
            if st.button("➕ Add", use_container_width=True):
                exp = {"date": today, "type": expense_type, "description": description, "amount": amount}
                st.session_state.expenses.append(exp)
                st.session_state.log.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Expense","amount": amount, "note": f"{expense_type}: {description}"
                })
                st.session_state.pending_changes = True
                rerun()

    idx = st.session_state.edit_expense_index
    if idx is not None and 0 <= idx < len(st.session_state.expenses):
        exp = st.session_state.expenses[idx]
        st.info(f"Editing {exp['date']}")
        new_type = st.selectbox("Type", options, index=options.index(exp["type"]) if exp["type"] in options else 0)
        new_desc = st.text_input("Description", value=exp["description"])
        new_amt = st.number_input("Amount $", min_value=0.0, step=0.01, value=float(exp["amount"]))
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("💾 Save", use_container_width=True):
                st.session_state.expenses[idx] = {"date": exp["date"], "type": new_type, "description": new_desc, "amount": new_amt}
                st.session_state.edit_expense_index = None
                st.session_state.pending_changes = True
                rerun()
        with c2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.edit_expense_index = None
                rerun()

    if st.session_state.expenses:
        st.markdown("### 📋 Logged")
        for i, entry in enumerate(reversed(st.session_state.expenses)):
            idx = len(st.session_state.expenses) - 1 - i
            label = f"{entry['date']} – ${entry['amount']:.2f} – {entry['type']} ({entry['description']})"
            c1, c2, c3 = st.columns([0.8, 0.1, 0.1], gap="small")
            with c1:
                st.write(label)
            with c2:
                if st.button("✏️", key=f"edit_expense_{i}"):
                    st.session_state.edit_expense_index = idx
                    rerun()
            with c3:
                if st.button("🗑", key=f"del_expense_{i}"):
                    del st.session_state.expenses[idx]
                    st.session_state.pending_changes = True
                    rerun()
    else:
        st.info("No expenses yet.")

    total_expense_amount = sum(e.get("amount",0.0) for e in st.session_state.expenses)
    st.markdown(f"**Total:** ${total_expense_amount:.2f}")

# ------------------------- PAGE: Earnings -------------------------
elif page == "earnings":
    st.subheader("💰 Income")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        worker = st.number_input("Worker $", min_value=0.0, step=0.01)
    with c2:
        owner = st.number_input("Owner $", min_value=0.0, step=0.01)

    today = datetime.now().strftime("%Y-%m-%d")
    total_expenses = sum(e.get("amount", 0.0) for e in st.session_state.expenses)
    owner_net = owner - total_expenses

    if st.button("✅ Confirm", use_container_width=True):
        earning = {"date": today, "worker": worker, "owner": owner, "net_owner": owner_net}
        st.session_state.earnings.append(earning)
        st.session_state.log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "Income", "amount": owner, "note": f"Worker ${worker:.2f}, Owner Net ${owner_net:.2f}"
        })
        st.session_state.pending_changes = True
        rerun()

    if st.session_state.earnings:
        df = pd.DataFrame(st.session_state.earnings)
        if "net_owner" not in df.columns:
            df["net_owner"] = df["owner"] - total_expenses
        st.dataframe(df, use_container_width=True)

        chart = alt.Chart(df).mark_line(point=True).encode(
            x="date:T", y=alt.Y("net_owner:Q", title="Owner Net"), tooltip=["date","net_owner"]
        ).properties(title="Owner Net Over Time", height=160)
        st.altair_chart(chart, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "income.csv", "text/csv", use_container_width=True)

        st.caption(f"Totals — Worker: ${df['worker'].sum():.2f} | Owner: ${df['owner'].sum():.2f} | Net: ${df['net_owner'].sum():.2f}")
    else:
        st.info("No income yet.")

# ------------------------- PAGE: Log -------------------------
elif page == "log":
    st.subheader("📜 Log")
    if st.session_state.log:
        for entry in reversed(st.session_state.log):
            if entry.get("type") == "Trip":
                st.write(
                    f"🕒 {entry['timestamp']} — 🚛 Trip: {entry['distance']:.2f} mi, {entry['mpg']:.2f} MPG, ${entry['total_cost']:.2f}, ${entry['cost_per_mile']:.2f}/mi"
                )
            else:
                st.write(f"🕒 {entry['timestamp']} — {entry.get('type')}: ${entry.get('amount',0.0):.2f} ({entry.get('note','')})")
    else:
        st.info("Empty log.")

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
            st.warning("Tap again to confirm. This erases all data.")
    else:
        if st.button("⚠️ Confirm Reset", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            _forget_persisted_user_in_browser()
            st.markdown("<script>window.location.reload();</script>", unsafe_allow_html=True)

# ------------------------- Statistics (bottom compact block) -------------------------
st.markdown("---")
st.markdown("### 📊 Statistics")
if st.session_state.total_miles > 0 and st.session_state.total_gallons > 0:
    avg_mpg = st.session_state.total_miles / st.session_state.total_gallons
    avg_cpm = st.session_state.total_cost / st.session_state.total_miles if st.session_state.total_miles else 0
    c1, c2 = st.columns(2, gap="small")
    with c1: st.metric("Avg MPG", f"{avg_mpg:.2f}")
    with c2: st.metric("Avg $/mi", f"${avg_cpm:.2f}")

    mpg_data = [
        {"Date": e["timestamp"], "MPG": e["mpg"]}
        for e in st.session_state.log if e.get("type") == "Trip" and e.get("mpg") is not None
    ]
    if mpg_data:
        mpg_df = pd.DataFrame(mpg_data)
        st.altair_chart(
            alt.Chart(mpg_df).mark_line(point=True).encode(x="Date:T", y="MPG:Q").properties(title="MPG per Trip", height=160),
            use_container_width=True,
        )

    if st.session_state.expenses:
        df_exp = pd.DataFrame(st.session_state.expenses)
        df_exp = df_exp.groupby("type")["amount"].sum().reset_index()
        st.altair_chart(
            alt.Chart(df_exp).mark_arc().encode(theta="amount", color="type", tooltip=["type","amount"]).properties(title="Expenses by Category", height=180),
            use_container_width=True,
        )
else:
    st.caption("Add trips to see stats.")

# ------------------------- Report (compact) -------------------------
st.markdown("---")
st.markdown("### 📄 Quick Report")
if st.button("🖨️ Generate Text", use_container_width=True):
    report = StringIO()
    report.write("Balls Logistics Report\n=====================\n")
    report.write(f"Baseline: {st.session_state.baseline}\n")
    report.write(f"Current: {st.session_state.last_mileage}\n")
    report.write(f"Miles: {st.session_state.total_miles:.2f}\n")
    report.write(f"Gallons: {st.session_state.total_gallons:.2f}\n")
    report.write(f"Fuel $: ${st.session_state.total_cost:.2f}\n")
    if st.session_state.total_gallons > 0:
        report.write(f"Avg MPG: {st.session_state.total_miles / st.session_state.total_gallons:.2f}\n")
    if st.session_state.total_miles > 0:
        report.write(f"Avg $/mi: {st.session_state.total_cost / st.session_state.total_miles:.2f}\n")
    report.write("\nEarnings:\n")
    for e in st.session_state.earnings:
        report.write(f"- {e['date']}: Worker ${e['worker']}, Owner ${e['owner']}, Net ${e.get('net_owner', e['owner']):.2f}\n")
    text = report.getvalue()
    st.text_area("Report", text, height=260)
    st.download_button("💾 Download .txt", text, file_name="balls_logistics_report.txt", use_container_width=True)
