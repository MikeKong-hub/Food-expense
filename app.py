from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Page Config
st.set_page_config(
    page_title="Food & Entertainment Expense Tracker",
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

def delete_data_row(row_index):
    client = init_connection()
    sheet = client.open("Food Expenses Data").worksheet("expenses")
    # Google Sheets rows are 1-indexed, and row 1 is headers. 
    # Therefore, dataframe index 0 corresponds to sheet row 2.
    sheet.delete_rows(row_index + 2)

df = load_data()

# 3. Sidebar: Budget Settings & Filters
st.sidebar.title("⚙️ Settings & Archive")
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
st.sidebar.caption("💡 YO! CONTROL YOURSELF")

# 4. Header Section
st.markdown("<h1>🍔🎬<br>Mickey's Tracker</h1>", unsafe_allow_html=True)
st.caption(f"Overview and quick expense logging for **{selected_month}**")

# 5. Quick Entry Form
st.subheader("➕ Quick Entry")
with st.form("expense_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1:
        description = st.text_input("Description / Item", placeholder="e.g., Chicken Rice")
    with col2:
        category = st.selectbox("Category", ["Groceries", "Breakfast", "Lunch", "Dinner", "Supper", "Snacks", "Entertainment", "Minnie"])
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

# 6. KPI Metrics Dashboard
st.subheader("📊 Budget Overview")
total_spent = filtered_df["Amount"].sum() if not filtered_df.empty else 0.00
remaining_budget = monthly_budget - total_spent

# ⚠️ Over-Budget Red Warning Banner
if remaining_budget < 0:
    st.error(
        f"🚨**Ooi MANGKUK! **BUDGET EXCEEDED!** You are **RM {abs(remaining_budget):,.2f}** over your monthly budget of RM {monthly_budget:,.2f}! Watch Your Pocket!"
    )
elif remaining_budget <= monthly_budget * 0.1 and monthly_budget > 0:
    st.warning(
        f"⚠️ **WARNING:****Agak2 Sikit**~ You only have **RM {remaining_budget:,.2f}** (less than 10%) left in your budget!"
    )

# Metrics Cards
m1, m2, m3 = st.columns(3)
m1.metric("Monthly Budget", f"RM {monthly_budget:,.2f}")
m2.metric("Total Spent", f"RM {total_spent:,.2f}")

if remaining_budget >= 0:
    m3.metric("Remaining Budget", f"RM {remaining_budget:,.2f}")
else:
    m3.metric(
        "Over Budget By",
        f"RM {abs(remaining_budget):,.2f}",
        delta=f"-RM {abs(remaining_budget):,.2f}",
        delta_color="inverse",  # Displays in prominent Red
    )

# Progress Bar
usage_pct = (total_spent / monthly_budget) if monthly_budget > 0 else 0.0
st.progress(min(usage_pct, 1.0), text=f"Budget Consumed: {usage_pct * 100:.1f}%")

st.markdown("---")

# 7. Visual Breakdown & History
if not filtered_df.empty:
    col_left, col_right = st.columns([1, 1.2])
    with col_left:
        st.subheader("Spending Breakdown")
        category_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        # 7. Visual Breakdown & History
if not filtered_df.empty:
    col_left, col_right = st.columns([1, 1.2])
    with col_left:
        st.subheader("🍩 Spending Breakdown")
        category_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        
        # Color mapping for all 8 categories
        category_colors = {
            "Groceries": "#2ec4b6",
            "Breakfast": "#ff9f1c",
            "Lunch": "#e71d36",
            "Dinner": "#7209b7",
            "Supper": "#3a86ff",
            "Snacks": "#fb5607",
            "Entertainment": "#ff006e",
            "Minnie": "#ff69b4"
        }
        
        fig = px.pie(
            category_summary, 
            values="Amount", 
            names="Category", 
            hole=0.5, 
            color="Category", 
            color_discrete_map=category_colors
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=True, height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📋 Daily Log")
        display_df = filtered_df.copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display_df[["Date", "Description", "Category", "Amount"]].sort_values(by="Date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    # 8. Delete Expense Section
    st.markdown("---")
    with st.expander("🗑️ Delete an Expense"):
        expense_options = {}
        for idx, row in filtered_df.iterrows():
            date_str = row["Date"].strftime("%Y-%m-%d")
            label = f"{date_str} | {row['Description']} | RM {row['Amount']:.2f} ({row['Category']})"
            expense_options[label] = idx

        selected_label = st.selectbox("Select expense to remove", list(expense_options.keys()))
        if st.button("Delete Selected Expense", type="primary"):
            row_to_delete = expense_options[selected_label]
            delete_data_row(row_to_delete)
            st.toast("🗑️ Expense deleted successfully!")
            st.rerun()
else:
    st.info(f"No expenses recorded yet for {selected_month}.")