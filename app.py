# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -------------------------------
# 🔐 Connect to Google Sheets
# -------------------------------
def connect_to_sheets():
    # This will work when we add secrets later
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
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading {str(e)}")
        return pd.DataFrame()

# -------------------------------
# 💡 Calculate Average Price
# -------------------------------
def calculate_price(df):
    if "Competitor Price" in df.columns:
        avg = df["Competitor Price"].mean()
        my_price = round(avg * 0.97, 2)  # 3% below average
        return round(avg, 2), my_price
    return None, None

# -------------------------------
# 🎨 Web Page
# -------------------------------
st.set_page_config(page_title="🏨 Hotel Pricing Tool")
st.title("🏨 Hotel Pricing Dashboard")

st.markdown("This app reads competitor prices from Google Sheets.")

if st.button("🔁 Refresh Data"):
    with st.spinner("Loading data..."):
        df = load_data()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            avg, my_price = calculate_price(df)
            if avg:
                st.success(f"📊 Average Competitor Price: **${avg}**")
                st.warning(f"🎯 Your Recommended Price: **${my_price}**")