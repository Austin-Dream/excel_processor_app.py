import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import base64
import traceback
import os
import csv
from datetime import datetime
import subprocess
import tempfile

st.set_page_config(page_title="赛狐文件和WF对接转化器", page_icon="📊", layout="wide")

# ==================== GitHub配置 ====================
# 在Streamlit Cloud的Secrets中配置：
# GITHUB_TOKEN = "你的GitHub Personal Access Token"
# GITHUB_REPO = "你的用户名/仓库名" 例如 "abc/saifu-tool"
# MAPPING_FILE_PATH = "sku_mapping.xlsx"  # 仓库中的映射文件路径

def get_github_config():
    """从secrets获取GitHub配置"""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        return token, repo
    except:
        return "", ""

def load_mapping_from_github():
    """从GitHub仓库加载映射表"""
    token, repo = get_github_config()
    if not token or not repo:
        st.warning("⚠️ 未配置GitHub Token，将使用内置默认映射表")
        return get_default_mapping()
    
    try:
        # 使用GitHub API获取文件
        import requests
        url = f"https://api.github.com/repos/{repo}/contents/sku_mapping.xlsx"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.raw"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            df = pd.read_excel(tmp_path, dtype=str)
            os.unlink(tmp_path)
            
            # 构建映射字典
            df = df.dropna(subset=['原始SKU', 'Wayfair SKU'])
            mapping = dict(zip(
                df['原始SKU'].str.strip().str.upper(),
                df['Wayfair SKU'].str.strip()
            ))
            return mapping
        else:
            st.warning(f"⚠️ 无法从GitHub读取映射文件 (状态码: {response.status_code})，使用内置默认映射")
            return get_default_mapping()
    except Exception as e:
        st.warning(f"⚠️ 读取GitHub映射文件失败: {str(e)}，使用内置默认映射")
        return get_default_mapping()

def get_default_mapping():
    """内置默认映射表（作为备用）"""
    return {
        # ===== WF-1店 (Retailer ID: 33054) - 007系列 =====
        "WS007-99-12": "WS007-30-TWIN",
        "WS007-99-14": "WS007-35-TWIN",
        "WS007-137-12": "WS007-30-FULL",
        "WS007-137-14": "WS007-35-FULL",
        "WS007-152-12": "WS007-30-QUEEN",
        "WS007-152-14": "WS007-35-QUEEN",
        "WS007-192-12": "WS007-30-KING",
        "WS007-192-14": "WS007-35-KING",
        "WS007-99-12B": "WS007-30-TWIN",
        "WS007-99-14B": "WS007-35-TWIN",
        "WS007-137-12B": "WS007-30-FULL",
        "WS007-137-14B": "WS007-35-FULL",
        "WS007-152-12B": "WS007-30-QUEEN",
        "WS007-152-14B": "WS007-35-QUEEN",
        "WS007-192-12B": "WS007-30-KING",
        "WS007-192-14B": "WS007-35-KING",
        "007-99-12": "WS007-30-TWIN",
        "007-99-14": "WS007-35-TWIN",
        "007-137-12": "WS007-30-FULL",
        "007-137-14": "WS007-35-FULL",
        "007-152-12": "WS007-30-QUEEN",
        "007-152-14": "WS007-35-QUEEN",
        "007-192-12": "WS007-30-KING",
        "007-192-14": "WS007-35-KING",
        "007-99-12B": "WS007-30-TWIN",
        "007-99-14B": "WS007-35-TWIN",
        "007-137-12B": "WS007-30-FULL",
        "007-137-14B": "WS007-35-FULL",
        "007-152-12B": "WS007-30-QUEEN",
        "007-152-14B": "WS007-35-QUEEN",
        "007-192-12B": "WS007-30-KING",
        "007-192-14B": "WS007-35-KING",
        # ===== WF-2店 (Retailer ID: 35369) - 008系列 =====
        "WS008-99-12": "WS008-99-12",
        "WS008-137-12": "WS008-137-12",
        "WS008-137-14": "WS008-137-14",
        "WS008-152-12": "WS008-152-12",
        "WS008-152-14": "WS008-152-14",
        "WS008-192-12": "WS008-192-12",
        "WS008-192-14": "WS008-192-14",
        "WS008-99-12B": "WS008-99-12",
        "WS008-137-12B": "WS008-137-12",
        "WS008-137-14B": "WS008-137-14",
        "WS008-152-12B": "WS008-152-12",
        "WS008-152-14B": "WS008-152-14",
        "WS008-192-12B": "WS008-192-12",
        "WS008-192-14B": "WS008-192-14",
        "008-99-12": "WS008-99-12",
        "008-137-12": "WS008-137-12",
        "008-137-14": "WS008-137-14",
        "008-152-12": "WS008-152-12",
        "008-152-14": "WS008-152-14",
        "008-192-12": "WS008-192-12",
        "008-192-14": "WS008-192-14",
        "008-99-12B": "WS008-99-12",
        "008-137-12B": "WS008-137-12",
        "008-137-14B": "WS008-137-14",
        "008-152-12B": "WS008-152-12",
        "008-152-14B": "WS008-152-14",
        "008-192-12B": "WS008-192-12",
        "008-192-14B": "WS008-192-14",
        # ===== WF-3店 (Retailer ID: 43682) - 006系列 =====
        "WS006-137-12": "006-137-12",
        "WS006-137-12B": "006-137-12",
        "WS006-137-14": "006-137-14",
        "WS006-137-14B": "006-137-14",
        "WS006-152-12": "006-152-12",
        "WS006-152-12B": "006-152-12",
        "WS006-152-14": "006-152-14",
        "WS006-152-14B": "006-152-14",
        "WS006-192-12": "006-192-12",
        "WS006-192-12B": "006-192-12",
        "WS006-192-14": "006-192-14",
        "WS006-192-14B": "006-192-14",
        "006-137-12": "006-137-12",
        "006-137-12B": "006-137-12",
        "006-137-14": "006-137-14",
        "006-137-14B": "006-137-14",
        "006-152-12": "006-152-12",
        "006-152-12B": "006-152-12",
        "006-152-14": "006-152-14",
        "006-152-14B": "006-152-14",
        "006-192-12": "006-192-12",
        "006-192-12B": "006-192-12",
        "006-192-14": "006-192-14",
        "006-192-14B": "006-192-14",
        # ===== WF-3店 (Retailer ID: 43682) - 009系列 =====
        "WS009-137-12": "009-137-12",
        "WS009-137-12B": "009-137-12",
        "WS009-137-14": "009-137-14",
        "WS009-137-14B": "009-137-14",
        "WS009-152-12": "009-152-12",
        "WS009-152-12B": "009-152-12",
        "WS009-152-14": "009-152-14",
        "WS009-152-14B": "009-152-14",
        "WS009-192-12": "009-192-12",
        "WS009-192-12B": "009-192-12",
        "WS009-192-14": "009-192-14",
        "WS009-192-14B": "009-192-14",
        "009-137-12": "009-137-12",
        "009-137-12B": "009-137-12",
        "009-137-14": "009-137-14",
        "009-137-14B": "009-137-14",
        "009-152-12": "009-152-12",
        "009-152-12B": "009-152-12",
        "009-152-14": "009-152-14",
        "009-152-14B": "009-152-14",
        "009-192-12": "009-192-12",
        "009-192-12B": "009-192-12",
        "009-192-14": "009-192-14",
        "009-192-14B": "009-192-14",
    }

def upload_mapping_to_github(df):
    """将映射表上传到GitHub仓库"""
    token, repo = get_github_config()
    if not token or not repo:
        return False, "未配置GitHub Token，无法上传"
    
    try:
        import requests
        import base64
        
        # 将DataFrame转换为Excel二进制数据
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='映射表')
        excel_data = output.getvalue()
        
        # 获取当前文件的SHA（用于更新）
        url = f"https://api.github.com/repos/{repo}/contents/sku_mapping.xlsx"
        headers = {"Authorization": f"token {token}"}
        get_response = requests.get(url, headers=headers)
        
        payload = {
            "message": "更新SKU映射表",
            "content": base64.b64encode(excel_data).decode('utf-8'),
            "branch": "main"
        }
        
        if get_response.status_code == 200:
            # 文件已存在，需要提供SHA
            payload["sha"] = get_response.json()["sha"]
        
        put_response = requests.put(url, headers=headers, json=payload)
        
        if put_response.status_code in [200, 201]:
            return True, "映射表已成功上传到GitHub！"
        else:
            return False, f"上传失败: {put_response.status_code}"
    except Exception as e:
        return False, f"上传出错: {str(e)}"

def create_mapping_template():
    """创建映射表模板（供下载）"""
    default_mapping = get_default_mapping()
    df = pd.DataFrame(list(default_mapping.items()), columns=['原始SKU', 'Wayfair SKU'])
    return df

# ==================== 原有的业务逻辑函数 ====================

def get_retailer_id(wayfair_sku):
    if wayfair_sku.startswith("WS007"):
        return "33054"
    elif wayfair_sku.startswith("WS008"):
        return "35369"
    elif wayfair_sku.startswith("006") or wayfair_sku.startswith("009"):
        return "43682"
    else:
        return None

PROCESSED_LOG_FILE = "processed_orders.csv"

def log_error(error_msg):
    with open("error_log.txt", "a") as f:
        f.write(f"{pd.Timestamp.now()}: {error_msg}\n")

def get_part_number(original_sku, mapping):
    """使用外部映射表转换SKU"""
    try:
        if pd.isna(original_sku):
            return None
        sku_str = str(original_sku).strip().upper()
        return mapping.get(sku_str)
    except Exception as e:
        log_error(f"SKU处理错误: {str(e)}")
        return None

def format_phone_number(phone_str):
    try:
        if pd.isna(phone_str) or phone_str == "":
            return ""
        phone_digits = re.sub(r'\D', '', str(phone_str))
        if len(phone_digits) == 10:
            return f"+1 {phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"
        else:
            return str(phone_str)
    except Exception as e:
        log_error(f"电话号码格式化错误: {str(e)}")
        return str(phone_str)

def split_address(address1, address2, door_number, max_length=35):
    try:
        parts = []
        for addr in [address1, address2, door_number]:
            if pd.notna(addr) and str(addr).strip() and str(addr).strip() != "nan":
                parts.append(str(addr).strip())
        if not parts:
            return "", ""
        full_address = " ".join(parts)
        if len(full_address) <= max_length:
            return full_address, ""
        split_index = max_length
        while split_index > 0 and full_address[split_index] != ' ':
            split_index -= 1
        if split_index == 0:
            split_index = max_length
        address_line1 = full_address[:split_index].strip()
        address_line2 = full_address[split_index:].strip()
        return address_line1, address_line2
    except Exception as e:
        log_error(f"地址拆分错误: {str(e)}")
        return str(address1), ""

def consolidate_orders(df):
    required_cols = ['订单号', 'SKU', 'SKU数量', '收件人', '地址1', '地址2', '门牌号', '城市', '州/省', '邮编', '电话']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"原始文件缺少必要列：{missing}，请检查文件格式")
        return df
    original_rows = len(df)
    df['SKU数量'] = pd.to_numeric(df['SKU数量'], errors='coerce').fillna(0)
    agg_dict = {
        'SKU数量': 'sum',
        '收件人': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
        '地址1': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
        '地址2': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
        '门牌号': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
        '城市': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
        '州/省': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
        '邮编': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
        '电话': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else '',
    }
    other_cols = [c for c in df.columns if c not in required_cols and c not in agg_dict]
    for col in other_cols:
        agg_dict[col] = lambda x, col=col: x.dropna().iloc[0] if len(x.dropna()) > 0 else ''
    grouped = df.groupby(['订单号', 'SKU'], as_index=False).agg(agg_dict)
    grouped['SKU数量'] = grouped['SKU数量'].astype(int)
    merged_rows = original_rows - len(grouped)
    if merged_rows > 0:
        st.warning(f"⚠️ 文件内合并：原数据 {original_rows} 行，按订单号+SKU合并后 {len(grouped)} 行，合并了 {merged_rows} 行（数量已累加）。")
    return grouped

def load_processed_orders():
    if not os.path.exists(PROCESSED_LOG_FILE):
        return set()
    processed = set()
    try:
        with open(PROCESSED_LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed.add((row['order_number'], row['sku']))
    except Exception as e:
        st.error(f"读取处理记录失败: {e}")
    return processed

def save_processed_orders(new_records, mode='a'):
    file_exists = os.path.exists(PROCESSED_LOG_FILE)
    with open(PROCESSED_LOG_FILE, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists or mode == 'w':
            writer.writerow(['order_number', 'sku', 'processed_at', 'source_file'])
        for order, sku, src_file in new_records:
            writer.writerow([order, sku, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), src_file])

def check_duplicate_orders(df, processed_set):
    duplicates = []
    new_indices = []
    for idx, row in df.iterrows():
        order = str(row.get('订单号', ''))
        sku = str(row.get('SKU', ''))
        if (order, sku) in processed_set:
            duplicates.append({
                'order_number': order,
                'sku': sku,
                'original_index': idx,
                'row_data': row.to_dict()
            })
        else:
            new_indices.append(idx)
    new_df = df.loc[new_indices].copy()
    return duplicates, new_df

def process_excel_data(df, signature_required, mapping):
    df = consolidate_orders(df)
    
    rows_by_store = {
        "33054": [],
        "35369": [],
        "43682": []
    }
    
    skipped_rows = []
    column_order = [
        'Retailer ID', 'Retailer PO Number', 'Retailer Order Number', 'Recipient Order Number',
        'Part Number', 'Quantity', 'Fulfillment Warehouse ID', 'Shipping Account Number',
        'SCAC Code', 'Ship Speed', 'Delivery Signature Required', 'Shipping Name',
        'Shipping Address 1', 'Shipping Address 2', 'Shipping City', 'Shipping State',
        'Shipping Postal Code', 'Shipping Country', 'Shipping Phone Number', 'Shipping Email'
    ]
    
    try:
        order_counter = {}
        
        for idx, row in df.iterrows():
            if pd.isna(row.get('SKU')) or row.get('SKU数量', 0) == 0:
                continue
            
            original_sku = row.get('SKU', '')
            wayfair_sku = get_part_number(original_sku, mapping)
            
            if not wayfair_sku:
                skipped_rows.append({
                    '行号': idx + 2,
                    '原始SKU': original_sku,
                    '原因': '无法匹配到Wayfair标准SKU'
                })
                continue
            
            retailer_id = get_retailer_id(wayfair_sku)
            
            if not retailer_id:
                skipped_rows.append({
                    '行号': idx + 2,
                    '原始SKU': original_sku,
                    '原因': f'无法确定店铺 (SKU: {wayfair_sku})'
                })
                continue
            
            order_number = str(row.get('订单号', '')).strip()
            quantity = int(row.get('SKU数量', 1))
            delivery_signature = "Yes" if signature_required else ""
            
            counter_key = f"{retailer_id}_{order_number}"
            if counter_key not in order_counter:
                order_counter[counter_key] = 0
            
            for i in range(quantity):
                order_counter[counter_key] += 1
                package_num = order_counter[counter_key]
                
                if package_num == 1:
                    po_number = order_number
                else:
                    po_number = f"{order_number}-{package_num}"
                
                addr1, addr2 = split_address(
                    row.get('地址1', ''),
                    row.get('地址2', ''),
                    row.get('门牌号', '')
                )
                
                new_row = {
                    'Retailer ID': retailer_id,
                    'Retailer PO Number': po_number,
                    'Retailer Order Number': po_number,
                    'Recipient Order Number': '',
                    'Part Number': wayfair_sku,
                    'Quantity': 1,
                    'Fulfillment Warehouse ID': '',
                    'Shipping Account Number': '',
                    'SCAC Code': '',
                    'Ship Speed': '',
                    'Delivery Signature Required': delivery_signature,
                    'Shipping Name': row.get('收件人', ''),
                    'Shipping Address 1': addr1,
                    'Shipping Address 2': addr2,
                    'Shipping City': row.get('城市', ''),
                    'Shipping State': row.get('州/省', ''),
                    'Shipping Postal Code': row.get('邮编', ''),
                    'Shipping Country': 'US',
                    'Shipping Phone Number': format_phone_number(row.get('电话', '')),
                    'Shipping Email': 'tpcfjjyxgs@163.com'
                }
                rows_by_store[retailer_id].append(new_row)
                
    except Exception as e:
        log_error(f"数据处理错误: {str(e)}")
        st.error(f"数据处理错误: {str(e)}")
    
    if skipped_rows:
        st.warning(f"⚠️ 发现 {len(skipped_rows)} 个无法映射的SKU")
        skipped_df = pd.DataFrame(skipped_rows)
        st.dataframe(skipped_df)
        st.info("这些订单已被跳过，不会生成发货文件。请检查SKU是否正确。")
    
    for retailer_id, rows in rows_by_store.items():
        if rows:
            store_name = {
                "33054": "WF-1店 (007系列)",
                "35369": "WF-2店 (008系列)",
                "43682": "WF-3店 (006/009系列)"
            }.get(retailer_id, retailer_id)
            st.info(f"📦 {store_name}: {len(rows)} 条包裹")
    
    today = datetime.now()
    date_str = today.strftime("%-m月%-d日")
    if date_str.startswith("0"):
        date_str = today.strftime("%#m月%#d日")
    if date_str.startswith("0"):
        month = today.month
        day = today.day
        date_str = f"{month}月{day}日"
    
    header_row = {col: '' for col in column_order}
    header_row['Retailer PO Number'] = date_str
    
    final_rows = [header_row]
    
    for retailer_id in ["33054", "35369", "43682"]:
        if rows_by_store[retailer_id]:
            final_rows.extend(rows_by_store[retailer_id])
    
    result_df = pd.DataFrame(final_rows)
    if not result_df.empty:
        result_df = result_df[column_order]
        mask = ~result_df['Retailer PO Number'].isin([date_str, ''])
        data_rows = result_df[mask]
        other_rows = result_df[~mask]
        data_rows = data_rows.drop_duplicates(subset=['Retailer PO Number', 'Part Number'], keep='first')
        result_df = pd.concat([other_rows, data_rows], ignore_index=True)
    
    return result_df, date_str, len(skipped_rows)

def get_download_link(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        if 'Shipping Postal Code' in df.columns:
            col_idx = df.columns.get_loc('Shipping Postal Code')
            cell_format = workbook.add_format({'num_format': '@'})
            worksheet.set_column(col_idx, col_idx, None, cell_format)
    processed_data = output.getvalue()
    b64 = base64.b64encode(processed_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">点击下载处理后的文件</a>'
    return href

# ==================== 主界面 ====================

def main():
    st.title("赛狐文件和WF对接转化器")
    st.markdown("---")
    
    # 加载映射表
    mapping = load_mapping_from_github()
    st.success(f"✅ 已加载映射表，共 {len(mapping)} 条映射规则")
    
    # ===== 映射表管理区域 =====
    with st.expander("📝 管理SKU映射表（助理专用）", expanded=False):
        st.markdown("""
        **操作说明：**
        1. 点击下方按钮下载当前映射表模板（Excel格式）
        2. 在Excel中编辑映射关系（两列：`原始SKU` 和 `Wayfair SKU`）
        3. 保存后，通过下方上传功能将新映射表提交到GitHub
        4. 提交成功后，所有用户将自动使用最新映射表
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 下载映射表模板"):
                template_df = create_mapping_template()
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    template_df.to_excel(writer, index=False, sheet_name='映射表')
                b64 = base64.b64encode(output.getvalue()).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="sku_mapping_template.xlsx">点击下载模板</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            uploaded_mapping = st.file_uploader("📤 上传新映射表", type=["xlsx"], key="mapping_upload")
            if uploaded_mapping is not None:
                try:
                    new_df = pd.read_excel(uploaded_mapping, dtype=str)
                    if '原始SKU' in new_df.columns and 'Wayfair SKU' in new_df.columns:
                        new_df = new_df.dropna(subset=['原始SKU', 'Wayfair SKU'])
                        if len(new_df) > 0:
                            st.dataframe(new_df.head(10))
                            if st.button("🚀 确认上传到GitHub"):
                                with st.spinner("正在上传到GitHub..."):
                                    success, msg = upload_mapping_to_github(new_df)
                                    if success:
                                        st.success(msg)
                                        st.info("🔄 页面即将刷新以加载新映射...")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        else:
                            st.warning("上传的文件为空，请检查后重试")
                    else:
                        st.error("文件格式错误：需要包含 '原始SKU' 和 'Wayfair SKU' 两列")
                except Exception as e:
                    st.error(f"读取文件失败: {str(e)}")
        
        # 显示当前映射表预览
        st.markdown("**当前映射表预览（前20条）：**")
        preview_df = pd.DataFrame(list(mapping.items()), columns=['原始SKU', 'Wayfair SKU']).head(20)
        st.dataframe(preview_df)
    
    st.markdown("---")
    
    # ===== 主功能区域 =====
    st.markdown("""
    ### 使用说明
    1. 上传从赛狐平台下载的Excel文件
    2. 选择是否需要**签收服务**（默认不勾选）
    3. 系统自动处理：
       - **SKU智能映射**：自动将赛狐SKU转换为Wayfair标准SKU
       - **自动分配店铺**：根据SKU自动分配Retailer ID
       - **自动拆包**：每件商品独立成一个包裹，订单号自动加 -1, -2, -3...
       - **跨文件防重复**：记录已处理的订单
       - **文件内合并**：同一订单号+同一SKU自动合并数量
       - **无效SKU提示**：无法映射的SKU会显示并跳过
    4. 下载处理后的文件，根据Retailer ID分别复制到不同店铺
    """)
    
    uploaded_file = st.file_uploader("选择要处理的Excel文件", type=["xlsx"])
    signature_required = st.checkbox("要求签收服务 (Delivery Signature Required)", value=False)
    
    with st.sidebar:
        st.header("历史记录管理")
        if st.button("清空所有处理记录"):
            if os.path.exists(PROCESSED_LOG_FILE):
                os.remove(PROCESSED_LOG_FILE)
                st.success("已清空所有历史记录，下次上传将重新处理所有订单。")
            else:
                st.info("记录文件不存在，无需清空。")
        if st.button("下载当前记录文件"):
            if os.path.exists(PROCESSED_LOG_FILE):
                with open(PROCESSED_LOG_FILE, "rb") as f:
                    st.download_button("点击下载", f, file_name=PROCESSED_LOG_FILE)
            else:
                st.info("暂无记录文件。")
        
        st.markdown("---")
        st.markdown("### 店铺Retailer ID")
        st.markdown("- WF-1店 (007系列): `33054`")
        st.markdown("- WF-2店 (008系列): `35369`")
        st.markdown("- WF-3店 (006/009系列): `43682`")
        
        st.markdown("---")
        st.markdown("### 拆包规则")
        st.markdown("每个包裹只能包含 **1件商品**")
        st.markdown("同一订单号多个包裹时：")
        st.markdown("- 第1个包裹: `订单号`")
        st.markdown("- 第2个包裹: `订单号-2`")
        st.markdown("- 第3个包裹: `订单号-3`")
        st.markdown("...以此类推")
    
    if uploaded_file is not None:
        try:
            st.info("正在读取文件...")
            df = pd.read_excel(uploaded_file, dtype={'邮编': str})
            if '邮编' in df.columns:
                df['邮编'] = df['邮编'].fillna('').astype(str).str.strip()
            st.success(f"成功读取文件，共 {len(df)} 行数据")
            
            with st.expander("查看原始数据预览"):
                st.dataframe(df.head())
            
            processed_set = load_processed_orders()
            duplicates, new_df = check_duplicate_orders(df, processed_set)
            
            if len(duplicates) > 0:
                st.warning(f"发现 {len(duplicates)} 个已处理过的订单（订单号+SKU组合）")
                dup_preview = pd.DataFrame([{'订单号': d['order_number'], 'SKU': d['sku']} for d in duplicates])
                st.dataframe(dup_preview)
                
                action = st.radio(
                    "请选择对重复订单的处理方式：",
                    ("跳过重复订单（推荐）", "强制重新处理（会覆盖旧记录，慎用！可能造成重复发货）"),
                    index=0
                )
                if action == "跳过重复订单（推荐）":
                    df_to_process = new_df
                    force_overwrite = False
                    st.info(f"将跳过 {len(duplicates)} 个重复订单，仅处理新订单")
                else:
                    df_to_process = df
                    force_overwrite = True
                    st.warning("强制处理模式：将覆盖旧记录，重新生成这些订单的发货文件。请确认不会造成重复发货！")
            else:
                df_to_process = df
                force_overwrite = False
                st.success("未发现已处理过的订单，全部为新订单。")
            
            if df_to_process.empty:
                st.error("没有需要处理的新订单，已全部跳过。")
                return
            
            st.info("正在生成WF文件...")
            processed_df, date_str, skipped_count = process_excel_data(df_to_process, signature_required, mapping)
            
            if processed_df.empty or len(processed_df) <= 1:
                st.error("处理完成，但没有生成有效数据，请检查原始文件格式")
            else:
                total_rows = len(processed_df) - 1
                st.success(f"处理完成，生成 {total_rows} 条包裹数据")
                if skipped_count > 0:
                    st.warning(f"⚠️ 跳过 {skipped_count} 个无法映射的SKU")
                
                with st.expander("查看处理后的数据预览"):
                    st.dataframe(processed_df.head(20))
                
                new_records = []
                for _, row in df_to_process.iterrows():
                    order = str(row.get('订单号', ''))
                    sku = str(row.get('SKU', ''))
                    if order and sku:
                        new_records.append((order, sku, uploaded_file.name))
                
                if new_records:
                    if force_overwrite:
                        current_set = load_processed_orders()
                        to_remove = {(order, sku) for order, sku, _ in new_records}
                        remaining = current_set - to_remove
                        all_records = []
                        for order, sku in remaining:
                            all_records.append((order, sku, "历史记录"))
                        for order, sku, src in new_records:
                            all_records.append((order, sku, src))
                        save_processed_orders(all_records, mode='w')
                        st.info(f"已更新记录：覆盖了 {len(to_remove)} 个订单，新增了 {len(new_records)} 个订单。")
                    else:
                        save_processed_orders(new_records, mode='a')
                        st.success(f"已将 {len(new_records)} 个新订单加入处理记录，下次上传将自动跳过。")
                else:
                    st.info("本次无新订单产生，未更新记录。")
                
                original_filename = uploaded_file.name
                base_name = original_filename.split('.')[0]
                download_filename = f"{base_name}_WF处理结果.xlsx"
                st.markdown("### 下载处理结果")
                st.markdown(get_download_link(processed_df, download_filename), unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 📊 包裹统计")
                for retailer_id in ["33054", "35369", "43682"]:
                    count = len(processed_df[processed_df['Retailer ID'] == retailer_id])
                    if count > 0:
                        store_name = {
                            "33054": "WF-1店 (007系列)",
                            "35369": "WF-2店 (008系列)",
                            "43682": "WF-3店 (006/009系列)"
                        }.get(retailer_id, retailer_id)
                        st.info(f"**{store_name}** (Retailer ID: {retailer_id}): {count} 个包裹")
                
        except Exception as e:
            st.error(f"处理出错: {str(e)}")
            st.code(traceback.format_exc())
            log_error(f"处理出错: {str(e)}\n{traceback.format_exc()}")
    
    st.markdown("---")
    st.markdown("如有问题，请检查错误日志文件或联系开发人员")

if __name__ == "__main__":
    main()
