"""
派工进度数据处理模块

处理《派工进度追踪表》，计算各零件各工序的待处理量。
"""

import io
import logging
import re
from typing import IO

import pandas as pd

from models import PartDispatchResult, ProcessStep
from utils import clean_numeric_column, detect_headers, read_uploaded_file

__all__ = [
    "process_dispatch_data",
]

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
REQUIRED_COLS = ["订单主题", "派工主题", "产品型号", "派工数量", "加工工序", "合格数量"]
OPTIONAL_COLS = ["产品名称"]
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def parse_theme(theme_str: str) -> tuple[str, str]:
    """从"订单主题"中解析出 PDM 图号和物料描述。

    规则：
      - 去掉"转自："前缀
      - 若以"/"分隔，通过字符特征判断哪个是 PDM（字母数字），哪个是描述（含中文）
      - 若无分隔符，尝试从开头提取连续字母数字作为 PDM

    Args:
        theme_str: 原始的订单主题字符串.

    Returns:
        A tuple of (pdm, desc).
    """
    clean_theme = re.sub(r"^转自[：:]", "", str(theme_str))
    parts = clean_theme.split("/")

    pdm, desc = "", ""

    if len(parts) >= 2:
        part1, part2 = parts[0].strip(), parts[1].strip()

        if re.match(r"^[A-Za-z0-9\-\.]+$", part1):
            pdm, desc = part1, part2
        elif re.match(r"^[A-Za-z0-9\-\.]+$", part2):
            pdm, desc = part2, part1
        else:
            has_chinese1 = bool(re.search(r"[\u4e00-\u9fff]", part1))
            has_chinese2 = bool(re.search(r"[\u4e00-\u9fff]", part2))
            if has_chinese1 and not has_chinese2:
                desc, pdm = part1, part2
            elif has_chinese2 and not has_chinese1:
                desc, pdm = part2, part1
            else:
                pdm, desc = part1, part2
    else:
        match = re.match(r"^([A-Za-z0-9\-\.]+)(.*)", clean_theme)
        if match:
            prefix, suffix = match.groups()
            if prefix and suffix:
                pdm = prefix
                desc = suffix.strip()
            elif re.match(r"^[A-Za-z0-9\-\.]+$", clean_theme):
                pdm = clean_theme
            else:
                desc = clean_theme
        elif re.match(r"^[A-Za-z0-9\-\.]+$", clean_theme):
            pdm = clean_theme
        else:
            desc = clean_theme

    return pdm, desc


def _resolve_pdm_and_desc(
    theme_group: pd.DataFrame,
    col_idx: dict[str, int],
    theme_value: str,
) -> tuple[str, str]:
    """确定图号和物料描述：优先使用文件列，否则从订单主题解析。

    Args:
        theme_group: 需要解析的订单主题对应的数据块 DataFrame.
        col_idx: 表头列名到列索引的映射表.
        theme_value: 订单主题内容字符串.

    Returns:
        A tuple of (pdm, desc).
    """
    pdm = ""
    desc = ""

    if "产品型号" in col_idx:
        pdm_values = theme_group[col_idx["产品型号"]].dropna().unique()
        pdm = str(pdm_values[0]) if len(pdm_values) > 0 else ""
    elif "PDM图号" in col_idx:
        pdm_values = theme_group[col_idx["PDM图号"]].dropna().unique()
        pdm = str(pdm_values[0]) if len(pdm_values) > 0 else ""

    if "产品名称" in col_idx:
        desc_values = theme_group[col_idx["产品名称"]].dropna().unique()
        desc = str(desc_values[0]) if len(desc_values) > 0 else ""

    if (not pdm or not desc) and "订单主题" in col_idx:
        parsed_pdm, parsed_desc = parse_theme(theme_value)
        if not pdm:
            pdm = parsed_pdm
        if not desc:
            desc = parsed_desc

    return pdm, desc


def _clean_text(value: object) -> str:
    """将单元格值转为去空格文本，过滤 pandas 空值。"""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text == "nan" else text


def _normalize_order_id(value: object) -> str:
    """从派工主题中提取用于展示的派工序列。"""
    text = _clean_text(value)
    if not text:
        return ""

    match = re.search(r"DD_[A-Za-z0-9]+", text)
    return match.group(0) if match else text


def _resolve_order_col(col_idx: dict[str, int]) -> int | None:
    """派工主题来自独立的派工主题列。"""
    if "派工主题" in col_idx:
        return col_idx["派工主题"]
    return None


def _resolve_row_product(row: pd.Series, col_idx: dict[str, int]) -> tuple[str, str]:
    """从单行数据中解析唯一产品键：(图号, 产品名称)。"""
    theme_value = _clean_text(row[col_idx["订单主题"]]) if "订单主题" in col_idx else ""

    pdm = ""
    if "产品型号" in col_idx:
        pdm = _clean_text(row[col_idx["产品型号"]])

    desc = _clean_text(row[col_idx["产品名称"]]) if "产品名称" in col_idx else ""

    if (not pdm or not desc) and theme_value:
        parsed_pdm, parsed_desc = parse_theme(theme_value)
        pdm = pdm or parsed_pdm
        desc = desc or parsed_desc

    if not pdm and not desc:
        desc = theme_value or str(row.name)

    return pdm, desc


def _format_product_label(product_key: tuple[str, str]) -> str:
    """将产品键格式化为用户可读的提示文本。"""
    pdm, desc = product_key
    if pdm and desc:
        return f"{desc}（{pdm}）"
    return desc or pdm


def _unique_clean_values(series: pd.Series) -> list[str]:
    """按出现顺序返回非空去重文本。"""
    values: list[str] = []
    for value in series.tolist():
        text = _clean_text(value)
        if text and text not in values:
            values.append(text)
    return values


def _collect_product_group_indices(data: pd.DataFrame, col_idx: dict[str, int]) -> dict[str, list[object]]:
    """按产品型号收集原始行索引，保留源文件出现顺序。"""
    product_groups: dict[str, list[object]] = {}
    for row_index, row in data.iterrows():
        product_model, desc = _resolve_row_product(row, col_idx)
        product_key = product_model or desc or str(row_index)
        product_groups.setdefault(product_key, []).append(row_index)
    return product_groups


def _resolve_group_theme_value(product_group: pd.DataFrame, col_idx: dict[str, int], product_model: str) -> str:
    """为兼容旧文件 fallback 保留主题文本；输出不再展示订单主题。"""
    if "订单主题" in col_idx:
        themes = _unique_clean_values(product_group[col_idx["订单主题"]])
        if themes:
            return " / ".join(themes)
    return product_model


def validate_dispatch_product_name_conflicts(data: pd.DataFrame, col_idx: dict[str, int]) -> list[str]:
    """校验是否存在同一派工主题对应多个产品。"""
    order_col = _resolve_order_col(col_idx)
    if order_col is None:
        return []

    order_to_products: dict[str, list[tuple[str, str]]] = {}
    for _, row in data.iterrows():
        order_id = _normalize_order_id(row[order_col])
        product_key = _resolve_row_product(row, col_idx)
        if not order_id or not _format_product_label(product_key):
            continue
        products = order_to_products.setdefault(order_id, [])
        if product_key not in products:
            products.append(product_key)

    warnings: list[str] = []
    for order_id, product_keys in order_to_products.items():
        if len(product_keys) <= 1:
            continue
        products_text = "、".join(_format_product_label(product_key) for product_key in product_keys)
        warning = f"同一派工主题 {order_id} 对应了多个产品型号：{products_text}。系统会按产品型号分开处理，请复核源表数据。"
        logger.warning("数据校验提示：%s", warning)
        warnings.append(warning)

    return warnings


def process_theme_group(
    theme_group: pd.DataFrame,
    col_idx: dict[str, int],
    theme_value: str,
) -> PartDispatchResult | None:
    """处理一个产品型号分组，计算各工序的待处理量。

    Args:
        theme_group: 需要处理的数据块 DataFrame.
        col_idx: 表头列名到列索引的映射表.
        theme_value: 当前产品型号关联的订单主题文本，仅用于兼容 fallback.

    Returns:
        包含 PDM、描述、工序步骤等信息的 PartDispatchResult；如果无有效工序则返回 None.
    """
    proc_col = col_idx["加工工序"]
    qty_col = col_idx["派工数量"]
    qual_col = col_idx["合格数量"]

    # 派工主题是独立字段，不从订单主题或订单编号兼容读取
    order_col = _resolve_order_col(col_idx)
    order_id_list: list[str] = []
    if order_col is not None:
        for value in theme_group[order_col].unique():
            order_id = _normalize_order_id(value)
            if order_id and order_id not in order_id_list:
                order_id_list.append(order_id)
    order_ids = " / ".join(order_id_list)

    # 产品型号 & 产品名称
    pdm, desc = _resolve_pdm_and_desc(theme_group, col_idx, theme_value)

    # 总派工量 = 所有【自制】行的派工数量之和
    total_dispatch = theme_group[theme_group[proc_col] == "【自制】"][qty_col].sum()

    # 具体工序（排除【自制】汇总行）
    full_process_list = theme_group[theme_group[proc_col] != "【自制】"]
    if full_process_list.empty:
        return None

    # 保持工序出现顺序
    unique_procs: list[str] = []
    for p in full_process_list[proc_col].tolist():
        p = _clean_text(p)
        if p and p not in unique_procs:
            unique_procs.append(p)

    proc_sums = full_process_list.groupby(proc_col)[qual_col].sum()

    # 计算各工序待处理量（汇总级别，用于输出列）
    steps: list[ProcessStep] = []
    prev_val = total_dispatch

    for i, proc in enumerate(unique_procs):
        total_qual = proc_sums.get(proc, 0.0)
        backlog = (total_dispatch - total_qual) if i == 0 else (prev_val - total_qual)
        backlog = max(0, round(backlog, 0))
        steps.append(ProcessStep(name=proc, qualified=total_qual, pending=backlog))
        prev_val = total_qual

    # 构建派工说明（汇总）
    summary_parts: list[str] = []
    for step in steps:
        if step.pending > 0:
            summary_parts.append(f"待{step.name}：{int(step.pending)}")

    # 构建详细派工说明：按派工主题逐条列出待处理工序
    detail_parts: list[str] = []
    in_progress_total = 0
    if order_col is not None:
        for oid_str in order_id_list:
            order_rows = theme_group[theme_group[order_col].map(_normalize_order_id) == oid_str]
            order_dispatch = order_rows[order_rows[proc_col] == "【自制】"][qty_col].sum()
            order_procs = order_rows[order_rows[proc_col] != "【自制】"]
            if order_procs.empty:
                continue
            order_proc_sums = order_procs.groupby(proc_col)[qual_col].sum()
            prev = order_dispatch

            order_proc_sequence: list[str] = []
            for proc_value in order_procs[proc_col].tolist():
                proc_name = _clean_text(proc_value)
                if proc_name and proc_name not in order_proc_sequence:
                    order_proc_sequence.append(proc_name)

            for j, proc in enumerate(order_proc_sequence):
                qual = order_proc_sums.get(proc, 0.0)
                bl = (order_dispatch - qual) if j == 0 else (prev - qual)
                bl = max(0, round(bl, 0))
                if bl > 0:
                    detail_parts.append(f"{oid_str}: 待{proc} {int(bl)}")
                    in_progress_total += int(bl)
                prev = qual

    return PartDispatchResult(
        order_id=order_ids,
        order_theme=theme_value if "订单主题" in col_idx else "",
        pdm=pdm,
        description=desc,
        steps=steps,
        in_progress_total=in_progress_total,
        dispatch_note="，".join(summary_parts),
        dispatch_note_detail="，".join(detail_parts),
    )


def build_output_dataframe(processed_themes: list[PartDispatchResult]) -> pd.DataFrame:
    """将处理后的产品型号列表构建为带动态表头的输出 DataFrame。

    每个产品型号独立一个区块，共享该产品型号对应工序的表头。

    Args:
        processed_themes: 按产品型号分组处理好的 PartDispatchResult 对象列表.

    Returns:
        生成的用于进一步导出 CSV 和 Excel 的 DataFrame 结构.
    """
    all_rows: list[list[str | int]] = []

    for t in processed_themes:
        # 表头行
        header: list[str | int] = [
            "产品型号",
            "产品名称",
            "在制汇总",
            "派工说明",
            "详细派工说明",
            "派工主题",
        ]
        for step in t.steps:
            header.append(step.name)
            header.append(f"待{step.name}")
        all_rows.append(header)

        # 数据行
        row: list[str | int] = [
            t.pdm,
            t.description,
            t.in_progress_total,
            t.dispatch_note,
            t.dispatch_note_detail,
            t.order_id,
        ]
        for step in t.steps:
            qual = step.qualified
            row.append(int(qual) if isinstance(qual, float) and qual.is_integer() else qual)  # type: ignore[arg-type]
            row.append(step.pending)  # type: ignore[arg-type]
        all_rows.append(row)

        # 空行（区块分隔）
        all_rows.append([""] * len(header))

    return pd.DataFrame(all_rows)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def process_dispatch_data(file_obj: IO[bytes]) -> tuple[bytes, bytes, list[str]]:
    """处理派工进度数据的主入口。

    读取上传的文件，识别表头，清洗并按订单和工序提取待加工作业，
    最后将结果打包为 XLSX 和 CSV 格式的字节流以供下载或进一步处理。

    Args:
        file_obj: 上传的文件对象（需要带 .name 属性标识扩展名，如 .csv, .xls, .xlsx）.

    Returns:
        A tuple containing:
        - xlsx_data: 格式化后的 Excel 字节流.
        - csv_data: UTF-8-SIG 编码的 CSV 字节流.
        - validation_warnings: 处理前置校验提示文案列表.

    Raises:
        ValueError: 当上传不受支持的文件格式，或缺少必需列时触发.
    """
    # 1. 读取文件
    try:
        df = read_uploaded_file(file_obj)
    except ValueError as e:
        raise ValueError(f"文件读取失败: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"无法解析上传的文件 (格式损坏或不受支持)。底层错误: {str(e)}") from e

    # 2. 识别表头
    col_idx, data_start_row = detect_headers(df, REQUIRED_COLS, OPTIONAL_COLS)

    # 3. 提取数据行
    data = df.iloc[data_start_row:].copy()
    if data.empty:
        raise ValueError("文件中没有检测到有效的数据行，请确保表头下方存在派工数据。")

    # 4. 向下填充订单和产品字段，使合并单元格下的工序行也保留所属信息
    for col_name in ("订单主题", "派工主题", "产品名称", "产品型号"):
        if col_name in col_idx:
            data.loc[:, col_idx[col_name]] = data[col_idx[col_name]].ffill()

    # 5. 前置校验
    validation_warnings = validate_dispatch_product_name_conflicts(data, col_idx)

    # 6. 数值清洗
    try:
        data[col_idx["派工数量"]] = clean_numeric_column(data[col_idx["派工数量"]])
        data[col_idx["合格数量"]] = clean_numeric_column(data[col_idx["合格数量"]])
    except Exception as e:
        raise ValueError(f"清洗数值列失败: {str(e)}") from e

    # 7. 按产品型号分组处理。同一产品型号的不同派工主题汇总到同一个输出区块。
    product_groups = _collect_product_group_indices(data, col_idx)
    processed_themes: list[PartDispatchResult] = []
    for product_model, row_indices in product_groups.items():
        theme_group = data.loc[row_indices]
        theme_value = _resolve_group_theme_value(theme_group, col_idx, product_model)

        result = process_theme_group(theme_group, col_idx, theme_value)
        if result is not None:
            processed_themes.append(result)

    if not processed_themes:
        raise ValueError("未能从文件中解析出任何有效的自制排活工序，请检查【自制】行数据及其后继工序是否完整。")

    # 8. 构建输出
    try:
        df_output = build_output_dataframe(processed_themes)
    except Exception as e:
        raise RuntimeError(f"构建导出数据表时发生内部错误: {str(e)}") from e

    # 9. 导出 XLSX
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        df_output.to_excel(writer, index=False, header=False)
    xlsx_data = xlsx_buffer.getvalue()

    # 10. 导出 CSV
    csv_buffer = io.StringIO()
    df_output.to_csv(csv_buffer, index=False, header=False, encoding="utf-8-sig")
    csv_data = csv_buffer.getvalue().encode("utf-8-sig")

    return xlsx_data, csv_data, validation_warnings
