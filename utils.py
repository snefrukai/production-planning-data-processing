"""
公共工具模块 - 可复用的数据处理工具函数
"""
import pandas as pd
from typing import IO, Dict, List, Tuple


def read_uploaded_file(file_obj: IO) -> pd.DataFrame:
    """
    读取上传的文件（CSV / XLS / XLSX），返回无表头的 DataFrame。

    Args:
        file_obj: 带有 .name 属性的文件对象

    Returns:
        pd.DataFrame, header=None

    Raises:
        ValueError: 不支持的文件格式
    """
    filename = file_obj.name.lower()

    if filename.endswith('.csv'):
        return pd.read_csv(file_obj, header=None)
    elif filename.endswith(('.xls', '.xlsx')):
        return pd.read_excel(file_obj, header=None)
    else:
        raise ValueError("不支持的文件格式，请上传 .csv, .xls 或 .xlsx 文件")


def detect_headers(
    df: pd.DataFrame,
    required_cols: List[str],
    optional_cols: List[str],
) -> Tuple[Dict[str, int], int]:
    """
    扫描前两行，识别列名到列索引的映射（支持多行列头）。

    Args:
        df: 原始 DataFrame（header=None）
        required_cols: 必需的列名列表
        optional_cols: 可选的列名列表

    Returns:
        (col_idx, data_start_row)
        - col_idx: {列名: 列索引} 映射
        - data_start_row: 数据行的起始索引（表头之后）

    Raises:
        ValueError: 缺少必需列
    """
    all_cols = required_cols + optional_cols

    row1 = [s.strip() if isinstance(s, str) else str(s).strip() for s in df.iloc[0].tolist()]
    row2 = (
        [s.strip() if isinstance(s, str) else str(s).strip() for s in df.iloc[1].tolist()]
        if len(df) > 1
        else None
    )

    col_idx: Dict[str, int] = {}
    row2_has_header = False

    # 扫描第一行
    for idx, val in enumerate(row1):
        if val in all_cols:
            col_idx[val] = idx

    # 扫描第二行，补充第一行未匹配到的列
    if row2:
        for idx, val in enumerate(row2):
            if val in all_cols and val not in col_idx:
                col_idx[val] = idx
                row2_has_header = True

    # 确定数据起始行
    header_end_row = 1 if row2_has_header else 0
    data_start_row = header_end_row + 1

    # 验证必需列
    missing = [col for col in required_cols if col not in col_idx]
    if missing:
        raise ValueError(f"文件缺少必要的列: {missing}。请检查文件格式是否正确。")

    return col_idx, data_start_row


def clean_numeric_column(series: pd.Series) -> pd.Series:
    """
    将 Series 中的值转换为数值类型（处理逗号、NaN 等）。

    使用 pandas 向量化操作替代逐行 apply，性能更好。

    Args:
        series: 需要转换的列

    Returns:
        转换后的浮点数 Series，无法解析的值填充为 0.0
    """
    return pd.to_numeric(
        series.astype(str).str.replace(',', '', regex=False),
        errors='coerce',
    ).fillna(0.0)
