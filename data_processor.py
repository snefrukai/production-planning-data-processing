import pandas as pd
import re
import io
import csv

def process_dispatch_data(file_obj):
    """
    接收上传的文件对象，支持 CSV 和 Excel，处理派工数据，并返回生成好的字节流
    """
    filename = file_obj.name.lower()

    if filename.endswith('.csv'):
        df = pd.read_csv(file_obj, header=None)
    elif filename.endswith('.xls') or filename.endswith('.xlsx'):
        df = pd.read_excel(file_obj, header=None)
    else:
        raise ValueError("不支持的文件格式，请上传 .csv, .xls 或 .xlsx 文件")

    # 读取表头（支持多行列头）
    required_cols = ['订单主题', '派工数量', '加工工序', '合格数量']
    optional_cols = ['订单编号', 'PDM图号', '产品名称']
    all_cols = required_cols + optional_cols

    # 获取前两行
    row1 = df.iloc[0].astype(str).tolist()
    row2 = df.iloc[1].astype(str).tolist() if len(df) > 1 else None

    # 清理列名
    row1 = [s.strip() if s else '' for s in row1]
    row2 = [s.strip() if s else '' for s in row2] if row2 else None

    # 动态扫描：构建列名到索引的映射
    col_idx = {}
    row2_has_header = False

    # 扫描row1
    for idx, val in enumerate(row1):
        if val in all_cols:
            col_idx[val] = idx

    # 扫描row2，补充缺失的列
    if row2:
        for idx, val in enumerate(row2):
            if val in all_cols and val not in col_idx:
                col_idx[val] = idx
                row2_has_header = True

    # 确定数据起始行
    header_row_idx = 1 if row2_has_header else 0

    # 验证必需列
    missing_cols = [col for col in required_cols if col not in col_idx]
    if missing_cols:
        raise ValueError(f"文件缺少必要的列: {missing_cols}。请检查文件格式是否正确。")

    # 处理订单主题的填充（如果存在）
    if '订单主题' in col_idx:
        df[col_idx['订单主题']] = df[col_idx['订单主题']].ffill()

    # 处理订单编号的填充（如果存在）
    if '订单编号' in col_idx:
        df[col_idx['订单编号']] = df[col_idx['订单编号']].ffill()

    data = df.iloc[header_row_idx + 1:].copy()

    def to_num(x):
        try:
            if pd.isna(x): return 0.0
            return float(str(x).replace(',', ''))
        except:
            return 0.0

    data[col_idx['派工数量']] = data[col_idx['派工数量']].apply(to_num)
    data[col_idx['合格数量']] = data[col_idx['合格数量']].apply(to_num)

    def parse_theme(theme_str):
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
            # 尝试提取前缀作为PDM（连续的数字字母混合）
            # 例如："18412H51300二次空气管法兰" -> PDM: "18412H51300", 描述: "二次空气管法兰"
            match = re.match(r'^([A-Za-z0-9\-\.]+)(.*)', clean_theme)
            if match:
                prefix, suffix = match.groups()
                if prefix and suffix:
                    # 前缀作为PDM，后缀作为描述
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

    # 确定用于分组的列（订单主题或使用索引）
    if '订单主题' in col_idx:
        theme_col = col_idx['订单主题']
        themes = data[theme_col].unique()
    else:
        # 如果没有订单主题，使用行索引作为分组键
        themes = data.index.unique()

    processed_themes = []

    for theme in themes:
        if '订单主题' in col_idx:
            theme_col = col_idx['订单主题']
            theme_group = data[data[theme_col] == theme]
        else:
            theme_group = data

        # 订单编号（可选）
        if '订单编号' in col_idx:
            order_col = col_idx['订单编号']
            order_ids = " / ".join(theme_group[order_col].unique())
        else:
            order_ids = ""

        # PDM图号和产品名称（优先使用文件中的值，否则从订单主题解析）
        if 'PDM图号' in col_idx:
            pdm_col = col_idx['PDM图号']
            pdm_values = theme_group[pdm_col].dropna().unique()
            pdm = str(pdm_values[0]) if len(pdm_values) > 0 else ""
        else:
            pdm = ""

        if '产品名称' in col_idx:
            desc_col = col_idx['产品名称']
            desc_values = theme_group[desc_col].dropna().unique()
            desc = str(desc_values[0]) if len(desc_values) > 0 else ""
        else:
            desc = ""

        # 如果PDM图号或产品名称为空，则从订单主题解析
        if not pdm or not desc:
            if '订单主题' in col_idx:
                parsed_pdm, parsed_desc = parse_theme(theme)
                if not pdm:
                    pdm = parsed_pdm
                if not desc:
                    desc = parsed_desc

        # 使用列名访问
        proc_col = col_idx['加工工序']
        qty_col = col_idx['派工数量']
        qual_col = col_idx['合格数量']

        total_dispatch = theme_group[theme_group[proc_col] == '【自制】'][qty_col].sum()
        full_process_list = theme_group[theme_group[proc_col] != '【自制】']

        if full_process_list.empty:
            continue

        unique_procs = []
        for p in full_process_list[proc_col].tolist():
            p = str(p).strip()
            if p not in unique_procs:
                unique_procs.append(p)

        proc_sums = full_process_list.groupby(proc_col)[qual_col].sum()

        # 获取订单主题的值（如果存在）
        theme_value = theme if '订单主题' in col_idx else ""

        theme_entry = {
            '订单编号': order_ids, '订单主题': theme_value,
            'PDM图号': pdm, '物料描述': desc, 'steps': []
        }

        prev_val = total_dispatch
        description_parts = []

        for i, proc in enumerate(unique_procs):
            total_qual = proc_sums.get(proc, 0.0)
            backlog = total_dispatch - total_qual if i == 0 else prev_val - total_qual
            backlog = max(0, round(backlog, 0))

            theme_entry['steps'].append({'name': proc, 'qual': total_qual, 'pending': backlog})
            if backlog > 0:
                description_parts.append(f"待{proc}：{int(backlog)}")
            prev_val = total_qual

        theme_entry['说明'] = "，".join(description_parts)
        processed_themes.append(theme_entry)

    blocks = {}
    for theme_res in processed_themes:
        seq_key = tuple(theme_res['steps'][i]['name'] for i in range(len(theme_res['steps'])))
        if seq_key not in blocks:
            blocks[seq_key] = []
        blocks[seq_key].append(theme_res)

    # 构建数据列表用于生成DataFrame
    all_rows = []

    for seq, theme_list in blocks.items():
        # 表头
        header = ['PDM图号', '物料描述', '说明', '订单主题', '订单编号']
        for proc in seq:
            header.append(proc)
            header.append(f"待{proc}")
        all_rows.append(header)

        # 数据行
        for t in theme_list:
            row = [t['PDM图号'], t['物料描述'], t['说明'], t['订单主题'], t['订单编号']]
            for step in t['steps']:
                row.append(int(step['qual']) if step['qual'].is_integer() else step['qual'])
                row.append(int(step['pending']))
            all_rows.append(row)

        # 空行
        all_rows.append([''] * len(header))

    # 创建DataFrame
    df_output = pd.DataFrame(all_rows)

    # 导出为XLSX
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine='openpyxl') as writer:
        df_output.to_excel(writer, index=False, header=False)
    xlsx_buffer.seek(0)
    xlsx_data = xlsx_buffer.getvalue()

    # 导出为CSV
    csv_buffer = io.StringIO()
    df_output.to_csv(csv_buffer, index=False, header=False, encoding='utf-8-sig')
    csv_data = csv_buffer.getvalue().encode('utf-8-sig')

    return xlsx_data, csv_data