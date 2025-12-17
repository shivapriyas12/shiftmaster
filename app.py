import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import io

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FCPL Shift Optimizer", layout="wide")

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
    st.title("🏭 FCPL Industrial Shift Optimizer")
with col_logout:
    # Added unique key to prevent duplicate ID error
    if st.button("🔴 Logout", key="main_logout_btn"):
        st.session_state.authorized = False
        st.rerun()

# Added unique key to prevent duplicate ID error
week_start = st.date_input("Select Week Start Date", datetime.now(), key="main_date_picker")
tabs = st.tabs(["📝 Incharge Entry", "📅 Shift Schedule", "🔒 HR Config"])

# --- TAB 1: INCHARGE ENTRY ---
with tabs[0]:
    st.subheader("Employee Registration")
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
                    "ID": eid, "Name": ename, "SPP": spp, "Gender": gender, 
                    "Sec": section, "Desig": desig, "Willing": willing, "Schedule": {}
                })
                st.success(f"Added: {ename}")
            else:
                st.error("Missing Data: ID and Shift preferences are required.")

    if st.session_state.employees:
        st.write("### Current Staff List")
        df_reg = pd.DataFrame(st.session_state.employees)[["ID", "Name", "Sec", "Willing"]]
        st.dataframe(df_reg, use_container_width=True)
        if st.button("🗑️ Clear All Data", key="clear_data_btn"):
            st.session_state.employees = []
            st.rerun()

# --- TAB 2: SCHEDULE GENERATION ---
with tabs[1]:
    if not st.session_state.employees:
        st.info("No employee data found. Please register staff in the first tab.")
    else:
        if st.button("🚀 GENERATE MASTER SCHEDULE", key="gen_schedule_btn"):
            dates = [(week_start + timedelta(days=i)).strftime("%d-%b (%a)") for i in range(7)]
            
            for i, emp in enumerate(st.session_state.employees):
                emp["Schedule"] = {d: "" for d in dates}
                emp["Schedule"][dates[i % 7]] = "W/O"

            for sec_name, rules in st.session_state.line_rules.items():
                sec_staff = [e for e in st.session_state.employees if e["Sec"] == sec_name]
                if not sec_staff: continue

                for idx, day in enumerate(dates):
                    is_sun = "Sun" in day
                    target = rules[4]//3 if is_sun else rules[0] + (rules[3]//3)
                    
                    pool = [e for e in sec_staff if e["Schedule"][day] != "W/O"]
                    random.shuffle(pool)

                    for shift in ["A", "B", "C"]:
                        count = 0
                        for e in pool[:]:
                            if count >= target: break
                            if shift == "A" and idx > 0 and e["Schedule"][dates[idx-1]] == "C": continue
                            if shift in e["Willing"]:
                                e["Schedule"][day] = shift
                                pool.remove(e)
                                count += 1
                    for e in pool:
                        for s in e["Willing"]: e["Schedule"][day] = s; break

            res_list = []
            for e in sorted(st.session_state.employees, key=lambda x: x['Sec']):
                row = {"Section": e["Sec"], "ID": e["ID"], "Name": e["Name"]}
                row.update(e["Schedule"])
                res_list.append(row)
            
            df_final = pd.DataFrame(res_list)
            st.dataframe(df_final, use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False)
            st.download_button("📥 Download Excel Report", output.getvalue(), f"Shift_Report_{week_start}.xlsx", key="dl_btn")

# --- TAB 3: HR CONFIGURATION ---
with tabs[2]:
    st.subheader("Requirement Rules Management")
    hr_p = st.text_input("Enter HR Password to unlock", type="password", key="hr_pass_input")
    if hr_p == HR_PASS:
        st.success("Access Granted")
        rules_df = pd.DataFrame.from_dict(st.session_state.line_rules, orient='index', 
                                          columns=["A", "B", "C", "AB Cover", "Sunday"])
        edited_df = st.data_editor(rules_df, key="rules_editor")
        if st.button("Save Changes", key="save_rules_btn"):
            st.session_state.line_rules = edited_df.to_dict('list')
            st.success("System Rules Updated!")
    elif hr_p != "":
        st.error("Incorrect HR Password")
