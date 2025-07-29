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

# === Xác thực người dùng ===
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
    # 👉 thêm nội dung app ở đây sau khi đăng nhập

elif auth_status is False:
    st.error("❌ Sai tên đăng nhập hoặc mật khẩu")

elif auth_status is None:
    st.warning("🔒 Vui lòng đăng nhập để tiếp tục")
