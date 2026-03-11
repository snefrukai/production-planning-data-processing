"""
数据模型定义 (@dataclass)

用于提供强类型的、明确的中间处理结构，替代原来的弱类型 dict。
"""

from dataclasses import dataclass

__all__ = [
    "ProcessStep",
    "PartDispatchResult",
]


@dataclass
class ProcessStep:
    """Represents a single production or processing step for a part.

    Attributes:
        name: 工序名称 (如: "氩焊钢丝")
        qualified: 累计合格数量
        pending: 待处理量（上道工序合格数 - 本工序合格数）
    """

    name: str
    qualified: float
    pending: float


@dataclass
class PartDispatchResult:
    """Aggregated processing result for a single part dispatch item.

    Attributes:
        pdm: PDM图号 (如: "36651H52100")
        description: 物料描述 (如: "导线夹")
        dispatch_note: 派工说明（汇总） (如: "待三价彩锌：6000")
        dispatch_note_detail: 详细派工说明（按订单编号分列）
        order_id: 订单编号
        order_theme: 订单主题
        steps: 当前零件的所有工序列表
    """

    pdm: str
    description: str
    dispatch_note: str
    dispatch_note_detail: str
    order_id: str
    order_theme: str
    steps: list[ProcessStep]
