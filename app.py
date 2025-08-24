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
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

# -------------------------------
# 📥 Load Data
# -------------------------------
def load_data():
    try:
        client = connect_to_sheets()
        sheet_url = "https://docs.google.com/spreadsheets/d/1Rx0pAtTL36ToWVctTA7bYUD-NIAXePJo2ycl5p3EcBM"
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.get_worksheet_by_id(211369863)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"❌ Failed to load {str(e)}")
        return pd.DataFrame(), None

# -------------------------------
# 💾 Save Price Back to Google Sheet
# -------------------------------
def save_my_price(worksheet, new_price):
    try:
        cell = worksheet.find("My Hotel")
        if cell:
            worksheet.update_cell(cell.row, 4, new_price)  # Column D = "My Hotel Price"
            return True, "✅ Successfully saved to Google Sheet!"
        else:
            return False, "❌ Could not find 'My Hotel' in the sheet"
    except Exception as e:
        return False, f"❌ Save failed: {str(e)}"

# -------------------------------
# 🚀 Push to NightsBridge (Optional)
# -------------------------------
def push_to_nightsbridge(new_price):
    try:
        url = "https://api.nightsbridge.com/v1/properties/YOUR_PROPERTY_ID/rates"
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

# Load from session (if refreshed)
if 'df' in st.session_state:
    df = st.session_state.df
    worksheet = st.session_state.worksheet

    # Show Data
    st.dataframe(df, use_container_width=True)

    # Calculate Average
    if "Competitor Price" in df.columns:
        comp_prices = df["Competitor Price"].dropna()
        avg_price = round(comp_prices.mean(), 2) if len(comp_prices) > 0 else 0
        recommended_price = round(avg_price * 0.97, 2)  # 3% below

        col1, col2 = st.columns(2)
        col1.metric("📊 Avg Competitor Price", f"${avg_price}")
        col2.metric("🎯 Recommended Price", f"${recommended_price}")

        # Chart
        st.bar_chart(df.set_index("Hotel Name")["Competitor Price"])

    # -------------------------------
    # ✏️ Edit & Save Price
    # -------------------------------
    st.markdown("### ✏️ Update Your Hotel Price")

    current_my_price = df[df["Hotel Name"] == "My Hotel"]["My Hotel Price"].iloc[0]
    new_price = st.number_input(
        "Enter new price",
        min_value=0.0,
        max_value=500.0,
        value=float(current_my_price),
        step=1.0
    )

    colA, colB = st.columns(2)

    if colA.button("💾 Save to Google Sheet"):
        success, msg = save_my_price(worksheet, new_price)
        if success:
            st.success(msg)
        else:
            st.error(msg)

    # Only show if API key is set
    if "NIGHTSBRIDGE_API_KEY" in st.secrets:
        if colB.button("🚀 Push to NightsBridge"):
            with st.spinner("Sending to NightsBridge..."):
                success, msg = push_to_nightsbridge(new_price)
                if success:
                    st.balloons()
                    st.success(msg)
                else:
                    st.error(msg)
    else:
        st.info("🔑 NightsBridge API key not set. Push disabled.")

else:
    st.info("👆 Click 'Refresh Data' to load pricing information.")
