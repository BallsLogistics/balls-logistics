import streamlit as st
from datetime import datetime
import pandas as pd
import altair as alt

import streamlit as st

# Set a fixed password (you can move it to st.secrets later)
CORRECT_PASSWORD = st.secrets["login_password"]

# Check login state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# If not logged in, show login form
if not st.session_state.logged_in:
    st.title("🔐 Login Required")
    password = st.text_input("Enter password:", type="password")
    if st.button("Login"):
        if password == CORRECT_PASSWORD:
            st.session_state.logged_in = True
            st.experimental_rerun()  # refresh app after login
        else:
            st.error("Incorrect password")
    st.stop()  # stop app for unauthorized users


st.set_page_config(page_title="🚛 Balls Logistics", layout="centered")

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




