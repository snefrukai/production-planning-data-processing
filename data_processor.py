import pandas as pd
import re
import io
import csv

def process_dispatch_data(file_obj):
    """
    接收上传的文件对象，支持 CSV 和 Excel，处理派工数据，并返回生成好的 CSV 字节流
    """
    filename = file_obj.name.lower()
    
    if filename.endswith('.csv'):
        df = pd.read_csv(file_obj, header=None)
    elif filename.endswith('.xls') or filename.endswith('.xlsx'):
        df = pd.read_excel(file_obj, header=None)
    else:
        raise ValueError("不支持的文件格式，请上传 .csv, .xls 或 .xlsx 文件")
    
    df[0] = df[0].ffill()
    df[1] = df[1].ffill()
    data = df.iloc[2:].copy()

    def to_num(x):
        try:
            if pd.isna(x): return 0.0
            return float(str(x).replace(',', ''))
        except:
            return 0.0

    data[10] = data[10].apply(to_num)
    data[12] = data[12].apply(to_num)

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
            if re.match(r'^[A-Za-z0-9\-\.]+$', clean_theme):
                pdm = clean_theme
            else:
                desc = clean_theme
        return pdm, desc

    themes = data[0].unique()
    processed_themes = []

    for theme in themes:
        theme_group = data[data[0] == theme]
        order_ids = " / ".join(theme_group[1].unique())
        pdm, desc = parse_theme(theme)
        
        total_dispatch = theme_group[theme_group[11] == '【自制】'][10].sum()
        full_process_list = theme_group[theme_group[11] != '【自制】']
        
        if full_process_list.empty:
            continue
        
        unique_procs = []
        for p in full_process_list[11].tolist():
            p = str(p).strip()
            if p not in unique_procs:
                unique_procs.append(p)
                
        proc_sums = full_process_list.groupby(11)[12].sum()
        
        theme_entry = {
            '订单编号': order_ids, '订单主题': theme, 
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

    output_buffer = io.StringIO()
    writer = csv.writer(output_buffer)
    
    for seq, theme_list in blocks.items():
        # ⚠️ 此处更新了表头顺序，前3列为 PDM图号、物料描述、说明
        header = ['PDM图号', '物料描述', '说明', '订单编号', '订单主题']
        for proc in seq:
            header.append(proc)
            header.append(f"待{proc}")
        writer.writerow(header)
        
        for t in theme_list:
            # ⚠️ 此处对应更新了数据行的输出顺序
            row = [t['PDM图号'], t['物料描述'], t['说明'], t['订单编号'], t['订单主题']]
            for step in t['steps']:
                row.append(int(step['qual']) if step['qual'].is_integer() else step['qual'])
                row.append(int(step['pending']))
            writer.writerow(row)
        writer.writerow([]) 

    return output_buffer.getvalue().encode('utf-8-sig')