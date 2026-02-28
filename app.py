import streamlit as st
from datetime import datetime
import pandas as pd
import io
import traceback

# 导入处理函数
from data_processor import process_dispatch_data

st.set_page_config(page_title="数据处理：派工进度", layout="wide")

# CSS禁用表格列排序
st.markdown("""
    <style>
    [data-testid="stTableColumnHeader"] {
        pointer-events: none;
    }
    /* 文件上传器宽度 */
    [data-testid="stFileUploader"] {
        width: 500px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("数据处理：派工进度")

st.markdown("""
- 根据《派工进度追踪表》，计算各个零件的未入库情况。
- 核心输出内容：PDM图号、物料描述、说明。
""")

st.subheader("上传文件")
uploaded_file = st.file_uploader(
    "上传《派工进度追踪表》：",
    type=["csv", "xls", "xlsx"],
)

if uploaded_file is not None:
    with st.spinner("文件已上传，正在处理..."):
        try:
            # 调用业务逻辑，返回XLSX和CSV字节流
            xlsx_data, csv_data = process_dispatch_data(uploaded_file)

            # 将XLSX字节流转为DataFrame用于展示，保留空行
            df_result = pd.read_excel(
                io.BytesIO(xlsx_data),
                header=None,
                keep_default_na=False
            )

            # 设置自定义列名
            num_cols = df_result.shape[1]
            custom_headers = [f"列{i+1}" for i in range(num_cols)]
            df_result.columns = custom_headers

            timestamp = datetime.now().strftime("%m%d%H%M")
            st.success(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 数据处理已完成。")

            # 处理结果
            st.subheader("处理结果")

            # 下载处理结果
            st.download_button(
                label="⬇️ 下载处理结果（.xlsx）",
                data=xlsx_data,
                file_name=f"派工进度追踪表_处理结果_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.download_button(
                label="⬇️ 下载处理结果（.csv）",
                data=csv_data,
                file_name=f"派工进度追踪表_处理结果_{timestamp}.csv",
                mime="text/csv"
            )

            # 显示表格数据
            st.dataframe(
                df_result,
                use_container_width=True,
                hide_index=True,
                height=600
            )


        except Exception as e:
            error_detail = traceback.format_exc()
            st.error(f'处理文件时发生错误：{e}')
            with st.expander("错误日志", expanded=True):
                st.code(error_detail)