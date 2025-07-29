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
    # Sử dụng mật khẩu đã hash sẵn cho '123456'
    hashed_passwords = ["$2b$12$KIXt87YOD41xZtMdpo97fOVJrNOxZbDTRZKFa6xB6KOe4a6DFi2lW"]
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

    with st.sidebar.expander("🏢 Thông tin doanh nghiệp"):
        company_name = st.text_input("Tên doanh nghiệp", "Công ty TNHH ABC")
        logo_file = st.file_uploader("Tải lên logo", type=["png", "jpg", "jpeg"])
        if logo_file:
            st.image(logo_file, use_column_width=True)
        st.markdown(f"**Tên doanh nghiệp:** {company_name}")

    df = load_from_google_sheets()

    # Làm sạch dữ liệu ngày hóa đơn nếu có
    if "Ngày hóa đơn" in df.columns:
        df["Ngày hóa đơn"] = pd.to_datetime(df["Ngày hóa đơn"], errors="coerce")

    # Tính toán các đợt thanh toán và giá trị còn lại nếu có cột Lịch sử thanh toán
    if "Lịch sử thanh toán" in df.columns:
        def parse_ltt(x):
            if pd.isna(x) or not isinstance(x, str):
                return 0
            parts = x.split(";")
            return sum([float(p.split("|")[1]) for p in parts if "|" in p])

        df["Tổng đã thanh toán"] = df["Lịch sử thanh toán"].apply(parse_ltt)
        df["Còn lại"] = df["Giá trị quyết toán"].fillna(0) - df["Tổng đã thanh toán"].fillna(0)

    if st.button("➕ Thêm hợp đồng mới"):
        with st.form("form_them_hop_dong", clear_on_submit=True):
            st.subheader("📝 Nhập thông tin hợp đồng mới")
            ma_hd = st.text_input("Mã hợp đồng")
            khach_hang = st.text_input("Khách hàng")
            ngay_ky = st.date_input("Ngày ký")
            gt_quyet_toan = st.number_input("Giá trị quyết toán", min_value=0.0, step=100000.0)
            trang_thai_hd = st.selectbox("Trạng thái hợp đồng", ["Đang thực hiện", "Hoàn thành", "Hủy"])
            trang_thai_hdong = st.selectbox("Trạng thái hóa đơn", ["Chưa xuất", "Đã xuất"])
            so_hoa_don = st.text_input("Số hóa đơn")
            ngay_hoa_don = st.date_input("Ngày hóa đơn") if trang_thai_hdong == "Đã xuất" else ""
            lich_su_tt = st.text_area("Lịch sử thanh toán", help="Nhập dạng: Ngày|Giá trị;Ngày|Giá trị")
            submitted = st.form_submit_button("Lưu hợp đồng")
            if submitted:
                new_row = {
                    "Mã hợp đồng": ma_hd,
                    "Khách hàng": khach_hang,
                    "Ngày ký": ngay_ky.strftime("%Y-%m-%d"),
                    "Giá trị quyết toán": gt_quyet_toan,
                    "Trạng thái hợp đồng": trang_thai_hd,
                    "Trạng thái hóa đơn": trang_thai_hdong,
                    "Số hóa đơn": so_hoa_don,
                    "Ngày hóa đơn": ngay_hoa_don.strftime("%Y-%m-%d") if ngay_hoa_don else "",
                    "Lịch sử thanh toán": lich_su_tt
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_to_google_sheets(df)
                st.success("✅ Hợp đồng mới đã được lưu!")

    if df.empty:
        st.info("Chưa có dữ liệu hợp đồng.")
    else:
        # Làm sạch dữ liệu ngày
        df["Ngày ký"] = pd.to_datetime(df["Ngày ký"], errors="coerce")
        df["Năm"] = df["Ngày ký"].dt.year
        df["Tháng"] = df["Ngày ký"].dt.month
        df["Quý"] = df["Ngày ký"].dt.quarter

        st.subheader("📑 Danh sách hợp đồng")
        # Hiển thị thêm cột trạng thái hợp đồng, trạng thái hóa đơn, tổng đã thanh toán, còn lại
        display_cols = [
            "Mã hợp đồng", "Khách hàng", "Ngày ký", "Giá trị quyết toán",
            "Trạng thái hợp đồng", "Trạng thái hóa đơn", "Ngày hóa đơn", "Số hóa đơn",
            "Tổng đã thanh toán", "Còn lại"
        ]
        for col in display_cols:
            if col not in df.columns:
                df[col] = None
        st.dataframe(df[display_cols], use_container_width=True)

        # Chỉnh sửa hợp đồng theo mã
        st.subheader("✏️ Cập nhật thanh toán và giá trị quyết toán")
        selected_hd = st.selectbox("Chọn hợp đồng để chỉnh sửa", df["Mã hợp đồng"].dropna().unique())
        if selected_hd:
            row = df[df["Mã hợp đồng"] == selected_hd].iloc[0]
            with st.form("form_sua_hd"):
                gt_moi = st.number_input("Cập nhật giá trị quyết toán", value=float(row["Giá trị quyết toán"]))
                lich_su_moi = st.text_area("Cập nhật lịch sử thanh toán", value=row.get("Lịch sử thanh toán", ""),
                                          help="Nhập dạng: Ngày|Giá trị;Ngày|Giá trị")
                submit_sua = st.form_submit_button("💾 Cập nhật")
                if submit_sua:
                    df.loc[df["Mã hợp đồng"] == selected_hd, "Giá trị quyết toán"] = gt_moi
                    df.loc[df["Mã hợp đồng"] == selected_hd, "Lịch sử thanh toán"] = lich_su_moi
                    save_to_google_sheets(df)
                    st.success("✅ Đã cập nhật hợp đồng!")
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            selected_kh = st.selectbox("👤 Lọc theo khách hàng", ["Tất cả"] + sorted(df["Khách hàng"].dropna().unique()))
        with col_filter2:
            selected_invoice = "Tất cả"
            if "Trạng thái hóa đơn" in df.columns:
                invoice_options = ["Tất cả"] + sorted(df["Trạng thái hóa đơn"].dropna().unique())
                selected_invoice = st.selectbox("🧾 Lọc theo trạng thái hóa đơn", invoice_options)
                if selected_invoice != "Tất cả":
                    df = df[df["Trạng thái hóa đơn"] == selected_invoice]

        if selected_kh != "Tất cả":
            df = df[df["Khách hàng"] == selected_kh]
        if selected_invoice != "Tất cả":
            df = df[df["Trạng thái hóa đơn"] == selected_invoice]
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
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            kh_stat.to_excel(writer, index=False, sheet_name="Thống kê")
            ws = writer.sheets["Thống kê"]

            # Ghi thông tin doanh nghiệp ở dòng đầu tiên nếu có tên
            if company_name:
                ws.insert_rows(0)
                ws.cell(row=1, column=1).value = f"Doanh nghiệp: {company_name}"

            # Thêm logo nếu có
            if logo_file:
                from openpyxl.drawing.image import Image as XLImage
                from PIL import Image
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                    img = Image.open(logo_file)
                    img.save(tmp_img.name)
                    xl_img = XLImage(tmp_img.name)
                    xl_img.width = 150
                    xl_img.height = 60
                    ws.add_image(xl_img, "F1")
                ws.insert_rows(0)
                ws.cell(row=1, column=1).value = f"Doanh nghiệp: {company_name}"

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
