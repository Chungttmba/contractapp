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
        return pd.DataFrame(res.json())
    except Exception as e:
        st.warning(f"Không thể tải dữ liệu từ Sheet.best: {e}")
        return pd.DataFrame()

# === User Authentication ===
def load_users():
    hashed_passwords = stauth.Hasher(['123456']).generate()
    return {
        "usernames": {
            "admin": {
                "name": "Admin",
                "password": hashed_passwords[0]
            }
        }
    }

credentials = load_users()
authenticator = stauth.Authenticate(
    credentials,
    "contract_app",
    "auth_token",
    cookie_expiry_days=1
)
name, auth_status, username = authenticator.login("🔐 Đăng nhập", location="main")

if auth_status:
    authenticator.logout("🚪 Đăng xuất", "sidebar")
    st.sidebar.success(f"✅ Xin chào, {name}")
    st.title("📋 Quản lý Hợp đồng & Đơn hàng")

    df = load_from_google_sheets()

    if df.empty:
        st.info("Chưa có dữ liệu hợp đồng.")
    else:
        # Làm sạch dữ liệu ngày
        df["Ngày ký"] = pd.to_datetime(df["Ngày ký"], errors="coerce")
        df["Năm"] = df["Ngày ký"].dt.year
        df["Tháng"] = df["Ngày ký"].dt.month
        df["Quý"] = df["Ngày ký"].dt.quarter

        st.subheader("📑 Danh sách hợp đồng")
        year_options = ["Tất cả"] + sorted(df["Năm"].dropna().unique().astype(int).tolist())
        selected_year = st.selectbox("📆 Lọc theo năm", year_options)

        if selected_year != "Tất cả":
            df = df[df["Năm"] == int(selected_year)]

        st.dataframe(df, use_container_width=True)

        st.subheader("📊 Thống kê doanh thu")
        col1, col2 = st.columns(2)

        with col1:
            month_stat = df.groupby("Tháng")["Giá trị quyết toán"].sum().reset_index()
            fig1 = px.bar(month_stat, x="Tháng", y="Giá trị quyết toán", title="Doanh thu theo tháng")
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            quarter_stat = df.groupby("Quý")["Giá trị quyết toán"].sum().reset_index()
            fig2 = px.pie(quarter_stat, names="Quý", values="Giá trị quyết toán", title="Tỷ lệ doanh thu theo quý")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("👥 Doanh thu theo khách hàng")
        kh_stat = df.groupby("Khách hàng")["Giá trị quyết toán"].sum().reset_index().sort_values(by="Giá trị quyết toán", ascending=False)
        fig3 = px.bar(kh_stat, x="Giá trị quyết toán", y="Khách hàng", orientation="h")
        st.plotly_chart(fig3, use_container_width=True)

        buffer = io.BytesIO()
        kh_stat.to_excel(buffer, index=False)
        st.download_button(
            label="📥 Tải thống kê theo khách hàng",
            data=buffer.getvalue(),
            file_name="doanh_thu_theo_khach_hang.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif auth_status is False:
    st.error("❌ Sai tên đăng nhập hoặc mật khẩu")
elif auth_status is None:
    st.warning("🔒 Vui lòng đăng nhập để tiếp tục")
