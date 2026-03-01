"""
数据模型定义 (@dataclass)
用于提供强类型的、明确的中间处理结构，替代原来的弱类型 dict。
"""
from dataclasses import dataclass
from typing import List


@dataclass
class ProcessStep:
    name: str        # 工序名称 (如: "氩焊钢丝")
    qualified: float # 累计合格数量
    pending: float   # 待处理量（上道工序合格数 - 本工序合格数）


@dataclass
class PartDispatchResult:
    pdm: str                        # PDM图号 (如: "36651H52100")
    description: str                # 物料描述 (如: "导线夹")
    dispatch_note: str              # 派工说明 (如: "待三价彩锌：6000")
    order_id: str                   # 订单编号
    order_theme: str                # 订单主题
    steps: List[ProcessStep]        # 当前零件的所有工序列表
