"""
pytest 测试框架 - 公共工具模块 (utils.py)
"""
import pytest
import os
import sys
import pandas as pd

# 添加script目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from utils import read_uploaded_file, detect_headers, clean_numeric_column


class TestReadUploadedFile:
    """测试文件读取"""

    def test_read_xls(self):
        """测试读取 .xls 文件"""
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'input', '派工进度追踪表_赵淑君.xls')

        with open(filepath, 'rb') as f:
            df = read_uploaded_file(f)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_read_xlsx(self):
        """测试读取 .xlsx 文件"""
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'input', '派工进度追踪表_赵淑君 (1).xlsx')

        with open(filepath, 'rb') as f:
            df = read_uploaded_file(f)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_unsupported_format(self):
        """测试不支持的文件格式应抛出异常"""

        class MockFile:
            def __init__(self, name):
                self.name = name

        with pytest.raises(ValueError, match="不支持的文件格式"):
            read_uploaded_file(MockFile("test.txt"))


class TestDetectHeaders:
    """测试表头识别"""

    def test_detect_required_cols(self):
        """测试必需列识别"""
        df = pd.DataFrame([
            ['订单主题', '派工数量', '加工工序', '合格数量'],
            ['主题1', 100, '落料', 80],
        ])
        required = ['订单主题', '派工数量', '加工工序', '合格数量']
        col_idx, data_start = detect_headers(df, required, [])

        assert '订单主题' in col_idx
        assert '派工数量' in col_idx
        assert '加工工序' in col_idx
        assert '合格数量' in col_idx
        assert data_start == 1

    def test_detect_optional_cols(self):
        """测试可选列识别"""
        df = pd.DataFrame([
            ['订单主题', '派工数量', '加工工序', '合格数量', 'PDM图号'],
            ['主题1', 100, '落料', 80, 'ABC123'],
        ])
        required = ['订单主题', '派工数量', '加工工序', '合格数量']
        optional = ['PDM图号', '产品名称']
        col_idx, _ = detect_headers(df, required, optional)

        assert 'PDM图号' in col_idx
        assert '产品名称' not in col_idx

    def test_missing_required_col_raises(self):
        """测试缺少必需列应抛出 ValueError"""
        df = pd.DataFrame([
            ['订单主题', '订单编号'],
            ['主题1', 'DD001'],
        ])
        required = ['订单主题', '派工数量', '加工工序', '合格数量']

        with pytest.raises(ValueError, match="缺少必要的列"):
            detect_headers(df, required, [])

    def test_multirow_header(self):
        """测试多行列头"""
        df = pd.DataFrame([
            ['订单主题', '派工数量', '', ''],
            ['', '', '加工工序', '合格数量'],
            ['主题1', 100, '落料', 80],
        ])
        required = ['订单主题', '派工数量', '加工工序', '合格数量']
        col_idx, data_start = detect_headers(df, required, [])

        assert len(col_idx) == 4
        assert data_start == 2  # 数据从第三行开始


class TestCleanNumericColumn:
    """测试数值清洗"""

    def test_normal_numbers(self):
        """测试普通数值"""
        s = pd.Series([1, 2, 3])
        result = clean_numeric_column(s)
        assert list(result) == [1.0, 2.0, 3.0]

    def test_comma_separated(self):
        """测试含逗号的数值"""
        s = pd.Series(['1,000', '2,500', '10,000'])
        result = clean_numeric_column(s)
        assert list(result) == [1000.0, 2500.0, 10000.0]

    def test_nan_values(self):
        """测试空值填充为0"""
        s = pd.Series([None, float('nan'), ''])
        result = clean_numeric_column(s)
        assert list(result) == [0.0, 0.0, 0.0]

    def test_non_numeric_values(self):
        """测试非数值填充为0"""
        s = pd.Series(['abc', '---', 'N/A'])
        result = clean_numeric_column(s)
        assert list(result) == [0.0, 0.0, 0.0]

    def test_mixed_values(self):
        """测试混合值"""
        s = pd.Series([100, '2,000', None, 'abc', 50.5])
        result = clean_numeric_column(s)
        assert list(result) == [100.0, 2000.0, 0.0, 0.0, 50.5]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
