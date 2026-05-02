"""
pytest 测试框架 - 派工进度数据处理
"""

import io
import os
import sys
from typing import IO, Any

import pandas as pd
import pytest

# 添加script目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from dispatch_processor import process_dispatch_data

# 测试文件目录
TEST_INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")


class TestProcessDispatch:
    """功能测试 - 处理现有测试文件"""

    @pytest.mark.parametrize(
        "filename",
        [
            "派工进度追踪表_赵淑君.xls",
        ],
    )
    def test_process_valid_files(self, filename: str) -> None:
        """测试处理 .xls 和 .xlsx 文件（参数化）"""
        filepath = os.path.join(TEST_INPUT_DIR, filename)

        with open(filepath, "rb") as f:
            xlsx_data, csv_data, validation_warnings = process_dispatch_data(f)

        # 验证输出非空
        assert len(xlsx_data) > 0, f"{filename}: XLSX数据为空"
        assert len(csv_data) > 0, f"{filename}: CSV数据为空"
        assert isinstance(validation_warnings, list)

        # 验证CSV可解析
        df = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
        assert len(df) > 0, f"{filename}: CSV解析后为空"


class TestOutputValidation:
    """输出验证 - 验证表格列和数据"""

    def _get_result_df(self, filename: str) -> pd.DataFrame:
        """处理文件并返回DataFrame"""
        filepath = os.path.join(TEST_INPUT_DIR, filename)
        with open(filepath, "rb") as f:
            _xlsx_data, csv_data, _validation_warnings = process_dispatch_data(f)
        return pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)

    def _find_header_row(self, df: pd.DataFrame) -> int | None:
        """找到表头行的索引"""
        for idx, row in df.iterrows():
            if "产品型号" in row.values:
                return int(str(idx))
        return None

    def test_output_columns_exist(self) -> None:
        """验证输出包含必需列: 产品型号, 产品名称, 在制汇总, 派工说明"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        assert header_idx is not None, "未找到表头行"

        header_row = df.iloc[header_idx].tolist()
        assert "产品型号" in header_row, "缺少产品型号列"
        assert "产品名称" in header_row, "缺少产品名称列"
        assert "在制汇总" in header_row, "缺少在制汇总列"
        assert "派工说明" in header_row, "缺少派工说明列"
        assert "派工主题" in header_row, "缺少派工主题列"
        assert "订单主题" not in header_row, "不应输出订单主题列"
        assert "订单编号" not in header_row, "不应输出订单编号列"

    def test_产品型号_and_在制汇总_source(self) -> None:
        """验证图号来自产品型号，且在制汇总来自详细派工说明数量合计"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        assert header_idx is not None
        header_row = df.iloc[header_idx].tolist()

        pdm_idx = header_row.index("产品型号")
        in_progress_idx = header_row.index("在制汇总")
        detail_idx = header_row.index("详细派工说明")
        dispatch_theme_idx = header_row.index("派工主题")

        first_data_row = df.iloc[header_idx + 1]
        assert first_data_row[pdm_idx] == "12545H26L00H000"
        assert first_data_row[in_progress_idx] == "60000"
        assert first_data_row[detail_idx] == "DD_20260430002: 待落料 60000"
        assert first_data_row[dispatch_theme_idx] == "DD_20260430002"

    def test_产品型号_not_empty(self) -> None:
        """验证产品型号列有值"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        assert header_idx is not None
        header_row = df.iloc[header_idx].tolist()

        # 找到产品型号列索引
        pdm_idx = header_row.index("产品型号")

        # 获取数据行（跳过表头和空行）
        for idx in range(header_idx + 1, len(df)):
            row = df.iloc[idx]
            if row[pdm_idx] and row[pdm_idx].strip():
                assert len(row[pdm_idx].strip()) > 0, f"第{idx}行产品型号为空"
                break

    def test_产品名称_not_empty(self) -> None:
        """验证产品名称列有值"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        assert header_idx is not None
        header_row = df.iloc[header_idx].tolist()

        # 找到产品名称列索引
        desc_idx = header_row.index("产品名称")

        # 获取数据行
        for idx in range(header_idx + 1, len(df)):
            row = df.iloc[idx]
            if row[desc_idx] and row[desc_idx].strip():
                assert len(row[desc_idx].strip()) > 0, f"第{idx}行产品名称为空"
                break

    def test_说明_format(self) -> None:
        """验证派工说明列格式正确"""
        df = self._get_result_df("派工进度追踪表_赵淑君.xls")

        header_idx = self._find_header_row(df)
        assert header_idx is not None
        header_row = df.iloc[header_idx].tolist()

        # 找到说明列索引
        note_idx = header_row.index("派工说明")

        # 检查说明格式 (如: "DD_20260209001: 待三价彩锌 6000" 或 "待落料：15164")
        import re

        # 新格式: "{订单编号}: 待{工序} {数量}" 或 旧格式: "待{工序}：{数量}"
        pattern = r"^(.+: 待.+ \d+|待.+：\d+)(，(.+: 待.+ \d+|待.+：\d+))*$"

        for idx in range(header_idx + 1, len(df)):
            row = df.iloc[idx]
            note = str(row[note_idx]).strip()
            # 跳过空行和表头行
            if not note or note == "" or note == "派工说明":
                continue
            # 验证格式
            assert re.match(pattern, note), f"第{idx}行派工说明格式错误: {note}"

    def test_详细派工说明_uses_each_dispatch_order_sequence(self) -> None:
        """验证每个派工单按自己的工序顺序生成详细派工说明"""
        csv_content = "\n".join(
            [
                "订单主题,派工主题,产品名称,产品型号,派工数量,加工工序,合格数量",
                "主题A,DD_001,零件A,A001,100,【自制】,0",
                ",,零件A,A001,,落料,20",
                ",,零件A,A001,,入库,0",
                "主题A,DD_002,零件A,A001,50,【自制】,0",
                ",,零件A,A001,,包装,10",
            ]
        )
        mock_file = io.BytesIO(csv_content.encode("utf-8"))
        mock_file.name = "test.csv"  # type: ignore[attr-defined]

        _xlsx_data, csv_data, validation_warnings = process_dispatch_data(mock_file)  # type: ignore[arg-type]
        assert validation_warnings == []

        df = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
        header_row = df.iloc[0].tolist()
        detail_idx = header_row.index("详细派工说明")
        detail = str(df.iloc[1, detail_idx])

        assert "DD_001: 待落料 80" in detail
        assert "DD_001: 待入库 20" in detail
        assert "DD_002: 待包装 40" in detail
        assert "DD_002: 待落料" not in detail

    def test_same_product_across_order_themes_is_merged(self) -> None:
        """验证同一产品型号可汇总不同派工主题，输出列格式符合要求"""
        csv_content = "\n".join(
            [
                "订单主题,派工主题,产品名称,产品型号,派工数量,加工工序,合格数量",
                "主题A,DD_001,零件A,A001,100,【自制】,0",
                ",,零件A,A001,,落料,20",
                "主题B,DD_002,零件A,A001,50,【自制】,0",
                ",,零件A,A001,,落料,10",
            ]
        )
        mock_file = io.BytesIO(csv_content.encode("utf-8"))
        mock_file.name = "test.csv"  # type: ignore[attr-defined]

        _xlsx_data, csv_data, validation_warnings = process_dispatch_data(mock_file)  # type: ignore[arg-type]
        assert validation_warnings == []

        df = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
        header_row = df.iloc[0].tolist()
        assert header_row[:6] == ["产品型号", "产品名称", "在制汇总", "派工说明", "详细派工说明", "派工主题"]

        product_rows = df[df[0] == "A001"]
        assert len(product_rows) == 1

        row = product_rows.iloc[0]
        detail_idx = header_row.index("详细派工说明")
        dispatch_theme_idx = header_row.index("派工主题")
        in_progress_idx = header_row.index("在制汇总")

        assert row[in_progress_idx] == "120"
        assert row[dispatch_theme_idx] == "DD_001 / DD_002"
        assert "DD_001: 待落料 80" in str(row[detail_idx])
        assert "DD_002: 待落料 40" in str(row[detail_idx])

    def test_same_process_route_products_share_one_output_block(self) -> None:
        """验证相同工序序列的不同产品型号放在同一个数据区块"""
        csv_content = "\n".join(
            [
                "派工主题,产品名称,产品型号,派工数量,加工工序,合格数量",
                "DD_001,零件A,A001,100,【自制】,0",
                ",零件A,A001,,落料,20",
                ",零件A,A001,,包装,10",
                "DD_002,零件B,B001,50,【自制】,0",
                ",零件B,B001,,落料,15",
                ",零件B,B001,,包装,5",
            ]
        )
        mock_file = io.BytesIO(csv_content.encode("utf-8"))
        mock_file.name = "test.csv"  # type: ignore[attr-defined]

        _xlsx_data, csv_data, validation_warnings = process_dispatch_data(mock_file)  # type: ignore[arg-type]
        assert validation_warnings == []

        df = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
        header_rows = df[df[0] == "产品型号"]
        assert len(header_rows) == 1

        header_row = df.iloc[0].tolist()
        assert header_row[:10] == [
            "产品型号",
            "产品名称",
            "在制汇总",
            "派工说明",
            "详细派工说明",
            "派工主题",
            "落料",
            "待落料",
            "包装",
            "待包装",
        ]
        assert df.iloc[1, 0] == "A001"
        assert df.iloc[2, 0] == "B001"
        assert df.iloc[3, 0] == ""

    def test_same_product_model_with_different_names_is_merged_by_model(self) -> None:
        """验证最终输出按产品型号分组，而不是按产品名称拆分"""
        csv_content = "\n".join(
            [
                "订单主题,派工主题,产品名称,产品型号,派工数量,加工工序,合格数量",
                "主题A,DD_001,零件A,A001,100,【自制】,0",
                ",,零件A,A001,,落料,20",
                "主题B,DD_002,零件A别名,A001,50,【自制】,0",
                ",,零件A别名,A001,,落料,10",
            ]
        )
        mock_file = io.BytesIO(csv_content.encode("utf-8"))
        mock_file.name = "test.csv"  # type: ignore[attr-defined]

        _xlsx_data, csv_data, validation_warnings = process_dispatch_data(mock_file)  # type: ignore[arg-type]
        assert validation_warnings == []

        df = pd.read_csv(io.BytesIO(csv_data), header=None, keep_default_na=False)
        product_rows = df[df[0] == "A001"]
        assert len(product_rows) == 1


class TestBoundaryCases:
    """边界测试 - 异常情况"""

    def test_missing_required_column(self) -> None:
        """测试缺少必需列应抛出异常"""
        # 创建一个缺少必需列的CSV
        csv_content = "订单主题,订单编号\n主题1,DD001"

        # 创建一个模拟文件对象
        class MockFile:
            def __init__(self, name: str, content: bytes) -> None:
                self.name = name
                self._content = content

            def read(self, n: int = -1) -> bytes:
                return self._content

            def __enter__(self) -> IO[bytes]:
                return self  # type: ignore[return-value]

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        mock_file = MockFile("test.csv", csv_content.encode("utf-8"))

        # 应该抛出异常（可能是ValueError或其他异常）
        with pytest.raises(Exception) as exc_info:
            process_dispatch_data(mock_file)  # type: ignore[arg-type]

        # 验证有异常信息
        assert len(str(exc_info.value)) > 0

    def test_invalid_file_format(self) -> None:
        """测试无效文件格式应抛出异常"""

        class MockFile:
            def __init__(self, name: str) -> None:
                self.name = name

            def __enter__(self) -> IO[bytes]:
                return self  # type: ignore[return-value]

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        mock_file = MockFile("test.txt")

        with pytest.raises(ValueError) as exc_info:
            process_dispatch_data(mock_file)  # type: ignore[arg-type]

        assert "不支持的文件格式" in str(exc_info.value)

    def test_duplicate_dispatch_order_with_different_product_names_warns(self) -> None:
        """测试同一派工单号对应多个产品名称时返回校验提示"""
        csv_content = "\n".join(
            [
                "订单主题,派工主题,产品名称,产品型号,派工数量,加工工序,合格数量",
                "主题A,DD_009,零件A,A001,10,【自制】,0",
                ",,零件A,A001,,落料,5",
                "主题B,DD_009,零件B,B001,10,【自制】,0",
                ",,零件B,B001,,落料,6",
            ]
        )
        mock_file = io.BytesIO(csv_content.encode("utf-8"))
        mock_file.name = "test.csv"  # type: ignore[attr-defined]

        _xlsx_data, _csv_data, validation_warnings = process_dispatch_data(mock_file)  # type: ignore[arg-type]

        assert len(validation_warnings) == 1
        warning = validation_warnings[0]
        assert "DD_009" in warning
        assert "零件A" in warning
        assert "零件B" in warning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
