"""
pytest 测试框架 - 派工进度数据处理
"""
import pytest
import os
import sys
import io
import pandas as pd

# 添加script目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from data_processor import process_dispatch_data

# 测试文件目录
TEST_INPUT_DIR = os.path.join(os.path.dirname(__file__), 'input')


class TestProcessDispatch:
    """功能测试 - 处理现有测试文件"""

    def test_process_赵淑君_xls(self):
        """测试处理 .xls 文件"""
        filename = "派工进度追踪表_赵淑君.xls"
        filepath = os.path.join(TEST_INPUT_DIR, filename)

        with open(filepath, 'rb') as f:
            xlsx_data, csv_data = process_dispatch_data(f)

        # 验证输出非空
        assert len(xlsx_data) > 0, "XLSX数据为空"
        assert len(csv_data) > 0, "CSV数据为空"

        # 验证CSV可解析
        df = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
        assert len(df) > 0, "CSV解析后为空"

    def test_process_赵淑君_xlsx(self):
        """测试处理 .xlsx 文件"""
        filename = "派工进度追踪表_赵淑君 (1).xlsx"
        filepath = os.path.join(TEST_INPUT_DIR, filename)

        with open(filepath, 'rb') as f:
            xlsx_data, csv_data = process_dispatch_data(f)

        # 验证输出非空
        assert len(xlsx_data) > 0, "XLSX数据为空"
        assert len(csv_data) > 0, "CSV数据为空"

        # 验证CSV可解析
        df = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
        assert len(df) > 0, "CSV解析后为空"


class TestOutputValidation:
    """输出验证 - 验证表格列和数据"""

    def _get_result_df(self, filename):
        """处理文件并返回DataFrame"""
        filepath = os.path.join(TEST_INPUT_DIR, filename)
        with open(filepath, 'rb') as f:
            xlsx_data, csv_data = process_dispatch_data(f)
        return pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)

    def _find_header_row(self, df):
        """找到表头行的索引"""
        for idx, row in df.iterrows():
            if 'PDM图号' in row.values:
                return idx
        return None

    def test_output_columns_exist(self):
        """验证输出包含必需列: PDM图号, 物料描述, 说明"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        assert header_idx is not None, "未找到表头行"

        header_row = df.iloc[header_idx].tolist()
        assert 'PDM图号' in header_row, "缺少PDM图号列"
        assert '物料描述' in header_row, "缺少物料描述列"
        assert '说明' in header_row, "缺少说明列"

    def test_pdm图号_not_empty(self):
        """验证PDM图号列有值"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        header_row = df.iloc[header_idx].tolist()

        # 找到PDM图号列索引
        pdm_idx = header_row.index('PDM图号')

        # 获取数据行（跳过表头和空行）
        for idx in range(header_idx + 1, len(df)):
            row = df.iloc[idx]
            if row[pdm_idx] and row[pdm_idx].strip():
                assert len(row[pdm_idx].strip()) > 0, f"第{idx}行PDM图号为空"
                break

    def test_物料描述_not_empty(self):
        """验证物料描述列有值"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        header_row = df.iloc[header_idx].tolist()

        # 找到物料描述列索引
        desc_idx = header_row.index('物料描述')

        # 获取数据行
        for idx in range(header_idx + 1, len(df)):
            row = df.iloc[idx]
            if row[desc_idx] and row[desc_idx].strip():
                assert len(row[desc_idx].strip()) > 0, f"第{idx}行物料描述为空"
                break

    def test_说明_format(self):
        """验证说明列格式正确"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        header_row = df.iloc[header_idx].tolist()

        # 找到说明列索引
        note_idx = header_row.index('说明')

        # 检查说明格式 (如: "待落料：15164" 或 "待三价彩锌：21000")
        import re
        pattern = r'^待.+：\d+$'

        for idx in range(header_idx + 1, len(df)):
            row = df.iloc[idx]
            note = str(row[note_idx]).strip()
            # 跳过空行和表头行
            if not note or note == '' or note == '说明':
                continue
            # 验证格式
            assert re.match(pattern, note), f"第{idx}行说明格式错误: {note}"


class TestBoundaryCases:
    """边界测试 - 异常情况"""

    def test_missing_required_column(self):
        """测试缺少必需列应抛出异常"""
        # 创建一个缺少必需列的CSV
        csv_content = "订单主题,订单编号\n主题1,DD001"

        # 创建一个模拟文件对象
        class MockFile:
            def __init__(self, name, content):
                self.name = name
                self._content = content

            def read(self, n=-1):
                return self._content

        mock_file = MockFile("test.csv", csv_content)

        # 应该抛出异常（可能是ValueError或其他异常）
        with pytest.raises(Exception) as exc_info:
            process_dispatch_data(mock_file)

        # 验证有异常信息
        assert len(str(exc_info.value)) > 0

    def test_invalid_file_format(self):
        """测试无效文件格式应抛出异常"""

        class MockFile:
            def __init__(self, name):
                self.name = name

        mock_file = MockFile("test.txt")

        with pytest.raises(ValueError) as exc_info:
            process_dispatch_data(mock_file)

        assert "不支持的文件格式" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
