import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# ================= 1. ตั้งค่าหน้าเว็บ =================
st.set_page_config(
    page_title="ระบบคัดกรองการได้ยิน (OAE)",
    page_icon="👂",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stAppHeader {background-color: #f0f2f6;}
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        font-weight: bold;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    h1, h2, h3 { color: #2c3e50; font-family: 'Sarabun', sans-serif; }
</style>
""", unsafe_allow_html=True)

# ================= 2. ฟังก์ชันเลือกวันที่ไทย =================
def thai_date_picker(label, key_prefix, default_date=None, start_year_th=None):
    st.write(f"**{label}**")
    c1, c2, c3 = st.columns([1, 1.5, 1])
    
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    
    today = default_date if default_date else date.today()
    current_year_th = today.year + 543
    
    with c1:
        day = st.selectbox("วัน", list(range(1, 32)), index=today.day-1, key=f"{key_prefix}_d", label_visibility="collapsed")
    with c2:
        month_str = st.selectbox("เดือน", thai_months, index=today.month-1, key=f"{key_prefix}_m", label_visibility="collapsed")
    with c3:
        if start_year_th:
            end_year = max(current_year_th, start_year_th) + 2
            year_list = list(range(start_year_th, end_year))
        else:
            year_list = list(range(current_year_th - 100, current_year_th + 5))
            
        try:
            default_idx = year_list.index(current_year_th)
        except ValueError:
            default_idx = 0
            
        year_th = st.selectbox("ปี (พ.ศ.)", year_list, index=default_idx, key=f"{key_prefix}_y", label_visibility="collapsed")

    month_idx = thai_months.index(month_str) + 1
    year_en = year_th - 543
    
    try:
        return date(year_en, month_idx, day)
    except ValueError:
        st.error(f"วันที่ไม่ถูกต้อง")
        return None

# ================= 3. เชื่อมต่อ Google Sheets =================
SHEET_FILENAME = "HearingDB"
CREDENTIALS_FILE = "credentials.json"
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

try:
    if "gcp_json" in st.secrets:
        key_dict = json.loads(st.secrets["gcp_json"])
        creds = Credentials.from_service_account_info(key_dict, scopes=scope)
    else:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"❌ เชื่อมต่อไม่ได้: {e}")
    st.stop()

def init_connection():
    try:
        sh = client.open(SHEET_FILENAME)
        worksheet = sh.sheet1
        if not worksheet.get_values("A1"):
            headers = [
                "Timestamp", "HN", "CitizenID", "Name", "Gender", 
                "DOB", "VisitNo", "Dept", "RightEar", "LeftEar", 
                "Summary", "ApptDate", "Recorder"
            ]
            worksheet.append_row(headers)
        return worksheet
    except Exception as e:
        st.error(f"Error init connection: {e}")
        st.stop()

def load_data(worksheet):
    try:
        data = worksheet.get_all_values()
        if len(data) < 2: return pd.DataFrame(columns=data[0])
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

# ================= 4. ส่วนแสดงผล =================
st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%); border-radius: 15px; margin-bottom: 20px;">
        <h1 style="color: white; margin:0;">👂 ระบบคัดกรองการได้ยิน (OAE)</h1>
        <p style="color: white; font-size: 1.2em;">โรงพยาบาลแพร่</p>
    </div>
""", unsafe_allow_html=True)

ws = init_connection()
df = load_data(ws)

tab1, tab2 = st.tabs(["📝 บันทึกผลตรวจ", "📊 แดชบอร์ดสรุปผล"])

with tab1:
    with st.container():
        st.markdown("### 👤 ข้อมูลผู้ป่วย")
        with st.form("entry_form", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)
            with c1: hn = st.text_input("HN *", placeholder="ระบุ HN").strip()
            with c2: citizen = st.text_input("เลขบัตรประชาชน (13 หลัก) *").strip()
            with c3: name = st.text_input("ชื่อ-นามสกุล *")

            c4, c5 = st.columns(2)
            with c4: dob = thai_date_picker("วันเกิด (ด/ว/ป)", "dob_picker", start_year_th=2567)
            with c5: gender = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True)

            st.markdown("---")
            st.markdown("### 🏥 ผลการตรวจ")
            c6, c7, c8 = st.columns(3)
            with c6: visit = st.selectbox("ตรวจครั้งที่", ["1", "2", "3", "4"])
            with c7: dept = st.selectbox("แผนกที่ตรวจ", ["NICU/Nursery", "หลังคลอด", "หูคอจมูก"])
            with c8: recorder = st.text_input("ผู้บันทึก *")

            c9, c10 = st.columns(2)
            with c9: right = st.selectbox("👂 หูขวา", ["ผ่าน", "ไม่ผ่าน"])
            with c10: left = st.selectbox("👂 หูซ้าย", ["ผ่าน", "ไม่ผ่าน"])

            st.markdown("#### 📋 สรุปผลการตรวจ")
            summary = st.selectbox("สรุปผลรวม", ["ผ่าน (discharge)", "ไม่ผ่าน (นัดรอบต่อไป)", "ส่งตัวไปรพ.ลำปาง"])
            
            has_appt = st.checkbox("มีการนัดหมายครั้งถัดไป?")
            appt_date = None
            if has_appt:
                appt_date = thai_date_picker("วันนัดหมาย", "appt_picker", default_date=date.today())

            submit_btn = st.form_submit_button("💾 บันทึกข้อมูลเข้าสู่ระบบ")

            if submit_btn:
                if not hn or not citizen or not name or not recorder:
                    st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
                elif dob is None or (has_appt and appt_date is None):
                    st.error("⚠️ วันที่ระบุไม่ถูกต้อง")
                else:
                    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    dob_str = dob.strftime("%d/%m/%Y")
                    appt_str = appt_date.strftime("%d/%m/%Y") if appt_date else "-"
                    
                    new_row = [
                        timestamp, hn, citizen, name, gender, dob_str, 
                        visit, dept, right, left, summary, appt_str, recorder
                    ]
                    
                    try:
                        # หาแถวเดิม
                        cell_hn = None
                        cell_id = None
                        try:
                            cell_hn = ws.find(hn, in_column=2)
                        except: pass
                        
                        try:
                            cell_id = ws.find(citizen, in_column=3)
                        except: pass

                        target_row = None
                        if cell_hn: target_row = cell_hn.row
                        elif cell_id: target_row = cell_id.row

                        if target_row:
                            ws.update(f"A{target_row}:M{target_row}", [new_row])
                            st.success(f"✅ แก้ไขข้อมูลเดิมเรียบร้อย (HN: {hn})")
                        else:
                            ws.append_row(new_row)
                            st.balloons()
                            st.success(f"✅ บันทึกข้อมูลใหม่เรียบร้อย (HN: {hn})")
                        
                        st.cache_data.clear()
                        
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

with tab2:
    st.markdown("### 📊 สรุปสถานการณ์")
    if st.button("🔄 รีเฟรชข้อมูล"):
        st.cache_data.clear()
        st.rerun()

    if not df.empty and 'Summary' in df.columns:
        total = len(df)
        passed = len(df[df['Summary'].str.contains("ผ่าน", na=False)])
        refer = len(df[df['Summary'].str.contains("ส่งตัว", na=False)])

        m1, m2, m3 = st.columns(3)
        m1.metric("👶 คัดกรองทั้งหมด", f"{total}", delta="คน")
        m2.metric("✅ ผ่าน", f"{passed}", delta="คน", delta_color="normal")
        m3.metric("🏥 ส่งต่อ", f"{refer}", delta="คน", delta_color="inverse")
        
        c_chart, c_table = st.columns([1, 2])
        with c_chart:
            st.bar_chart(df['Summary'].value_counts(), color="#00C9FF")
        with c_table:
            # เลือกเฉพาะคอลัมน์ที่มีอยู่จริง
            cols_to_show = ['Timestamp', 'HN', 'Name', 'Summary']
            # กรองเอาเฉพาะคอลัมน์ที่มีใน df จริงๆ (กัน error)
            valid_cols = [c for c in cols_to_show if c in df.columns]
            
            v_df = df[valid_cols].copy()
            st.dataframe(v_df.sort_index(ascending=False).head(10), hide_index=True, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในระบบ")
