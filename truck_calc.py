# balls_logistics_app.py
import streamlit as st
import os
import json
from datetime import datetime
import pandas as pd
import altair as alt
from io import StringIO

st.set_page_config(page_title="🚛 Balls Logistics", layout="centered")

DATA_FILE = "data.json"

# ----------------------- Persistence Functions -----------------------
def save_data():
    # Save current session state values to a local JSON file for persistence
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
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_data():
    # Load session state from a saved JSON file, if it exists
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        st.session_state.baseline = data.get("baseline")
        st.session_state.last_mileage = data.get("last_mileage")
        st.session_state.total_miles = data.get("total_miles", 0.0)
        st.session_state.total_cost = data.get("total_cost", 0.0)
        st.session_state.total_gallons = data.get("total_gallons", 0.0)
        st.session_state.last_trip_summary = data.get("last_trip_summary", {})
        st.session_state.log = data.get("log", [])
        st.session_state.expenses = data.get("expenses", [])
        st.session_state.earnings = data.get("earnings", [])

# ----------------------- Load on First App Run -----------------------
if "initialized" not in st.session_state:
    # Load existing data only on the first run to avoid overwriting session state
    st.session_state.initialized = True
    load_data()

# ----------------------- Auto-save Logic -----------------------
# Save session state to file only if changes have been marked
if st.session_state.get("pending_changes", False):
    save_data()
    st.session_state.pending_changes = False

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

st.info("✅ Persistent storage system loaded. All changes will be saved to 'data.json'.")

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
    report.write("Balls Logistics Report\n")
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
            justify-content: center;
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

nav_cols = st.columns(6)
nav_buttons = [
    ("⛽\nFuel", "mileage"),
    ("💸\nExpenses", "expenses"),
    ("💰\nIncome", "earnings"),
    ("📜\nData Log", "log"),
    ("📁\nUpload Files", "upload"),
    ("⚙️\nSettings", "settings")
]
for col, (label, page_id) in zip(nav_cols, nav_buttons):
    with col:
        if st.button(label):
            st.session_state.page = page_id

# Default page
page_name = st.session_state.page

st.title("🚛 Balls Logistics Management")

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
                        st.rerun()

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
            st.rerun()

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
                    st.rerun()
            with col2:
                if st.button("❌ Cancel Edit"):
                    st.session_state.edit_expense_index = None
                    st.rerun()
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
                    st.rerun()
            with col3:
                if st.button("🗑", key=f"delete_expense_{i}"):
                    del st.session_state.expenses[idx]
                    st.session_state.pending_changes = True
                    st.success("Expense deleted.")
                    st.rerun()
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

            # Inject JavaScript to reload the browser page
            st.markdown("""
                <script>
                window.location.reload();
                </script>
            """, unsafe_allow_html=True)


