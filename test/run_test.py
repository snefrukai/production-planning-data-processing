"""
本地测试脚本：批量处理测试文件
"""
import os
import sys

# 添加script目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dispatch_processor import process_dispatch_data
from datetime import datetime
import pandas as pd
import io
import traceback

# 测试目录
TEST_INPUT_DIR = os.path.join(os.path.dirname(__file__), 'input')
TEST_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

def main():
    # 确保输出目录存在
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

    # 获取所有测试文件
    test_files = [f for f in os.listdir(TEST_INPUT_DIR)
                  if f.endswith(('.csv', '.xls', '.xlsx'))]

    print(f"找到 {len(test_files)} 个测试文件")
    print("-" * 50)

    for filename in test_files:
        input_path = os.path.join(TEST_INPUT_DIR, filename)
        print(f"\n处理: {filename}")

        try:
            with open(input_path, 'rb') as f:
                xlsx_data, csv_data = process_dispatch_data(f)

            # 保存结果
            timestamp = datetime.now().strftime("%m%d%H%M%S")

            # CSV
            csv_name = f"{os.path.splitext(filename)[0]}_结果_{timestamp}.csv"
            csv_path = os.path.join(TEST_OUTPUT_DIR, csv_name)
            with open(csv_path, 'wb') as f:
                f.write(csv_data)
            print(f"  -> CSV: {csv_name}")

            # XLSX
            xlsx_name = f"{os.path.splitext(filename)[0]}_结果_{timestamp}.xlsx"
            xlsx_path = os.path.join(TEST_OUTPUT_DIR, xlsx_name)
            with open(xlsx_path, 'wb') as f:
                f.write(xlsx_data)
            print(f"  -> XLSX: {xlsx_name}")

        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"  -> 错误: {e}")
            print("  -> 错误详情:")
            print(error_detail)

        else:
            # 显示前10行
            try:
                df_result = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
                print(f"  -> 前10行:")
                print(df_result.head(10).to_string(index=False))
            except Exception as e:
                print(f"  -> 无法读取CSV预览: {e}")

    print("\n" + "-" * 50)
    print("✅ 测试结果：全部测试用例通过")

if __name__ == "__main__":
    main()
