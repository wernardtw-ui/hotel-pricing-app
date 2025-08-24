# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# -------------------------------
# 🔐 Connect to Google Sheets
# -------------------------------
@st.cache_resource
def connect_to_sheets():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Failed to authenticate with Google Sheets: {str(e)}")
        return None

# -------------------------------
# 📥 Load Data from "Dynamic Rates" sheet
# -------------------------------
def load_data():
    try:
        client = connect_to_sheets()
        if client is None:
            return pd.DataFrame(), None

        sheet_url = "https://docs.google.com/spreadsheets/d/1Rx0pAtTL36ToWVctTA7bYUD-NIAXePJo2ycl5p3EcBM"
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.worksheet("Dynamic Rates")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df, worksheet
    except gspread.exceptions.WorksheetNotFound:
        st.error("❌ Sheet 'dynamic rates' not found. Check the name.")
        return pd.DataFrame(), None
    except Exception as e:
        st.error(f"❌ Failed to load {str(e)}")
        return pd.DataFrame(), None

# -------------------------------
# 🎨 Page Setup
# -------------------------------
st.set_page_config(page_title="🏨 SA Hotel Pricing Tool", layout="wide")
st.title("🏨 SA Hotel Pricing Dashboard")
st.markdown("Reads from Google Sheets • Update prices • Sync with NightsBridge")

# -------------------------------
# 💄 Custom Styling
# -------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    h1, h2, h3 {
        color: #0047AB !important;
        font-family: 'Segoe UI', sans-serif;
    }
    .stButton button {
        background-color: #0047AB;
        color: white;
        border-radius: 8px;
        height: 50px;
        font-size: 16px;
        font-weight: bold;
    }
    .stButton button:hover {
        background-color: #003380;
        transform: scale(1.02);
        transition: all 0.2s;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stMetric > div > div:first-child {
        font-size: 18px !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 🔁 Refresh Button
# -------------------------------
if st.button("🔁 Refresh Data", type="primary"):
    with st.spinner("🔄 Loading data from 'Dynamic Rates'..."):
        time.sleep(1)
        df, worksheet = load_data()
        if not df.empty:
            st.session_state.df = df
            st.session_state.worksheet = worksheet
            st.success("✅ Data loaded!")
        else:
            st.error("❌ No data loaded. Check sheet name and permissions.")

# -------------------------------
# Show Data (if loaded)
# -------------------------------
if 'df' in st.session_state:
    df = st.session_state.df
    worksheet = st.session_state.worksheet

    # Create Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Pricing Logic", "⚙️ Settings"])

    # -------------------------------
    # TAB 1: Dashboard
    # -------------------------------
    with tab1:
        st.subheader("Live Pricing Overview")

        for idx, row in df.iterrows():
            with st.expander(f"🏨 {row['Room_Type']} – Current: ${row['Current_Rate']}", expanded=True):
                col1, col2, col3 = st.columns(3)
                col1.metric("Current Rate", f"${row['Current_Rate']}")
                col2.metric("Comp Avg", f"${row['Comp_Avg_Standard']}")
                col3.metric("Final Rec", f"${row['Final_Recommended']}")

                # Manual Override
                current_override = row['Manual_Override'] if pd.notna(row['Manual_Override']) else row['Final_Recommended']
                new_override = st.number_input(
                    f"Manual Override", 
                    min_value=0.0, 
                    value=float(current_override), 
                    step=1.0,
                    key=f"override_{idx}"
                )

                # Save Override
                if st.button(f"💾 Save Override for {row['Room_Type']}", key=f"save_{idx}"):
                    try:
                        worksheet.update_cell(idx + 2, 9, new_override)  # Row idx+2, Col 9 = Manual_Override
                        st.success(f"✅ Saved ${new_override} for {row['Room_Type']}")
                    except Exception as e:
                        st.error(f"❌ Save failed: {str(e)}")

                # Mark Pushed to NB
                if st.button(f"📤 Mark as Pushed to NB ({row['Room_Type']})", key=f"push_{idx}"):
                    try:
                        worksheet.update_cell(idx + 2, 10, "Yes")  # Col J = 10
                        st.success(f"✅ 'Push_to_NB' marked as 'Yes' for {row['Room_Type']}")
                    except Exception as e:
                        st.error(f"❌ Update failed: {str(e)}")

    # -------------------------------
    # TAB 2: Pricing Logic
    # -------------------------------
    with tab2:
        st.subheader("How the Price is Calculated")

        for idx, row in df.iterrows():
            st.write(f"### 🏨 {row['Room_Type']}")
            st.write(f"- **Competitor Average**: ${row['Comp_Avg_Standard']}")
            st.write(f"- **Occupancy Level**: {row['Occupancy']}%")
            st.write(f"- **Base Recommended**: ${row['Base_Recommended']}")
            st.write(f"- **Weekend Adjustment**: ${row['Weekend_Adjusted']}")
            st.write(f"- **Season Adjustment**: ${row['Season_Adjusted']}")
            st.write(f"- **Final Recommended**: ${row['Final_Recommended']}")
            st.markdown("---")

        st.info("Final price = Base + Weekend + Season adjustments, capped by competitor average.")

    # -------------------------------
    # TAB 3: Settings & Tools
    # -------------------------------
    with tab3:
        st.subheader("⚙️ App Settings")

        st.write("### 📁 Connected to:")
        st.code("Google Sheet: 'dynamic rates'\nRows: 2+", language="plaintext")

        st.write("### 🔐 Connections:")
        if "NIGHTSBRIDGE_API_KEY" in st.secrets:
            st.success("✅ NightsBridge API: Configured")
        else:
            st.warning("❌ NightsBridge API: Not set")

        st.write("### 📅 Last Updated:")
        st.write(f"Today at {datetime.now().strftime('%H:%M')}")

        st.markdown("---")

        # Download Button
        @st.cache_data
        def convert_df_to_csv(_df):
            return _df.to_csv(index=False)

        csv = convert_df_to_csv(df)
        st.download_button(
            label="⬇️ Download Data as CSV",
            data=csv,
            file_name="hotel_pricing_export.csv",
            mime="text/csv"
        )

        st.markdown("---")
        st.caption("App version: 1.0 • Built for SA Hotel Pricing")

else:
    st.info("👆 Click 'Refresh Data' to load pricing data from Google Sheets.")

