"""
派工进度数据处理模块

处理《派工进度追踪表》，计算各零件各工序的待处理量。
"""

import io
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
REQUIRED_COLS = ["订单主题", "派工数量", "加工工序", "合格数量"]
OPTIONAL_COLS = ["订单编号", "PDM图号", "产品名称"]


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
    """确定 PDM 图号和物料描述：优先使用文件列，否则从订单主题解析。

    Args:
        theme_group: 需要解析的订单主题对应的数据块 DataFrame.
        col_idx: 表头列名到列索引的映射表.
        theme_value: 订单主题内容字符串.

    Returns:
        A tuple of (pdm, desc).
    """
    pdm = ""
    desc = ""

    if "PDM图号" in col_idx:
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


def process_theme_group(
    theme_group: pd.DataFrame,
    col_idx: dict[str, int],
    theme_value: str,
) -> PartDispatchResult | None:
    """处理一个"订单主题"分组，计算各工序的待处理量。

    Args:
        theme_group: 需要处理的数据块 DataFrame.
        col_idx: 表头列名到列索引的映射表.
        theme_value: 当前订单主题名称.

    Returns:
        包含 PDM、描述、工序步骤等信息的 PartDispatchResult；如果无有效工序则返回 None.
    """
    proc_col = col_idx["加工工序"]
    qty_col = col_idx["派工数量"]
    qual_col = col_idx["合格数量"]

    # 订单编号（可选）
    order_ids = " / ".join(str(v) for v in theme_group[col_idx["订单编号"]].unique()) if "订单编号" in col_idx else ""

    # PDM 图号 & 物料描述
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
        p = str(p).strip()
        if p not in unique_procs:
            unique_procs.append(p)

    proc_sums = full_process_list.groupby(proc_col)[qual_col].sum()

    # 计算各工序待处理量
    steps: list[ProcessStep] = []
    description_parts: list[str] = []
    prev_val = total_dispatch

    for i, proc in enumerate(unique_procs):
        total_qual = proc_sums.get(proc, 0.0)
        backlog = (total_dispatch - total_qual) if i == 0 else (prev_val - total_qual)
        backlog = max(0, round(backlog, 0))

        steps.append(ProcessStep(name=proc, qualified=total_qual, pending=backlog))
        if backlog > 0:
            description_parts.append(f"待{proc}：{int(backlog)}")
        prev_val = total_qual

    return PartDispatchResult(
        order_id=order_ids,
        order_theme=theme_value if "订单主题" in col_idx else "",
        pdm=pdm,
        description=desc,
        steps=steps,
        dispatch_note="，".join(description_parts),
    )


def build_output_dataframe(processed_themes: list[PartDispatchResult]) -> pd.DataFrame:
    """将处理后的主题列表按工艺路线分组，构建带动态表头的输出 DataFrame。

    相同工序序列的主题共享一组表头，不同序列之间以空行分隔。

    Args:
        processed_themes: 按订单分组处理好的 PartDispatchResult 对象列表.

    Returns:
        生成的用于进一步导出 CSV 和 Excel 的 DataFrame 结构.
    """
    # 按工序序列分组
    blocks: dict[tuple[str, ...], list[PartDispatchResult]] = {}
    for theme_result in processed_themes:
        seq_key = tuple(step.name for step in theme_result.steps)
        blocks.setdefault(seq_key, []).append(theme_result)

    all_rows: list[list[str | int]] = []

    for seq, theme_list in blocks.items():
        # 表头行
        header: list[str | int] = ["PDM图号", "物料描述", "派工说明", "订单主题", "订单编号"]
        for proc in seq:
            header.append(proc)
            header.append(f"待{proc}")
        all_rows.append(header)

        # 数据行
        for t in theme_list:
            row: list[str | int] = [t.pdm, t.description, t.dispatch_note, t.order_theme, t.order_id]
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


def process_dispatch_data(file_obj: IO[bytes]) -> tuple[bytes, bytes]:
    """处理派工进度数据的主入口。

    读取上传的文件，识别表头，清洗并按订单和工序提取待加工作业，
    最后将结果打包为 XLSX 和 CSV 格式的字节流以供下载或进一步处理。

    Args:
        file_obj: 上传的文件对象（需要带 .name 属性标识扩展名，如 .csv, .xls, .xlsx）.

    Returns:
        A tuple containing:
        - xlsx_data: 格式化后的 Excel 字节流.
        - csv_data: UTF-8-SIG 编码的 CSV 字节流.

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

    # 3. 向下填充（订单主题、订单编号）
    for col_name in ("订单主题", "订单编号"):
        if col_name in col_idx:
            df[col_idx[col_name]] = df[col_idx[col_name]].ffill()

    # 4. 提取数据行 & 数值清洗
    data = df.iloc[data_start_row:].copy()
    if data.empty:
        raise ValueError("文件中没有检测到有效的数据行，请确保表头下方存在派工数据。")

    try:
        data[col_idx["派工数量"]] = clean_numeric_column(data[col_idx["派工数量"]])
        data[col_idx["合格数量"]] = clean_numeric_column(data[col_idx["合格数量"]])
    except Exception as e:
        raise ValueError(f"清洗数值列失败: {str(e)}") from e

    # 5. 按订单主题分组处理
    themes = data[col_idx["订单主题"]].unique() if "订单主题" in col_idx else data.index.unique()

    processed_themes: list[PartDispatchResult] = []
    for theme in themes:
        theme_group = data[data[col_idx["订单主题"]] == theme] if "订单主题" in col_idx else data

        result = process_theme_group(theme_group, col_idx, str(theme))
        if result is not None:
            processed_themes.append(result)

    if not processed_themes:
        raise ValueError("未能从文件中解析出任何有效的自制排活工序，请检查【自制】行数据及其后继工序是否完整。")

    # 6. 构建输出
    try:
        df_output = build_output_dataframe(processed_themes)
    except Exception as e:
        raise RuntimeError(f"构建导出数据表时发生内部错误: {str(e)}") from e

    # 7. 导出 XLSX
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        df_output.to_excel(writer, index=False, header=False)
    xlsx_data = xlsx_buffer.getvalue()

    # 8. 导出 CSV
    csv_buffer = io.StringIO()
    df_output.to_csv(csv_buffer, index=False, header=False, encoding="utf-8-sig")
    csv_data = csv_buffer.getvalue().encode("utf-8-sig")

    return xlsx_data, csv_data
