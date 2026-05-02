import io
import os
import traceback
from datetime import datetime

import pandas as pd
import streamlit as st

# 导入处理函数
from dispatch_processor import process_dispatch_data

# 读取输出标准说明。部署 script repo 时使用本地 docs，根 repo 运行时也保持一致。
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "docs", "输出标准.md")
with open(PROMPT_PATH, encoding="utf-8") as f:
    PROMPT_CONTENT = f.read()

st.set_page_config(page_title="数据分析：生产计划", layout="wide")

# CSS禁用表格列排序
st.markdown(
    """
    <style>
    [data-testid="stTableColumnHeader"] {
        pointer-events: none;
    }
    /* 文件上传器宽度 */
    [data-testid="stFileUploader"] {
        width: 500px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("数据分析：生产计划")

tab1, tab2 = st.tabs(["在制分析", "库存分析"])

with tab1:
    st.subheader("功能说明")
    st.markdown("""
    - 根据《派工进度追踪表》，计算各个零件的在制情况。
    - 上传的表格 **必须包含** 以下表格列：派工主题、产品型号、派工数量、加工工序、合格数量。
    """)

    st.subheader("上传文件")
    uploaded_file = st.file_uploader(
        "上传《派工进度追踪表》：",
        type=["csv", "xls", "xlsx"],
    )

    if uploaded_file is not None:
        with st.spinner("文件已上传，正在处理..."):
            try:
                # 调用业务逻辑，返回XLSX、CSV和前置校验提示；兼容旧部署的2返回值版本。
                process_result = process_dispatch_data(uploaded_file)
                if len(process_result) == 2:
                    xlsx_data, csv_data = process_result
                    validation_warnings = []
                else:
                    xlsx_data, csv_data, validation_warnings = process_result

                # 将XLSX字节流转为DataFrame用于展示，保留空行
                df_result = pd.read_excel(io.BytesIO(xlsx_data), header=None, keep_default_na=False)

                # 设置自定义列名
                num_cols = df_result.shape[1]
                custom_headers = [f"列{i + 1}" for i in range(num_cols)]
                df_result.columns = custom_headers

                timestamp = datetime.now().strftime("%m%d%H%M")

                # 处理结果
                st.subheader("处理结果")
                st.success(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 数据处理已完成。")
                if validation_warnings:
                    st.warning("数据校验提示：发现同一派工主题对应了多个产品型号，请复核源表。")
                    with st.expander("查看校验详情", expanded=True):
                        for warning in validation_warnings:
                            st.write(f"- {warning}")

                # 下载处理结果
                st.download_button(
                    label="⬇️ 下载处理结果（.xlsx）",
                    data=xlsx_data,
                    file_name=f"派工进度追踪表_处理结果_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.download_button(
                    label="⬇️ 下载处理结果（.csv）",
                    data=csv_data,
                    file_name=f"派工进度追踪表_处理结果_{timestamp}.csv",
                    mime="text/csv",
                )

                # 显示表格数据
                st.dataframe(df_result, use_container_width=True, hide_index=True, height=600)

            except Exception as e:
                error_detail = traceback.format_exc()
                st.error(f"处理文件时发生错误：{e}")
                with st.expander("错误日志", expanded=True):
                    st.code(error_detail)

    # 输出标准（页面底部）
    st.subheader("输出标准")
    st.code(PROMPT_CONTENT, language="markdown")

with tab2:
    st.subheader("库存分析")
    st.info("库存分析 content TBD")
