# -*- coding: utf-8 -*-
"""
reason_engine.py —— 第2天模块④：话术引擎
===========================================
职责：当一家店铺命中若干规则时，自动拼出"会计写的专业原因话术"。
这些话术全部来自会计《风险评估.docx》第三部分，软件弹窗/报告直接引用，
答辩时可讲"系统风险提示的专业解释均由会计专业规则驱动"。
"""


def build_reason_text(hits):
    """
    hits: score_shop 返回的命中列表 [ {dim,name,score,reason,...}, ... ]
    返回: 一段连贯的中文风险说明（含维度+指标+会计专业原因）
    """
    if not hits:
        return "该店铺各维度指标处于样本正常区间，未触发风险规则，经营状态符合持续经营会计假设。"
    parts = []
    for h in hits:
        parts.append(f"【{h['dim']}·{h['name']}】{h['reason']}")
    return "".join(parts)


def build_hit_summary(hits):
    """返回简短命中摘要，用于表格列展示，如：盈利风险/客单价(+2)；..."""
    if not hits:
        return "-"
    return "；".join(f"{h['dim']}/{h['name']}(+{h['score']})" for h in hits)


if __name__ == "__main__":
    demo_hits = [
        {"dim": "盈利风险", "name": "客单价水平", "score": 2.0,
         "reason": "客单价持续偏低，单位订单边际贡献不足。"},
        {"dim": "存续风险", "name": "店铺近期活跃度", "score": 3.0,
         "reason": "长期无新订单，持续经营能力受损。"},
    ]
    print(build_reason_text(demo_hits))
    print()
    print(build_reason_text([]))
    print()
    print(build_hit_summary(demo_hits))
