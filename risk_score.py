# -*- coding: utf-8 -*-
"""
risk_score.py —— 第2天模块②：打分器
=====================================
职责：给单家店铺打 0~24 分。
1) 先根据【全体店铺样本】计算每个指标的分位数(25%/75%) —— 会计规则里
   "高于样本75%分位/低于样本25%分位" 都指全体店铺的相对位置。
2) 再逐条判断规则是否命中，累加分值。
3) 反向修正：指标处于"良好区间"(前25%)时，扣掉对应分值的50%，平滑极端值。

对外接口：
  compute_quantiles(rows) -> (p25, p75)   计算全体样本分位数
  score_shop(row, p25, p75) -> (score, hits)  给单店打分
"""
import statistics

from risk_rules import RULES, RULE_MAP

# 参与分位数比较的指标
QUANTILE_FIELDS = [r["id"] for r in RULES if r["mode"] in ("low_p25", "high_p75")]


def compute_quantiles(rows, p_low=0.25, p_high=0.75):
    """
    计算全体样本各指标的分位数。
    rows: 每行是一个 dict(字段名->数值或None)
    返回: ({字段:低分位}, {字段:高分位})
    """
    p25, p75 = {}, {}
    for field in QUANTILE_FIELDS:
        vals = sorted(r[field] for r in rows if r.get(field) is not None)
        if not vals:
            p25[field] = p75[field] = None
            continue
        n = len(vals)
        # 分位数索引（含端点），p=0.25/0.75
        p25[field] = vals[int(p_low * (n - 1))]
        p75[field] = vals[int(p_high * (n - 1))]
    return p25, p75


def _is_good(value, field, p25, p75):
    """反向修正判定：该指标是否处于"样本良好区间"(前25%)"""
    lo, hi = p25[field], p75[field]
    if lo is None or hi is None:
        return False
    rule = RULE_MAP[field]
    if rule["mode"] == "low_p25":          # 越低越不利 -> 良好=越高越好(>=p75)
        return value >= hi
    else:                                   # 越高越不利 -> 良好=越低越好(<=p25)
        return value <= lo


def score_shop(row, p25, p75):
    """
    对单家店铺打分。
    返回: (总得分, hits)
      hits = [ {dim, name, id, score, reason} for 命中的规则 ]
    """
    total = 0.0
    hits = []
    for rule in RULES:
        field = rule["id"]
        v = row.get(field)
        if v is None:          # 缺失值(如无评价店铺)跳过，不误判
            continue

        hit = False
        if rule["mode"] == "low_p25":
            hit = v < p25[field]
        elif rule["mode"] == "high_p75":
            hit = v > p75[field]
        elif rule["mode"] == "abs":         # 绝对条件规则
            if field == "mom_growth":
                hit = v <= -0.30            # 环比下滑超过30%
            elif field == "inactive_days":
                hit = v > 90                # 近3个月(>90天)无有效订单

        if hit:
            total += rule["score"]
            hits.append({
                "id": field, "dim": rule["dim"], "name": rule["name"],
                "score": rule["score"], "reason": rule["reason"],
            })
        else:
            # 反向修正：良好区间扣对应分值的50%
            if rule["mode"] != "abs" and _is_good(v, field, p25, p75):
                total -= rule["score"] * 0.5
    return round(total, 1), hits


if __name__ == "__main__":
    # 自测：构造一份假样本验证打分逻辑
    demo = [
        {"avg_ticket": 40, "freight_ratio": 0.5, "mom_growth": -0.5, "cancel_rate": 0.4,
         "late_rate": 0.5, "order_vol": 1.0, "inst_ratio": 0.9, "avg_inst": 6.0,
         "avg_score": 2.5, "bad_rate": 0.5, "hhi": 1.0, "inactive_days": 200},
        {"avg_ticket": 150, "freight_ratio": 0.15, "mom_growth": 0.2, "cancel_rate": 0.0,
         "late_rate": 0.0, "order_vol": 0.1, "inst_ratio": 0.2, "avg_inst": 1.5,
         "avg_score": 4.8, "bad_rate": 0.0, "hhi": 0.5, "inactive_days": 5},
    ]
    p25, p75 = compute_quantiles(demo)
    for i, r in enumerate(demo):
        score, hits = score_shop(r, p25, p75)
        print(f"店铺{i}: 总分={score} 命中{len(hits)}项 -> {[h['name'] for h in hits]}")
