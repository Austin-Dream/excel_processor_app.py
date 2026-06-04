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

st.set_page_config(page_title="赛狐文件和WF对接转化器", page_icon="📊", layout="wide")

# 固定的SKU映射表（仅用于WS007系列）
SKU_MAPPING = {
    "WS007-137-10": "WS007-26-FULL",
    "WS007-137-12": "WS007-30-FULL",
    "WS007-137-14": "WS007-35-FULL",
    "WS007-152-10": "WS007-26-QUEEN",
    "WS007-152-12": "WS007-30-QUEEN",
    "WS007-152-14": "WS007-35-QUEEN",
    "WS007-192-10": "WS007-26-KING",
    "WS007-192-12": "WS007-30-KING",
    "WS007-192-14": "WS007-35-KING",
    "WS007-99-12": "WS007-30-TWIN",
    "WS007-99-14": "WS007-35-TWIN",
    # WS008映射已废弃，直接使用原始SKU
    "WS008-137-10": "WS008-26-FULL",
    "WS008-137-12": "WS008-30-FULL",
    "WS008-137-14": "WS008-35-FULL",
    "WS008-152-10": "WS008-26-QUEEN",
    "WS008-152-12": "WS008-30-QUEEN",
    "WS008-152-14": "WS008-35-QUEEN",
    "WS008-192-10": "WS008-26-KING",
    "WS008-192-12": "WS008-30-KING",
    "WS008-192-14": "WS008-35-KING",
    "WS008-99-12": "WS008-30-TWIN",
    "WS008-99-14": "WS008-35-TWIN"
}

PROCESSED_LOG_FILE = "processed_orders.csv"

def log_error(error_msg):
    with open("error_log.txt", "a") as f:
        f.write(f"{pd.Timestamp.now()}: {error_msg}\n")

def get_part_number(original_sku):
    try:
        if pd.isna(original_sku):
            return ""
        sku_str = str(original_sku).strip()
        if sku_str.startswith("WS007"):
            return SKU_MAPPING.get(sku_str, sku_str)
        elif sku_str.startswith("WS008"):
            return sku_str
        else:
            return sku_str
    except Exception as e:
        log_error(f"SKU处理错误: {str(e)}")
        return str(original_sku)

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
    """单文件内合并重复订单行（同一订单号+同一SKU）"""
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
    """加载历史处理记录，返回 set of (订单号, SKU)"""
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
    """追加新记录，mode='w' 会覆盖文件并写入表头"""
    file_exists = os.path.exists(PROCESSED_LOG_FILE)
    with open(PROCESSED_LOG_FILE, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists or mode == 'w':
            writer.writerow(['order_number', 'sku', 'processed_at', 'source_file'])
        for order, sku, src_file in new_records:
            writer.writerow([order, sku, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), src_file])

def check_duplicate_orders(df, processed_set):
    """检查当前 df 中哪些订单已处理过，返回 (重复列表, 新订单DataFrame)"""
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

def process_excel_data(df, signature_required):
    """处理赛狐数据，生成WF多渠道格式（已包含文件内合并，不包含跨文件去重）"""
    # 文件内合并
    df = consolidate_orders(df)
    
    rows_007 = []
    rows_008 = []
    column_order = [
        'Retailer ID', 'Retailer PO Number', 'Retailer Order Number', 'Recipient Order Number',
        'Part Number', 'Quantity', 'Fulfillment Warehouse ID', 'Shipping Account Number',
        'SCAC Code', 'Ship Speed', 'Delivery Signature Required', 'Shipping Name',
        'Shipping Address 1', 'Shipping Address 2', 'Shipping City', 'Shipping State',
        'Shipping Postal Code', 'Shipping Country', 'Shipping Phone Number', 'Shipping Email'
    ]
    
    try:
        for _, row in df.iterrows():
            if pd.isna(row.get('SKU')) or row.get('SKU数量', 0) == 0:
                continue
            original_sku = row.get('SKU', '')
            part_number = get_part_number(original_sku)
            if part_number.startswith("WS007"):
                retailer_id = "33054"
                target_list = rows_007
            elif part_number.startswith("WS008"):
                retailer_id = "35369"
                target_list = rows_008
            else:
                continue
            order_number = row.get('订单号', '')
            quantity = int(row.get('SKU数量', 1))
            delivery_signature = "Yes" if signature_required else ""
            for i in range(quantity):
                suffix = f"-{i+1}" if quantity > 1 else ""
                addr1, addr2 = split_address(
                    row.get('地址1', ''),
                    row.get('地址2', ''),
                    row.get('门牌号', '')
                )
                new_row = {
                    'Retailer ID': retailer_id,
                    'Retailer PO Number': f"{order_number}{suffix}",
                    'Retailer Order Number': f"{order_number}{suffix}",
                    'Recipient Order Number': '',
                    'Part Number': part_number,
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
                target_list.append(new_row)
    except Exception as e:
        log_error(f"数据处理错误: {str(e)}")
        st.error(f"数据处理错误: {str(e)}")
    
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
    
    final_rows = []
    final_rows.append(header_row)
    final_rows.extend(rows_007)
    if rows_007 and rows_008:
        empty_row = {col: '' for col in column_order}
        final_rows.append(empty_row)
    final_rows.extend(rows_008)
    
    result_df = pd.DataFrame(final_rows)
    if not result_df.empty:
        result_df = result_df[column_order]
        # 二次去重（基于PO+PartNumber）
        mask = ~result_df['Retailer PO Number'].isin([date_str, ''])
        data_rows = result_df[mask]
        other_rows = result_df[~mask]
        data_rows = data_rows.drop_duplicates(subset=['Retailer PO Number', 'Part Number'], keep='first')
        result_df = pd.concat([other_rows, data_rows], ignore_index=True)
    return result_df, date_str

def get_download_link(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    processed_data = output.getvalue()
    b64 = base64.b64encode(processed_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">点击下载处理后的文件</a>'
    return href

def main():
    st.title("赛狐文件和WF对接转化器")
    st.markdown("---")
    
    st.markdown("""
    ### 使用说明
    1. 上传从赛狐平台下载的Excel文件
    2. 选择是否需要**签收服务**（默认勾选“是”）
    3. 系统自动处理：
       - **跨文件防重复**：记录已处理的订单（订单号+SKU），避免重复发货
       - **文件内合并**：同一订单号+同一SKU自动合并数量
       - **SKU映射**：WS007系列按映射表转换；WS008系列保留原始SKU
       - **订单排序**：顶部日期行 → 007系列 → 空行 → 008系列
    4. 下载处理后的文件，可直接导入Wayfair系统
    """)
    
    uploaded_file = st.file_uploader("选择要处理的Excel文件", type=["xlsx"])
    signature_required = st.checkbox("要求签收服务 (Delivery Signature Required)", value=True)
    
    # 侧边栏：管理记录
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
    
    if uploaded_file is not None:
        try:
            st.info("正在读取文件...")
            df = pd.read_excel(uploaded_file)
            st.success(f"成功读取文件，共 {len(df)} 行数据")
            
            with st.expander("查看原始数据预览"):
                st.dataframe(df.head())
            
            # 加载历史记录
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
            processed_df, date_str = process_excel_data(df_to_process, signature_required)
            
            if processed_df.empty:
                st.error("处理完成，但没有生成有效数据，请检查原始文件格式")
            else:
                st.success(f"处理完成，生成 {len(processed_df)} 行数据（含日期行和空行）")
                with st.expander("查看处理后的数据预览"):
                    st.dataframe(processed_df.head(20))
                
                # 准备记录本次新处理的订单（基于 df_to_process，因为已经过滤了重复）
                new_records = []
                for _, row in df_to_process.iterrows():
                    order = str(row.get('订单号', ''))
                    sku = str(row.get('SKU', ''))
                    if order and sku:
                        new_records.append((order, sku, uploaded_file.name))
                
                # 保存记录
                if new_records:
                    if force_overwrite:
                        # 强制模式：需要移除旧记录中本次涉及的订单，再全部重新保存
                        # 获取旧记录中不包含本次订单的剩余部分
                        current_set = load_processed_orders()
                        to_remove = {(order, sku) for order, sku, _ in new_records}
                        remaining = current_set - to_remove
                        # 构建全部新记录（剩余+本次）
                        all_records = []
                        for order, sku in remaining:
                            # 需要从历史文件中找回原文件信息？为了简单，我们只保存订单和SKU，处理时间重新写入当前时间
                            # 但这样会丢失原处理时间。更好的办法：全量重写文件
                            all_records.append((order, sku, "历史记录"))
                        for order, sku, src in new_records:
                            all_records.append((order, sku, src))
                        # 覆盖写入
                        save_processed_orders(all_records, mode='w')
                        st.info(f"已更新记录：覆盖了 {len(to_remove)} 个订单，新增了 {len(new_records)} 个订单。")
                    else:
                        # 正常追加
                        save_processed_orders(new_records, mode='a')
                        st.success(f"已将 {len(new_records)} 个新订单加入处理记录，下次上传将自动跳过。")
                else:
                    st.info("本次无新订单产生，未更新记录。")
                
                # 下载文件
                original_filename = uploaded_file.name
                base_name = original_filename.split('.')[0]
                download_filename = f"{base_name}_处理结果.xlsx"
                st.markdown("### 下载处理结果")
                st.markdown(get_download_link(processed_df, download_filename), unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"处理出错: {str(e)}")
            st.code(traceback.format_exc())
            log_error(f"处理出错: {str(e)}\n{traceback.format_exc()}")
    
    st.markdown("---")
    st.markdown("如有问题，请检查错误日志文件或联系开发人员")

if __name__ == "__main__":
    main()
