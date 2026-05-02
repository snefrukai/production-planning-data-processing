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
    """单个生产工序的计算结果。

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
    """单个产品型号的在制分析结果。

    Attributes:
        pdm: 产品型号 (如: "36651H52100")
        description: 产品名称 (如: "导线夹")
        dispatch_note: 派工说明（汇总） (如: "待三价彩锌：6000")
        dispatch_note_detail: 详细派工说明（按派工主题分列）
        in_progress_total: 在制汇总（详细派工说明中的数量合计）
        order_id: 派工主题
        order_theme: 兼容字段，当前输出不展示
        steps: 当前零件的所有工序列表
    """

    pdm: str
    description: str
    dispatch_note: str
    dispatch_note_detail: str
    in_progress_total: int
    order_id: str
    order_theme: str
    steps: list[ProcessStep]
