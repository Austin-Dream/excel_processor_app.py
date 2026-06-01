import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import base64
import traceback
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="赛狐文件和WF对接转化器",
    page_icon="📊",
    layout="wide"
)

# 固定的SKU映射表
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

def log_error(error_msg):
    """记录错误到日志文件"""
    with open("error_log.txt", "a") as f:
        f.write(f"{pd.Timestamp.now()}: {error_msg}\n")

def reverse_sku_mapping(original_sku):
    """反向映射SKU：从值找键"""
    try:
        return SKU_MAPPING.get(original_sku, original_sku)
    except Exception as e:
        log_error(f"SKU映射错误: {str(e)}")
        return original_sku

def format_phone_number(phone_str):
    """格式化电话号码"""
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
    """拆分地址"""
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

def process_excel_data(df, signature_required):
    """处理赛狐数据，生成WF多渠道格式
    
    Args:
        df: 原始赛狐订单DataFrame
        signature_required: bool, 是否要求签收服务
    """
    new_rows = []
    
    # 定义输出列的顺序（完全符合Wayfair模板）
    column_order = [
        'Retailer ID', 'Retailer PO Number', 'Retailer Order Number', 'Recipient Order Number',
        'Part Number', 'Quantity', 'Fulfillment Warehouse ID', 'Shipping Account Number',
        'SCAC Code', 'Ship Speed', 'Delivery Signature Required', 'Shipping Name',
        'Shipping Address 1', 'Shipping Address 2', 'Shipping City', 'Shipping State',
        'Shipping Postal Code', 'Shipping Country', 'Shipping Phone Number', 'Shipping Email'
    ]
    
    try:
        for _, row in df.iterrows():
            # 检查必要的列是否存在
            if 'SKU' not in row or 'SKU数量' not in row:
                continue
                
            if pd.isna(row.get('SKU')) or row.get('SKU数量', 0) == 0:
                continue
                
            order_number = row.get('订单号', '')
            quantity = int(float(row.get('SKU数量', 1)))
            
            for i in range(quantity):
                suffix = f"-{i+1}" if quantity > 1 else ""
                
                # 获取映射后的Part Number
                part_number = reverse_sku_mapping(row.get('SKU', ''))
                
                # 根据Part Number确定Retailer ID（固定数字）
                if part_number.startswith("WS007"):
                    retailer_id = "33054"   # WF 1店
                elif part_number.startswith("WS008"):
                    retailer_id = "35369"   # WF 2店
                else:
                    retailer_id = ""        # 其他情况留空
                
                # 签名服务字段值
                delivery_signature = "Yes" if signature_required else ""
                
                # 构建行数据（按顺序）
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
                    'Shipping Address 1': '',
                    'Shipping Address 2': '',
                    'Shipping City': row.get('城市', ''),
                    'Shipping State': row.get('州/省', ''),
                    'Shipping Postal Code': row.get('邮编', ''),
                    'Shipping Country': 'US',
                    'Shipping Phone Number': format_phone_number(row.get('电话', '')),
                    'Shipping Email': 'tpcfjjyxgs@163.com'
                }
                
                # 处理地址拆分
                addr1, addr2 = split_address(
                    row.get('地址1', ''),
                    row.get('地址2', ''),
                    row.get('门牌号', '')
                )
                new_row['Shipping Address 1'] = addr1
                new_row['Shipping Address 2'] = addr2
                
                new_rows.append(new_row)
                
    except Exception as e:
        log_error(f"数据处理错误: {str(e)}")
        st.error(f"数据处理错误: {str(e)}")
    
    # 构建DataFrame并确保列顺序
    result_df = pd.DataFrame(new_rows)
    if not result_df.empty:
        result_df = result_df[column_order]
    
    return result_df

def get_download_link(df, filename):
    """生成下载链接"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    processed_data = output.getvalue()
    b64 = base64.b64encode(processed_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">点击下载处理后的文件</a>'
    return href

def main():
    """主函数"""
    st.title("赛狐文件和WF对接转化器")
    st.markdown("---")
    
    st.markdown("""
    ### 使用说明
    1. 上传从赛狐平台下载的Excel文件
    2. 选择是否需要**签收服务**（Delivery Signature Required）
    3. 系统自动处理：
       - 根据SKU系列自动填写 `Retailer ID`：  
         - WS007系列 → **33054** (WF 1店)  
         - WS008系列 → **35369** (WF 2店)  
       - 按照Wayfair多渠道模板生成标准列顺序
       - 自动拆分地址（每行不超过35字符）
    4. 下载处理后的文件，可直接导入Wayfair系统
    """)
    
    # 文件上传区域
    st.markdown("### 上传文件")
    uploaded_file = st.file_uploader("选择要处理的Excel文件", type=["xlsx"])
    
    # 新增：签名服务选项
    st.markdown("### 签收服务设置")
    signature_required = st.checkbox("要求签收服务 (Delivery Signature Required)", 
                                     help="勾选后，输出文件的「Delivery Signature Required」列将填写 Yes")
    
    if uploaded_file is not None:
        try:
            # 读取文件
            st.info("正在读取文件...")
            df = pd.read_excel(uploaded_file)
            st.success(f"成功读取文件，共 {len(df)} 行数据")
            
            # 显示原始数据预览
            with st.expander("查看原始数据预览"):
                st.dataframe(df.head())
            
            # 处理数据
            st.info("正在处理数据...")
            processed_df = process_excel_data(df, signature_required)
            
            if processed_df.empty:
                st.error("处理完成，但没有生成有效数据，请检查原始文件格式")
            else:
                st.success(f"处理完成，生成 {len(processed_df)} 行数据")
                
                # 显示处理后的数据预览
                with st.expander("查看处理后的数据预览（已按WF模板排列）"):
                    st.dataframe(processed_df.head())
                
                # 生成下载链接
                original_filename = uploaded_file.name
                base_name = original_filename.split('.')[0]
                download_filename = f"{base_name}_处理结果.xlsx"
                
                st.markdown("### 下载处理结果")
                st.markdown(get_download_link(processed_df, download_filename), unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"处理出错: {str(e)}")
            st.code(traceback.format_exc())
            log_error(f"处理出错: {str(e)}\n{traceback.format_exc()}")
    
    # 添加页脚
    st.markdown("---")
    st.markdown("如有问题，请检查错误日志文件或联系开发人员")

if __name__ == "__main__":
    main()
