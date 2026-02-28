import streamlit as st
from datetime import datetime

# 导入处理函数
from data_processor import process_dispatch_data 

st.set_page_config(page_title="数据处理：派工进度", layout="wide")
st.title("数据处理：派工进度")

st.markdown("""
- 根据《派工进度追踪表》，计算各个零件的未入库情况。
- 核心输出内容：PDM图号、物料描述、说明。
""")

uploaded_file = st.file_uploader("上传《派工进度追踪表》：", type=["csv", "xls", "xlsx"])

if uploaded_file is not None:
    with st.spinner("文件已上传，正在处理..."):
        try:
            # 调用业务逻辑
            csv_data = process_dispatch_data(uploaded_file)
            
            timestamp = datetime.now().strftime("%m%d%H%M")
            st.success(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 数据处理已完成。")
            
            st.download_button(
                label="⬇️ 下载处理结果",
                data=csv_data,
                file_name=f"派工进度追踪表_处理结果_{timestamp}.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"处理文件时发生错误。错误信息：{e}")