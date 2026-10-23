from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Page Config
st.set_page_config(
    page_title="Food Expense Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Connect to Google Sheets
@st.cache_resource
def init_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    # Connect using Streamlit secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def load_data():
    try:
        client = init_connection()
        sheet = client.open("Food Expenses Data").worksheet("expenses")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df["Amount"] = pd.to_numeric(df["Amount"])
        else:
            df = pd.DataFrame(columns=["Date", "Description", "Category", "Amount"])
        return df
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame(columns=["Date", "Description", "Category", "Amount"])

def append_data(date, description, category, amount):
    client = init_connection()
    sheet = client.open("Food Expenses Data").worksheet("expenses")
    sheet.append_row([date, description, category, amount])

df = load_data()

# 3. Custom Modern CSS Styling
st.markdown("""
<style>
.stApp { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e9ecef; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
div[data-testid="stForm"] { background-color: #ffffff; border: 1px solid #e9ecef; border-radius: 16px; padding: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
.app-title { font-size: 2.2rem; font-weight: 800; color: #1a1d20; margin-bottom: 0.2rem; }
.app-subtitle { font-size: 1.05rem; color: #6c757d; margin-bottom: 1.8rem; }
</style>
""", unsafe_allow_html=True)

# 4. Sidebar: Budget Settings & Filters
st.sidebar.markdown("### ⚙️ Settings & Archive")
monthly_budget = st.sidebar.number_input("Set Monthly Budget (RM)", min_value=0.0, value=800.00, step=50.00, format="%.2f")

current_month_str = datetime.now().strftime("%Y-%m")
if not df.empty and "Date" in df.columns:
    df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
    available_months = sorted(df["YearMonth"].unique(), reverse=True)
    if current_month_str not in available_months:
        available_months.insert(0, current_month_str)
    selected_month = st.sidebar.selectbox("Select Month to Review", available_months)
    filtered_df = df[df["YearMonth"] == selected_month]
else:
    selected_month = current_month_str
    filtered_df = df

st.sidebar.markdown("---")
st.sidebar.caption("💡 Add this app to your phone home screen for instant access!")

# 5. Header Section
st.markdown('<div class="app-title">🍔 Food Expense Tracker</div>', unsafe_allow_html=True)
st.markdown(f'<div class="app-subtitle">Overview and quick expense logging for <b>{selected_month}</b></div>', unsafe_allow_html=True)

# 6. Quick Entry Form
st.markdown("### ➕ Quick Entry")
with st.form("expense_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1:
        description = st.text_input("Description / Item", placeholder="e.g., Chicken Rice")
    with col2:
        category = st.selectbox("Category", ["Groceries", "Food Outside"])
    with col3:
        amount = st.number_input("Amount (RM)", min_value=0.0, format="%.2f", step=5.0)

    submitted = st.form_submit_button("Submit Expense", use_container_width=True, type="primary")

    if submitted:
        if description and amount > 0:
            today_str = datetime.now().strftime("%Y-%m-%d")
            append_data(today_str, description, category, amount)
            st.toast(f"✅ Added: {description} (RM {amount:.2f}) under {category}!")
            st.rerun()
        else:
            st.error("Please enter a valid description and amount.")

st.markdown("---")

# 7. KPI Metrics Dashboard
st.markdown("### 📊 Budget Overview")
total_spent = filtered_df["Amount"].sum() if not filtered_df.empty else 0.00
remaining_budget = monthly_budget - total_spent

m1, m2, m3 = st.columns(3)
m1.metric("Monthly Budget", f"RM {monthly_budget:,.2f}")
m2.metric("Total Spent", f"RM {total_spent:,.2f}")
if remaining_budget >= 0:
    m3.metric("Remaining Budget", f"RM {remaining_budget:,.2f}")
else:
    m3.metric("Over Budget By", f"RM {abs(remaining_budget):,.2f}", delta=f"-RM {abs(remaining_budget):,.2f}", delta_color="inverse")

usage_pct = (total_spent / monthly_budget) if monthly_budget > 0 else 0.0
st.progress(min(usage_pct, 1.0), text=f"Budget Consumed: {usage_pct * 100:.1f}%")

st.markdown("---")

# 8. Charts & Log
if not filtered_df.empty:
    col_left, col_right = st.columns([1, 1.2])
    with col_left:
        st.markdown("### 🍩 Spending Breakdown")
        category_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        fig = px.pie(category_summary, values="Amount", names="Category", hole=0.5, color="Category", color_discrete_map={"Groceries": "#2ec4b6", "Food Outside": "#ff9f1c"})
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False, height=280)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("### 📋 Daily Log")
        display_df = filtered_df.copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(display_df[["Date", "Description", "Category", "Amount"]].sort_values(by="Date", ascending=False), use_container_width=True, hide_index=True)
else:
    st.info(f"No expenses recorded yet for {selected_month}.")