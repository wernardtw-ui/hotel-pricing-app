# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
from datetime import datetime

# -------------------------------
# 🔐 Connect to Google Sheets
# -------------------------------
@st.cache_resource
def connect_to_sheets():
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]  # ✅ No extra spaces
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

# -------------------------------
# 📥 Load Data from "Dynamic Rates" sheet
# -------------------------------
def load_data():
    try:
        client = connect_to_sheets()
        sheet_url = "https://docs.google.com/spreadsheets/d/1Rx0pAtTL36ToWVctTA7bYUD-NIAXePJo2ycl5p3EcBM"  # ✅ No trailing spaces
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.get_worksheet_by_id(211369863)  # ✅ Correct gid
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df, worksheet
    except Exception as e:
        st.error(f"❌ Failed to load {str(e)}")
        return pd.DataFrame(), None

# -------------------------------
# 💾 Save Manual_Override Back to Google Sheet
# -------------------------------
def save_manual_override(worksheet, row_index, new_price):
    try:
        # Update Column I (9th column) = Manual_Override
        worksheet.update_cell(row_index + 2, 9, new_price)  # +2 because: 1=header, 0-indexed
        return True, "✅ Successfully saved to 'Manual_Override'!"
    except Exception as e:
        return False, f"❌ Save failed: {str(e)}"

# -------------------------------
# 🚀 Push to NightsBridge (Optional)
# -------------------------------
def push_to_nightsbridge(new_price):
    try:
        url = "https://api.nightsbridge.com/v1/properties/YOUR_PROPERTY_ID/rates"  # ✅ No trailing spaces
        headers = {
            "Authorization": f"Bearer {st.secrets['NIGHTSBRIDGE_API_KEY']}",
            "Content-Type": "application/json"
        }
        payload = {
            "room_type_id": "YOUR_ROOM_TYPE_ID",
            "start_date": "2025-04-05",
            "end_date": "2025-04-12",
            "rate": new_price
        }
        response = requests.put(url, json=payload, headers=headers)
        if response.ok:
            return True, "🎉 Successfully updated NightsBridge!"
        else:
            return False, f"❌ NB Error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"

# -------------------------------
# 🎨 Page Setup
# -------------------------------
st.set_page_config(page_title="🏨 SA Hotel Pricing Tool", layout="wide")
st.title("🏨 SA Hotel Pricing Dashboard")
st.markdown("""
This app helps you **compare prices**, **set competitive rates**, and **update systems** — all in one place.
""")

# Custom Styling
st.markdown("""
<style>
    .stButton button {
        background-color: #0047AB; color: white; font-weight: bold;
    }
    .stButton button:hover {
        background-color: #003380;
    }
    .stApp { background-color: #f8f9fa; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 🔄 Refresh Button
# -------------------------------
if st.button("🔁 Refresh Data", type="primary"):
    with st.spinner("Loading data from Google Sheets..."):
        df, worksheet = load_data()

        if not df.empty:
            st.session_state.df = df
            st.session_state.worksheet = worksheet
        else:
            st.warning("No data loaded. Check sheet name and permissions.")

# Load from session (if refreshed)
if 'df' in st.session_state:
    df = st.session_state.df
    worksheet = st.session_state.worksheet

    # Show Data
    st.dataframe(df, use_container_width=True)

    # -------------------------------
    # Loop Through Each Room Type
    # -------------------------------
    for idx, row in df.iterrows():
        st.markdown(f"### 🏨 {row['Room_Type']}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Rate", f"${row['Current_Rate']}")
        col2.metric("Comp Avg", f"${row['Comp_Avg_Standard']}")
        col3.metric("Final Rec", f"${row['Final_Recommended']}")
        col4.metric("Occupancy", f"{row['Occupancy']}%")

        # Manual Override Input
        current_override = row['Manual_Override'] if pd.notna(row['Manual_Override']) else row['Final_Recommended']
        new_override = st.number_input(
            f"Manual Override for {row['Room_Type']}",
            min_value=0.0,
            max_value=1000.0,
            value=float(current_override),
            step=1.0,
            key=f"override_{idx}"
        )

        colA, colB = st.columns(2)

        # Save Override
        if colA.button(f"💾 Save Override for {row['Room_Type']}", key=f"save_{idx}"):
            success, msg = save_manual_override(worksheet, idx, new_override)
            if success:
                st.success(msg)
            else:
                st.error(msg)

        # Push to NightsBridge
        if "NIGHTSBRIDGE_API_KEY" in st.secrets:
            if colB.button(f"🚀 Push ${new_override} to NightsBridge", key=f"push_{idx}"):
                with st.spinner("Sending to NightsBridge..."):
                    success, msg = push_to_nightsbridge(new_override)
                    if success:
                        st.balloons()
                        st.success(msg)
                    else:
                        st.error(msg)
        else:
            st.info("🔑 NightsBridge API key not set. Push disabled.")

    # Chart: Compare Final Recommended Prices
    st.bar_chart(df.set_index("Room_Type")["Final_Recommended"])

else:
    st.info("👆 Click 'Refresh Data' to load pricing information.")
