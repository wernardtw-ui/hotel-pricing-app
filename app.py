# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

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
        df = pd.DataFrame(data)
        return df, worksheet
    except Exception as e:
        st.error(f"❌ Failed to load {str(e)}")
        return pd.DataFrame(), None

# -------------------------------
# 🎨 Page Setup
# -------------------------------
st.set_page_config(page_title="🏨 SA Hotel Pricing Tool", layout="wide")
st.title("🏨 SA Hotel Pricing Dashboard")

# -------------------------------
# 🔁 Refresh Button
# -------------------------------
if st.button("🔁 Refresh Data", type="primary"):
    with st.spinner("Loading data from Google Sheets..."):
        df, worksheet = load_data()
        if not df.empty:
            st.session_state.df = df
            st.session_state.worksheet = worksheet
        else:
            st.error("❌ No data loaded.")

# -------------------------------
# Show Data & Edit Prices
# -------------------------------
if 'df' in st.session_state:
    df = st.session_state.df
    worksheet = st.session_state.worksheet

    st.dataframe(df, use_container_width=True)

    st.markdown("### ✏️ Adjust Prices")

    for idx, row in df.iterrows():
        st.markdown(f"**{row['Room_Type']}**")

        col1, col2, col3 = st.columns(3)
        col1.metric("Current Rate", f"${row['Current_Rate']}")
        col2.metric("Comp Avg", f"${row['Comp_Avg_Standard']}")
        col3.metric("Final Rec", f"${row['Final_Recommended']}")

        # Safe override value
        override_val = row['Manual_Override']
        final_rec = row['Final_Recommended']

        if pd.isna(override_val) or override_val == '':
            override_value = float(final_rec) if pd.notna(final_rec) else 0.0
        else:
            override_value = float(override_val)

        new_override = st.number_input(
            f"Manual Override",
            min_value=0.0,
            max_value=1000.0,
            value=override_value,
            step=1.0,
            key=f"override_{idx}"
        )

        if st.button(f"💾 Save to Google Sheet", key=f"save_{idx}"):
            try:
                worksheet.update_cell(idx + 2, 9, new_override)  # Col I = 9
                st.success(f"✅ Saved ${new_override}")
            except Exception as e:
                st.error(f"❌ Save failed: {str(e)}")

else:
    st.info("👆 Click 'Refresh Data' to load your pricing data.")
