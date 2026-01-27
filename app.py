import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import io

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FCPL ShiftMaster", layout="wide")

# --- 2. SECURITY CREDENTIALS ---
MASTER_USER = "admin"
MASTER_PASS = "fcpl_user@2025"
HR_PASS = "hr@123"

# --- 3. SESSION STATE INITIALIZATION ---
if 'authorized' not in st.session_state:
    st.session_state.authorized = False
if 'employees' not in st.session_state:
    st.session_state.employees = []
if 'line_rules' not in st.session_state:
    st.session_state.line_rules = {
        "Line 1": [30, 30, 30, 9, 15],
        "V60": [20, 20, 20, 6, 10],
        "New Line": [25, 25, 25, 7, 12],
        "Farmlite": [15, 15, 15, 3, 8],
        "FG": [10, 10, 10, 3, 5],
        "Packing Module": [40, 40, 40, 12, 20],
        "Tecon": [12, 12, 12, 3, 6],
        "Combi": [18, 18, 18, 5, 9]
    }

# --- 4. ACCESS CONTROL UI ---
if not st.session_state.authorized:
    st.markdown("<h1 style='text-align: center;'>🔐 FCPL Secure Portal</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_gate"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Access System"):
                if u == MASTER_USER and p == MASTER_PASS:
                    st.session_state.authorized = True
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    st.stop()

# --- 5. MAIN APPLICATION UI ---
col_title, col_logout = st.columns([5, 1])
with col_title:
    st.title("👷🏽🏭 FCPL Shift Schedule Maker")
with col_logout:
    if st.button("🔴 Logout"):
        st.session_state.authorized = False
        st.rerun()

week_start = st.date_input("Select Week Start Date", datetime.now())
tabs = st.tabs(["📝 Incharge Entry", "📅 Shift Schedule", "🔒 HR CONFIGURATION"])

# ------------------------------------------------------------------
# -------------------- TAB 1: INCHARGE ENTRY ------------------------
# ------------------------------------------------------------------
with tabs[0]:
    st.subheader("📤 Bulk Upload Employees (Excel)")

    uploaded_file = st.file_uploader(
        "Upload Employee Excel File",
        type=["xlsx", "xls"],
        help="Columns required: ID, Name, SPP, Gender, Sec, Desig, Willing"
    )

    if uploaded_file is not None:
        try:
            df_upload = pd.read_excel(uploaded_file)
            required_cols = {"ID", "Name", "SPP", "Gender", "Sec", "Desig", "Willing"}

            if not required_cols.issubset(df_upload.columns):
                st.error(f"Excel must contain columns: {required_cols}")
            else:
                existing_ids = {e["ID"] for e in st.session_state.employees}
                added = 0

                for _, row in df_upload.iterrows():
                    willing = [s.strip() for s in str(row["Willing"]).split(",") if s.strip() in ["A", "B", "C"]]

                    if pd.isna(row["ID"]) or not willing or str(row["ID"]) in existing_ids:
                        continue

                    st.session_state.employees.append({
                        "ID": str(row["ID"]),
                        "Name": row["Name"],
                        "SPP": row["SPP"],
                        "Gender": row["Gender"],
                        "Sec": row["Sec"],
                        "Desig": row["Desig"],
                        "Willing": willing,
                        "Schedule": {}
                    })
                    added += 1

                st.success(f"✅ Successfully uploaded {added} employees")

        except Exception as e:
            st.error(f"Error reading Excel: {e}")

    # ---- Manual Entry (Backup / Exception Handling) ----
    st.divider()
    st.subheader("➕ Manual Employee Entry")

    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        spp = c1.text_input("SPP NAME")
        eid = c2.text_input("EMP ID")
        ename = c3.text_input("EMP NAME")

        c4, c5, c6 = st.columns(3)
        gender = c4.selectbox("GENDER", ["F", "M", "Not Defined"])
        section = c5.selectbox("SECTION", list(st.session_state.line_rules.keys()))
        desig = c6.text_input("DESIGNATION")

        st.write("Willing Shifts")
        sc = st.columns(3)
        wa = sc[0].checkbox("Shift A")
        wb = sc[1].checkbox("Shift B")
        wc = sc[2].checkbox("Shift C")

        if st.form_submit_button("Add Employee"):
            willing = [s for s, b in zip(["A", "B", "C"], [wa, wb, wc]) if b]
            if eid and willing:
                st.session_state.employees.append({
                    "ID": eid,
                    "Name": ename,
                    "SPP": spp,
                    "Gender": gender,
                    "Sec": section,
                    "Desig": desig,
                    "Willing": willing,
                    "Schedule": {}
                })
                st.success(f"Added: {ename}")
            else:
                st.error("EMP ID and at least one shift required")

    if st.session_state.employees:
        st.write("### Current Staff List")
        df_reg = pd.DataFrame(st.session_state.employees)[["ID", "Name", "Sec", "Willing"]]
        st.dataframe(df_reg, use_container_width=True)

        if st.button("🗑️ Clear All Data"):
            st.session_state.employees = []
            st.rerun()

# ------------------------------------------------------------------
# -------------------- TAB 2: SCHEDULE ------------------------------
# ------------------------------------------------------------------
with tabs[1]:
    if not st.session_state.employees:
        st.info("No employee data found.")
    else:
        if st.button("🚀 GENERATE SHIFT SCHEDULE"):
            dates = [(week_start + timedelta(days=i)).strftime("%d-%b (%a)") for i in range(7)]

            for i, emp in enumerate(st.session_state.employees):
                emp["Schedule"] = {d: "" for d in dates}
                emp["Schedule"][dates[i % 7]] = "W/O"

            for sec, rules in st.session_state.line_rules.items():
                staff = [e for e in st.session_state.employees if e["Sec"] == sec]
                if not staff:
                    continue

                for idx, day in enumerate(dates):
                    is_sun = "Sun" in day
                    target = rules[4] // 3 if is_sun else rules[0] + (rules[3] // 3)
                    pool = [e for e in staff if e["Schedule"][day] != "W/O"]
                    random.shuffle(pool)

                    for shift in ["A", "B", "C"]:
                        count = 0
                        for e in pool[:]:
                            if count >= target:
                                break
                            if shift == "A" and idx > 0 and e["Schedule"][dates[idx - 1]] == "C":
                                continue
                            if shift in e["Willing"]:
                                e["Schedule"][day] = shift
                                pool.remove(e)
                                count += 1

                    for e in pool:
                        e["Schedule"][day] = e["Willing"][0]

            result = []
            for e in st.session_state.employees:
                row = {"Section": e["Sec"], "ID": e["ID"], "Name": e["Name"]}
                row.update(e["Schedule"])
                result.append(row)

            df_final = pd.DataFrame(result)
            st.dataframe(df_final, use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_final.to_excel(writer, index=False)

            st.download_button(
                "📥 Download Excel Report",
                output.getvalue(),
                f"Shift_Report_{week_start}.xlsx"
            )

# ------------------------------------------------------------------
# -------------------- TAB 3: HR CONFIG -----------------------------
# ------------------------------------------------------------------
with tabs[2]:
    st.subheader("Requirement Rules Management")
    hr_p = st.text_input("Enter HR Password", type="password")

    if hr_p == HR_PASS:
        st.success("Access Granted")
        rules_df = pd.DataFrame.from_dict(
            st.session_state.line_rules,
            orient="index",
            columns=["A", "B", "C", "AB Cover", "Sunday"]
        )
        edited_df = st.data_editor(rules_df)

        if st.button("Save Changes"):
            st.session_state.line_rules = edited_df.to_dict("list")
            st.success("Rules Updated")
    elif hr_p:
        st.error("Incorrect Password")
