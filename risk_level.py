# -*- coding: utf-8 -*-
"""
risk_level.py —— 第2天模块③：分级器
=====================================
职责：按会计《风险评估.docx》的固定阈值，把总分转成三级风险等级。
  高风险  ≥ 12 分    （红）
  中风险  6 ≤ 分 < 12 （黄）
  低风险  < 6 分      （绿）
"""
from enum import Enum


class RiskLevel(Enum):
    HIGH = "高风险"
    MEDIUM = "中风险"
    LOW = "低风险"
    INCOMPLETE = "数据不完整"


def judge_level(score):
    """score: float -> RiskLevel"""
    if score >= 12:
        return RiskLevel.HIGH
    elif score >= 6:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


def judge_level_full(score, n_missing, n_rules):
    """
    带数据完整性门控的分级：
      缺失字段超过一半(n_missing > n_rules//2) -> 数据不完整，不评级
      否则按原阈值分级
    目的：缺字段时宁可标注"数据不完整"，也不要把缺数据的店铺
          静默判成低风险，避免结果系统性偏向低风险。
    """
    if n_missing > n_rules // 2:
        return RiskLevel.INCOMPLETE
    return judge_level(score)


# 界面/报告用：等级 -> 颜色 & 说明
LEVEL_INFO = {
    RiskLevel.HIGH:   ("red",  "收入结构失衡、现金流枯竭、持续经营能力受损，存在实质性财务危机"),
    RiskLevel.MEDIUM: ("orange", "盈利质量下滑、回款效率降低、经营稳定性减弱，存在潜在财务隐患"),
    RiskLevel.LOW:    ("green", "盈利稳定、履约正常、现金流健康，经营状态符合持续经营会计假设"),
    RiskLevel.INCOMPLETE: ("gray", "关键字段缺失过半，现有数据不足以支撑风险评级，请补全数据后重新分析"),
}


if __name__ == "__main__":
    for s in (15, 12, 11.5, 6, 5.9, 0, -3):
        lv = judge_level(s)
        color, desc = LEVEL_INFO[lv]
        print(f"得分{s:>5} -> {lv.value}({color})  {desc[:20]}...")
