import streamlit as st
from datetime import datetime
import pandas as pd
import io
import traceback
import os

# 导入处理函数
from dispatch_processor import process_dispatch_data

# 读取处理规则说明
PROMPT_PATH = os.path.join(os.path.dirname(__file__), 'prompt.md')
with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
    PROMPT_CONTENT = f.read()

st.set_page_config(page_title="数据分析：生产计划", layout="wide")

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

st.title("数据分析：生产计划")

tab1, tab2 = st.tabs(["派工进度分析", "库存分析"])

with tab1:
    st.subheader("功能说明")
    st.markdown("""
    - 根据《派工进度追踪表》，计算各个零件的未入库情况。
    - 上传的表格 **必须** 包含以下列：订单主题、派工数量、加工工序、合格数量。
    - 上传的表格 **可选** 包含以下列：订单编号、PDM图号、产品名称。
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

                # 处理结果
                st.subheader("处理结果")
                st.success(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 数据处理已完成。")

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

    # AI 提示词（页面底部）
    st.subheader("AI 提示词")
    st.code(PROMPT_CONTENT, language="markdown")

with tab2:
    st.subheader("库存分析")
    st.info("库存分析 content TBD")