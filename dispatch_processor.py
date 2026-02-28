"""
派工进度数据处理模块

处理《派工进度追踪表》，计算各零件各工序的待处理量。
"""
import re
import io
from typing import IO, Dict, List, Tuple

import pandas as pd

from utils import read_uploaded_file, detect_headers, clean_numeric_column


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
REQUIRED_COLS = ['订单主题', '派工数量', '加工工序', '合格数量']
OPTIONAL_COLS = ['订单编号', 'PDM图号', '产品名称']


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def parse_theme(theme_str: str) -> Tuple[str, str]:
    """
    从"订单主题"中解析出 PDM 图号和物料描述。

    规则：
      - 去掉"转自："前缀
      - 若以"/"分隔，通过字符特征判断哪个是 PDM（字母数字），哪个是描述（含中文）
      - 若无分隔符，尝试从开头提取连续字母数字作为 PDM
    """
    clean_theme = re.sub(r'^转自[：:]', '', str(theme_str))
    parts = clean_theme.split('/')

    pdm, desc = "", ""

    if len(parts) >= 2:
        part1, part2 = parts[0].strip(), parts[1].strip()

        if re.match(r'^[A-Za-z0-9\-\.]+$', part1):
            pdm, desc = part1, part2
        elif re.match(r'^[A-Za-z0-9\-\.]+$', part2):
            pdm, desc = part2, part1
        else:
            has_chinese1 = bool(re.search(r'[\u4e00-\u9fff]', part1))
            has_chinese2 = bool(re.search(r'[\u4e00-\u9fff]', part2))
            if has_chinese1 and not has_chinese2:
                desc, pdm = part1, part2
            elif has_chinese2 and not has_chinese1:
                desc, pdm = part2, part1
            else:
                pdm, desc = part1, part2
    else:
        match = re.match(r'^([A-Za-z0-9\-\.]+)(.*)', clean_theme)
        if match:
            prefix, suffix = match.groups()
            if prefix and suffix:
                pdm = prefix
                desc = suffix.strip()
            elif re.match(r'^[A-Za-z0-9\-\.]+$', clean_theme):
                pdm = clean_theme
            else:
                desc = clean_theme
        elif re.match(r'^[A-Za-z0-9\-\.]+$', clean_theme):
            pdm = clean_theme
        else:
            desc = clean_theme

    return pdm, desc


def _resolve_pdm_and_desc(
    theme_group: pd.DataFrame,
    col_idx: Dict[str, int],
    theme_value: str,
) -> Tuple[str, str]:
    """
    确定 PDM 图号和物料描述：
    优先使用文件中的 PDM图号 / 产品名称 列，否则从订单主题解析。
    """
    pdm = ""
    desc = ""

    if 'PDM图号' in col_idx:
        pdm_values = theme_group[col_idx['PDM图号']].dropna().unique()
        pdm = str(pdm_values[0]) if len(pdm_values) > 0 else ""

    if '产品名称' in col_idx:
        desc_values = theme_group[col_idx['产品名称']].dropna().unique()
        desc = str(desc_values[0]) if len(desc_values) > 0 else ""

    if (not pdm or not desc) and '订单主题' in col_idx:
        parsed_pdm, parsed_desc = parse_theme(theme_value)
        if not pdm:
            pdm = parsed_pdm
        if not desc:
            desc = parsed_desc

    return pdm, desc


def process_theme_group(
    theme_group: pd.DataFrame,
    col_idx: Dict[str, int],
    theme_value: str,
) -> dict | None:
    """
    处理一个"订单主题"分组，计算各工序的待处理量。

    Returns:
        包含 PDM、描述、工序步骤等信息的字典；如果无有效工序则返回 None。
    """
    proc_col = col_idx['加工工序']
    qty_col = col_idx['派工数量']
    qual_col = col_idx['合格数量']

    # 订单编号（可选）
    if '订单编号' in col_idx:
        order_ids = " / ".join(
            str(v) for v in theme_group[col_idx['订单编号']].unique()
        )
    else:
        order_ids = ""

    # PDM 图号 & 物料描述
    pdm, desc = _resolve_pdm_and_desc(theme_group, col_idx, theme_value)

    # 总派工量 = 所有【自制】行的派工数量之和
    total_dispatch = theme_group[theme_group[proc_col] == '【自制】'][qty_col].sum()

    # 具体工序（排除【自制】汇总行）
    full_process_list = theme_group[theme_group[proc_col] != '【自制】']
    if full_process_list.empty:
        return None

    # 保持工序出现顺序
    unique_procs: List[str] = []
    for p in full_process_list[proc_col].tolist():
        p = str(p).strip()
        if p not in unique_procs:
            unique_procs.append(p)

    proc_sums = full_process_list.groupby(proc_col)[qual_col].sum()

    # 计算各工序待处理量
    steps: List[dict] = []
    description_parts: List[str] = []
    prev_val = total_dispatch

    for i, proc in enumerate(unique_procs):
        total_qual = proc_sums.get(proc, 0.0)
        backlog = (total_dispatch - total_qual) if i == 0 else (prev_val - total_qual)
        backlog = max(0, round(backlog, 0))

        steps.append({'name': proc, 'qual': total_qual, 'pending': backlog})
        if backlog > 0:
            description_parts.append(f"待{proc}：{int(backlog)}")
        prev_val = total_qual

    return {
        '订单编号': order_ids,
        '订单主题': theme_value if '订单主题' in col_idx else "",
        'PDM图号': pdm,
        '物料描述': desc,
        'steps': steps,
        '派工说明': "，".join(description_parts),
    }


def build_output_dataframe(processed_themes: List[dict]) -> pd.DataFrame:
    """
    将处理后的主题列表按工艺路线分组，构建带动态表头的输出 DataFrame。

    相同工序序列的主题共享一组表头，不同序列之间以空行分隔。
    """
    # 按工序序列分组
    blocks: Dict[tuple, List[dict]] = {}
    for theme_result in processed_themes:
        seq_key = tuple(step['name'] for step in theme_result['steps'])
        blocks.setdefault(seq_key, []).append(theme_result)

    all_rows: List[list] = []

    for seq, theme_list in blocks.items():
        # 表头行
        header = ['PDM图号', '物料描述', '派工说明', '订单主题', '订单编号']
        for proc in seq:
            header.append(proc)
            header.append(f"待{proc}")
        all_rows.append(header)

        # 数据行
        for t in theme_list:
            row = [t['PDM图号'], t['物料描述'], t['派工说明'], t['订单主题'], t['订单编号']]
            for step in t['steps']:
                qual = step['qual']
                row.append(int(qual) if isinstance(qual, float) and qual.is_integer() else qual)
                row.append(int(step['pending']))
            all_rows.append(row)

        # 空行（区块分隔）
        all_rows.append([''] * len(header))

    return pd.DataFrame(all_rows)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def process_dispatch_data(file_obj: IO) -> Tuple[bytes, bytes]:
    """
    处理派工进度数据的主入口。

    Args:
        file_obj: 上传的文件对象（需带 .name 属性）

    Returns:
        (xlsx_data, csv_data) — 分别为 XLSX 和 CSV 格式的字节流
    """
    # 1. 读取文件
    df = read_uploaded_file(file_obj)

    # 2. 识别表头
    col_idx, data_start_row = detect_headers(df, REQUIRED_COLS, OPTIONAL_COLS)

    # 3. 向下填充（订单主题、订单编号）
    for col_name in ('订单主题', '订单编号'):
        if col_name in col_idx:
            df[col_idx[col_name]] = df[col_idx[col_name]].ffill()

    # 4. 提取数据行 & 数值清洗
    data = df.iloc[data_start_row:].copy()
    data[col_idx['派工数量']] = clean_numeric_column(data[col_idx['派工数量']])
    data[col_idx['合格数量']] = clean_numeric_column(data[col_idx['合格数量']])

    # 5. 按订单主题分组处理
    if '订单主题' in col_idx:
        themes = data[col_idx['订单主题']].unique()
    else:
        themes = data.index.unique()

    processed_themes: List[dict] = []
    for theme in themes:
        if '订单主题' in col_idx:
            theme_group = data[data[col_idx['订单主题']] == theme]
        else:
            theme_group = data

        result = process_theme_group(theme_group, col_idx, theme)
        if result is not None:
            processed_themes.append(result)

    # 6. 构建输出
    df_output = build_output_dataframe(processed_themes)

    # 7. 导出 XLSX
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine='openpyxl') as writer:
        df_output.to_excel(writer, index=False, header=False)
    xlsx_data = xlsx_buffer.getvalue()

    # 8. 导出 CSV
    csv_buffer = io.StringIO()
    df_output.to_csv(csv_buffer, index=False, header=False, encoding='utf-8-sig')
    csv_data = csv_buffer.getvalue().encode('utf-8-sig')

    return xlsx_data, csv_data
