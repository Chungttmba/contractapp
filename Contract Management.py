import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
from datetime import datetime
import streamlit_authenticator as stauth
import json
import requests

FILE_NAME = "contracts.xlsx"
INFO_FILE = "info.xlsx"
LOGIN_LOG_FILE = "login_history.csv"
USERS_FILE = "users.json"
SHEETBEST_API_URL = "https://api.sheetbest.com/sheets/befd2b02-ac57-42fa-93be-1d37ccd5291d"

st.set_page_config(page_title="Quản lý hợp đồng", layout="wide")

# === Google Sheets ===
def save_to_google_sheets(df):
    try:
        requests.delete(SHEETBEST_API_URL)
        for record in df.to_dict(orient="records"):
            requests.post(SHEETBEST_API_URL, json=record)
    except Exception as e:
        st.warning(f"Không thể đồng bộ lên Sheet.best: {e}")

def load_from_google_sheets():
    try:
        res = requests.get(SHEETBEST_API_URL)
        res.raise_for_status()
        data = res.json()
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Không thể tải dữ liệu từ Sheet.best: {e}")
        return pd.DataFrame()

# === Quản lý user ===
def load_users():
    return {
        "usernames": {
            "admin": {
                "name": "Admin",
                "password": "$2b$12$KIXt87YOD41xZtMdpo97fOVJrNOxZbDTRZKFa6xB6KOe4a6DFi2lW"  # hash của '123456'
            }
        }
    }
        }
    }

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)

# === Dữ liệu hợp đồng ===
COLUMNS = [
    "Mã hợp đồng", "Khách hàng", "Ngày ký", "Giá trị", "Trạng thái",
    "Tình trạng thanh toán", "Giá trị quyết toán",
    "Lịch sử thanh toán", "Tổng đã thanh toán", "Còn lại",
    "Trạng thái hóa đơn", "Số hóa đơn", "Ngày hóa đơn"
]

def load_contracts():
    df = load_from_google_sheets()
    if df.empty:
        if os.path.exists(FILE_NAME):
            df = pd.read_excel(FILE_NAME)
        else:
            df = pd.DataFrame(columns=COLUMNS)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = 0.0 if "Giá trị" in col or "Tổng" in col else ""
    return df

def save_contracts(df):
    df.to_excel(FILE_NAME, index=False)
    save_to_google_sheets(df)

# === Xác thực người dùng ===
credentials = load_users()
authenticator = stauth.Authenticate(credentials, "contract_app", "auth_token", cookie_expiry_days=1)
name, auth_status, username = authenticator.login("🔐 Đăng nhập", location="main")

if auth_status:
    authenticator.logout("🚪 Đăng xuất", "sidebar")
    st.sidebar.success(f"✅ Xin chào, {name}")

    st.title("📋 Quản lý Hợp đồng & Đơn hàng")
    df = load_contracts()

    st.markdown("## 📑 Danh sách hợp đồng")

    # Lọc theo năm và trạng thái
    df["Ngày ký"] = pd.to_datetime(df["Ngày ký"], errors="coerce")
    df["Năm"] = df["Ngày ký"].dt.year
    df["Tháng"] = df["Ngày ký"].dt.month
    df["Quý"] = df["Ngày ký"].dt.quarter

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        selected_year = st.selectbox("📆 Lọc theo năm", ["Tất cả"] + sorted(df["Năm"].dropna().unique().astype(int).tolist()))
    with col_filter2:
        selected_status = st.selectbox("📌 Lọc theo trạng thái hợp đồng", ["Tất cả"] + sorted(df["Trạng thái"].dropna().unique()))

    if selected_year != "Tất cả":
        df = df[df["Năm"] == int(selected_year)]
    if selected_status != "Tất cả":
        df = df[df["Trạng thái"] == selected_status]

    st.dataframe(df, use_container_width=True)

    # Thống kê doanh thu
    st.markdown("## 📊 Thống kê doanh thu")
    col1, col2 = st.columns(2)
    with col1:
        month_stat = df.groupby("Tháng")["Giá trị quyết toán"].sum().reset_index()
        fig1 = px.bar(month_stat, x="Tháng", y="Giá trị quyết toán", title="Doanh thu theo tháng")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        quarter_stat = df.groupby("Quý")["Giá trị quyết toán"].sum().reset_index()
        fig2 = px.pie(quarter_stat, names="Quý", values="Giá trị quyết toán", title="Tỷ lệ doanh thu theo quý")
        st.plotly_chart(fig2, use_container_width=True)

    # Thống kê theo khách hàng
    st.markdown("## 👥 Doanh thu theo khách hàng")
    kh_stat = df.groupby("Khách hàng")["Giá trị quyết toán"].sum().reset_index().sort_values(by="Giá trị quyết toán", ascending=False)
    fig3 = px.bar(kh_stat, x="Giá trị quyết toán", y="Khách hàng", orientation="h", title="Doanh thu theo khách hàng")
    st.plotly_chart(fig3, use_container_width=True)

    # Xuất thống kê theo khách hàng ra Excel
    buffer = io.BytesIO()
    kh_stat.to_excel(buffer, index=False)
    st.download_button(
        label="📥 Tải thống kê theo khách hàng",
        data=buffer.getvalue(),
        file_name="doanh_thu_theo_khach_hang.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.warning("Vui lòng đăng nhập để tiếp tục.")
