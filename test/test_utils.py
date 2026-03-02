"""
pytest 测试框架 - 公共工具模块 (utils.py)
"""

import os
import sys
from typing import IO, Any

import pandas as pd
import pytest

# 添加script目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utils import clean_numeric_column, detect_headers, read_uploaded_file


class TestReadUploadedFile:
    """测试文件读取"""

    def test_read_xls(self) -> None:
        """测试读取 .xls 文件"""
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input", "派工进度追踪表_赵淑君.xls")

        with open(filepath, "rb") as f:
            df = read_uploaded_file(f)

        assert not df.empty, "DataFrame 应包含数据"
        assert len(df) > 0

    def test_read_xlsx(self) -> None:
        """测试读取 .xlsx 文件"""
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input", "派工进度追踪表_赵淑君 (1).xlsx")

        with open(filepath, "rb") as f:
            df = read_uploaded_file(f)

        assert not df.empty, "DataFrame 应包含数据"
        assert len(df) > 0

    def test_unsupported_format(self) -> None:
        """测试读取不支持的文件格式应抛出异常"""

        class MockFile:
            name = "test.txt"

            def read(self) -> bytes:
                return b"some content"

            def readlines(self) -> list[bytes]:
                return [b"some content"]

            def seek(self, offset: int, whence: int = 0) -> int:
                return 0

            def __enter__(self) -> IO[bytes]:
                return self  # type: ignore[return-value]

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        # 由于 MockFile 不符合 pandas 的要求，实际测试的是其是否能引发 ValueError 或其他文件异常
        with pytest.raises((ValueError, Exception)):
            read_uploaded_file(MockFile())  # type: ignore[arg-type]


class TestDetectHeaders:
    """测试表头识别"""

    def test_detect_required_cols(self) -> None:
        """测试仅包含必选列的情况"""
        df = pd.DataFrame(
            [
                ["订单主题", "派工数量", "加工工序", "合格数量"],
                ["主题1", 100, "落料", 80],
            ]
        )
        required = ["订单主题", "派工数量", "加工工序", "合格数量"]
        col_idx, data_start = detect_headers(df, required, [])

        assert "订单主题" in col_idx
        assert "派工数量" in col_idx
        assert "加工工序" in col_idx
        assert "合格数量" in col_idx
        assert data_start == 1

    def test_detect_optional_cols(self) -> None:
        """测试同时包含必选列和可选列的情况"""
        df = pd.DataFrame(
            [
                ["订单主题", "派工数量", "加工工序", "合格数量", "PDM图号"],
                ["主题1", 100, "落料", 80, "ABC123"],
            ]
        )
        required = ["订单主题", "派工数量", "加工工序", "合格数量"]
        optional = ["PDM图号", "产品名称"]
        col_idx, _ = detect_headers(df, required, optional)

        assert "PDM图号" in col_idx
        assert "产品名称" not in col_idx

    def test_missing_required_col_raises(self) -> None:
        """测试缺少必选列时抛出 ValueError"""
        df = pd.DataFrame(
            [
                ["订单主题", "订单编号"],
                ["主题1", "DD001"],
            ]
        )
        required = ["订单主题", "派工数量", "加工工序", "合格数量"]

        with pytest.raises(ValueError, match="缺少必要的列"):
            detect_headers(df, required, [])

    def test_multirow_header(self) -> None:
        """测试多行表头（包含杂音）向下查找"""
        df = pd.DataFrame(
            [
                ["订单主题", "派工数量", "", ""],
                ["", "", "加工工序", "合格数量"],
                ["主题1", 100, "落料", 80],
            ]
        )
        required = ["订单主题", "派工数量", "加工工序", "合格数量"]
        col_idx, data_start = detect_headers(df, required, [])

        assert len(col_idx) == 4
        assert data_start == 2  # 数据从第三行开始


class TestCleanNumericColumn:
    """测试数值清洗"""

    @pytest.mark.parametrize(
        "input_data,expected",
        [
            ([1, 2, 3], [1.0, 2.0, 3.0]),  # normal_numbers
            (["1,000", "2,500", "10,000"], [1000.0, 2500.0, 10000.0]),  # comma_separated
            ([None, float("nan"), ""], [0.0, 0.0, 0.0]),  # nan_values
            (["abc", "---", "N/A"], [0.0, 0.0, 0.0]),  # non_numeric_values
            ([100, "2,000", None, "abc", 50.5], [100.0, 2000.0, 0.0, 0.0, 50.5]),  # mixed_values
        ],
        ids=["normal", "comma_separated", "nan", "non_numeric", "mixed"],
    )
    def test_clean_numeric_column_variations(self, input_data: list[Any], expected: list[float]) -> None:
        """测试不同情况下的数值列清理（使用参数化）"""
        s = pd.Series(input_data)
        result = clean_numeric_column(s)
        assert list(result) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
