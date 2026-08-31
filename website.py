import os
import streamlit as st
import pandas as pd
import altair as alt
import io


def standardize_columns(df):
    ALIAS = {
        "seller_id": ["店铺id", "店铺ID", "卖家id", "seller", "shop_id"],
        "n_orders": ["订单数", "订单量", "order_count", "orders"],
        "avg_ticket": ["客单价", "平均客单价", "avg_order_value", "aov"],
        "freight_ratio": ["运费负担率", "运费率", "freight_rate"],
        "mom_growth": ["环比增速", "环比增长率", "mom", "sales_growth"],
        "cancel_rate": ["取消率", "订单取消率", "cancellation_rate"],
        "late_rate": ["延迟交货率", "延迟率", "late_delivery_rate"],
        "order_vol": ["订单波动率", "订单波动", "order_volatility"],
        "inst_ratio": ["分期支付占比", "分期占比", "installment_ratio"],
        "avg_inst": ["平均分期数", "平均支付分期数", "avg_installments"],
        "avg_score": ["平均评分", "店铺评分", "review_score", "avg_rating"],
        "bad_rate": ["差评率", "bad_review_rate"],
        "hhi": ["品类集中度", "concentration"],
        "inactive_days": ["不活跃天数", "停更天数", "dormant_days"],
    }
    rename = {}
    for std, names in ALIAS.items():
        for col in df.columns:
            if str(col).strip().lower() in [n.lower() for n in names]:
                rename[str(col)] = std
    df = df.rename(columns=rename)
    need = ["seller_id", "n_orders", "avg_ticket", "freight_ratio", "mom_growth",
            "cancel_rate", "late_rate", "order_vol", "inst_ratio", "avg_inst",
            "avg_score", "bad_rate", "hhi", "inactive_days"]
    filled = [c for c in need if c not in df.columns]
    for c in filled:
        df[c] = pd.NA
    return df, filled


from risk_score import compute_quantiles, score_shop, FULL_SCORE
from risk_level import judge_level_full, LEVEL_INFO
from reason_engine import build_reason_text, build_hit_summary
from risk_rules import RULE_MAP

st.set_page_config(page_title="智审云", page_icon="📊")
st.title("小微企业智能财务风险识别与预警系统")
st.markdown("本系统基于会计专业规则，对小微电商店铺进行财务风险评分与预警。")
st.divider()

# ---- 数据来源：可选上传，不上传则使用云端仓库内置的示例数据 ----
uploaded = st.file_uploader("上传店铺数据 CSV（可选，不上传则分析内置示例数据）", type=["csv"])
if uploaded is not None:
    df = pd.read_csv(uploaded)
    st.info("正在分析上传的数据。")
else:
    df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop_data.csv"))
    st.info("未上传文件，正在分析内置示例数据（3095 家店铺）。")

# ---- 以下为分析主流程（无论上传与否都执行）----
df, filled = standardize_columns(df)
if filled:
    rule_missing = [RULE_MAP[c]["name"] for c in filled if c in RULE_MAP]
    other_missing = [c for c in filled if c not in RULE_MAP]
    msg = "已自动适配：以下风险字段缺失，这些维度的风险将不参与评分，结果会系统性偏向低风险，请补全后重新上传或谨慎解读：" + "、".join(rule_missing)
    if other_missing:
        msg += f"。另缺非评分字段: {other_missing}"
    st.warning(msg)
st.dataframe(df.head(1000))
st.write(f"共 {len(df)} 家店铺，正在分析…")

# ---- 📋 数据诊断①：识别情况与缺失率（排查"为什么全是低风险"）----
st.subheader("📋 数据诊断")
diag_fields = list(RULE_MAP.keys())          # 12 个评分指标字段
diag_found = [c for c in diag_fields if c not in filled]   # 原文件真正有的评分指标
diag_missed = [c for c in diag_fields if c in filled]      # 原文件缺失、被补空的指标
if diag_missed:
    diag_names = "、".join(RULE_MAP[c]["name"] for c in diag_missed)
    st.warning(f"未识别到 {len(diag_missed)} 个评分指标：{diag_names} → 这些维度不参与评分，结果会系统性偏向低风险。")
else:
    st.success("12 个评分指标全部识别成功。")
miss_rows = []
for c in diag_fields:
    if c in df.columns:
        na_pct = float(df[c].isna().mean() * 100)
        miss_rows.append({"评分指标": RULE_MAP[c]["name"], "缺失率%": round(na_pct, 1)})
st.write("各评分指标缺失率（>0 表示有店铺该指标取不到值，会跳过对应规则）：")
st.dataframe(pd.DataFrame(miss_rows))

rows = df.where(pd.notna(df), None).to_dict("records")
p25, p75 = compute_quantiles(rows)
results = []
for r in rows:
    score, hits, missing, max_score = score_shop(r, p25, p75)
    level = judge_level_full(score, len(missing), len(RULE_MAP))
    results.append({
        "seller_id": r["seller_id"],
        "总分": score,
        "最大可得": max_score,
        "缺失字段": "、".join(RULE_MAP[c]["name"] for c in missing) if missing else "无",
        "风险等级": level.value,
        "命中规则": build_hit_summary(hits),
        "风险原因": build_reason_text(hits),
    })

if len(results) == 0:
    st.warning("文件中没有有效数据行，无法分析。")
    st.stop()


def color_risk(val):
    if val == "高风险":
        return "background-color: #ffcccc; color: #cc0000"
    elif val == "中风险":
        return "background-color: #fff3cc; color: #cc8800"
    elif val == "数据不完整":
        return "background-color: #e0e0e0; color: #555555"
    else:
        return "background-color: #ccffcc; color: #008800"


result_df = pd.DataFrame(results)
st.subheader("风险评估结果")
st.dataframe(result_df.head(1000).style.map(color_risk, subset=["风险等级"]))
st.write(f"共 {len(result_df)} 家店铺，上方仅显示前 1000 家，完整结果请下载 Excel。")

# ---- 📋 数据诊断②：评分结果（0 分占比说明是否系统性偏低）----
scores = result_df["总分"]
zero_n = int((scores == 0).sum())
st.write(f"评分诊断：{len(result_df)} 家中 {zero_n} 家（{zero_n / len(result_df) * 100:.0f}%）得 0 分（未命中任何规则）。")
st.write(f"得分范围 {scores.min()} ~ {scores.max()}，平均 {scores.mean():.1f}（规则满分 {FULL_SCORE}）。")
if zero_n / len(result_df) > 0.5:
    st.warning("超过一半店铺得 0 分 → 很可能是上传文件的字段与评分指标不匹配（指标全缺失），请查看上面的「数据诊断①」缺失率表。")
else:
    st.info("0 分店铺占比正常，低风险结果来自真实打分。")

lv_counts = result_df["风险等级"].value_counts().reset_index()
lv_counts.columns = ["风险等级", "店铺数"]
pie = alt.Chart(lv_counts).mark_arc().encode(
    theta="店铺数:Q",
    color="风险等级:N",
    tooltip=["风险等级", "店铺数"]
).properties(title="风险等级分布")
st.altair_chart(pie, width="stretch")

buffer = io.BytesIO()
result_df.to_excel(buffer, index=False, engine="openpyxl")
st.download_button("📥 下载审计风险清单 Excel", buffer.getvalue(),
                   file_name="审计风险清单.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

c1, c2, c3, c4 = st.columns(4)
c1.metric("高风险店铺", int((result_df["风险等级"] == "高风险").sum()))
c2.metric("中风险店铺", int((result_df["风险等级"] == "中风险").sum()))
c3.metric("低风险店铺", int((result_df["风险等级"] == "低风险").sum()))
c4.metric("数据不完整", int((result_df["风险等级"] == "数据不完整").sum()))

dist = alt.Chart(result_df).mark_bar().encode(
    alt.X("总分:Q", bin=True, title="风险得分"),
    y="count()",
).properties(title="风险得分分布")
st.altair_chart(dist, width="stretch")

top10 = result_df.nlargest(10, "总分")
rank = alt.Chart(top10).mark_bar().encode(
    y=alt.Y("seller_id:N", sort="-x", title="店铺ID"),
    x="总分:Q",
).properties(title="风险得分 Top 10 店铺")
st.altair_chart(rank, width="stretch")
