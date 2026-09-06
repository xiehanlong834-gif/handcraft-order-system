# -*- coding: utf-8 -*-
"""
数据分析模块（创新点二：数据统计分析 / 经营画像）
=================================================
定位: 由 Java 后端以本地脚本方式调用的"经营分析引擎"。
纯函数核心与数据库解耦: 本模块只负责"按规则算", 数据获取由 SQL 适配器完成。
因此可在任何环境用 SQLite/纯数据测试, 生产环境接 MySQL —— 结果一致。

产出报表(对应规划文档 4.2):
    1. 利润趋势报表   —— 按月/按季统计 收入/成本/利润
    2. 客户复购分析   —— 复购率、客单价、客户价值分层
    3. 材料消耗分析   —— 各类材料消耗量与消耗成本

作者: 课程项目组 | 日期: 2026-09
"""

from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------- 工具
def _money(x):
    """金额保留 2 位小数。"""
    return round(float(x or 0), 2)


def _month_key(date_str):
    """'2026-03-15' -> '2026-03'"""
    return str(date_str)[:7]


def _quarter_key(date_str):
    """'2026-03-15' -> '2026-Q1'"""
    m = int(str(date_str)[5:7])
    return "%s-Q%d" % (str(date_str)[:4], (m - 1) // 3 + 1)


# ---------------------------------------------------------------- 报表1: 利润趋势
def profit_trend(completed_orders, group="month"):
    """按月/按季统计收入、成本、利润。

    :param completed_orders: 已完成订单行, 每行 dict:
        {completed_date:'YYYY-MM-DD', quantity, unit_price, material_cost, labor_cost}
    :param group: 'month' | 'quarter'
    :return: [{period, orders, income, cost, profit}], 按 period 升序
    """
    key_fn = _month_key if group == "month" else _quarter_key
    agg = defaultdict(lambda: {"orders": 0, "income": 0.0, "cost": 0.0})
    for o in completed_orders:
        d = o.get("completed_date") or o.get("created_at")
        if not d:
            continue
        k = key_fn(d)
        income = _money(o.get("quantity", 1)) * _money(o.get("unit_price"))
        cost = _money(o.get("material_cost")) + _money(o.get("labor_cost"))
        agg[k]["orders"] += 1
        agg[k]["income"] = _money(agg[k]["income"] + income)
        agg[k]["cost"] = _money(agg[k]["cost"] + cost)
    rows = [{"period": k, "orders": v["orders"], "income": v["income"],
             "cost": v["cost"], "profit": _money(v["income"] - v["cost"])}
            for k, v in agg.items()]
    rows.sort(key=lambda r: r["period"])
    return rows


# ---------------------------------------------------------------- 报表2: 客户复购分析
def repurchase_analysis(completed_orders):
    """复购率 / 客单价 / 客户价值分层。

    复购率    = 下单>=2次的客户数 / 有下单客户数
    客单价    = 总收入 / 订单数 (每单平均金额)
    客户价值  = 按累计消费金额分档: >=8000 高价值 / >=2000 中价值 / 其余 普通
    :param completed_orders: 行 dict: {customer_id, customer_name?, quantity,
        unit_price, material_cost, labor_cost}
    """
    if not completed_orders:
        return {"total_customers": 0, "repeat_customers": 0, "repurchase_rate": 0.0,
                "total_orders": 0, "total_income": 0.0, "avg_order_value": 0.0,
                "value_tiers": {}, "customer_list": []}

    cust = defaultdict(lambda: {"orders": 0, "income": 0.0, "name": "未知"})
    for o in completed_orders:
        cid = o.get("customer_id")
        cust[cid]["orders"] += 1
        cust[cid]["income"] = _money(
            cust[cid]["income"] + _money(o.get("quantity", 1)) * _money(o.get("unit_price")))
        if o.get("customer_name"):
            cust[cid]["name"] = o["customer_name"]

    total_customers = len(cust)
    repeat = [c for c in cust.values() if c["orders"] >= 2]
    income = sum(c["income"] for c in cust.values())
    n_orders = sum(c["orders"] for c in cust.values())

    def tier(income_):
        if income_ >= 8000:
            return "高价值"
        if income_ >= 2000:
            return "中价值"
        return "普通"

    tiers = defaultdict(lambda: {"customers": 0, "income": 0.0})
    customer_list = []
    for cid, c in sorted(cust.items(), key=lambda kv: -kv[1]["income"]):
        t = tier(c["income"])
        tiers[t]["customers"] += 1
        tiers[t]["income"] = _money(tiers[t]["income"] + c["income"])
        customer_list.append({"customer_id": cid, "name": c["name"],
                              "orders": c["orders"], "total_spend": c["income"], "tier": t})

    return {
        "total_customers": total_customers,
        "repeat_customers": len(repeat),
        "repurchase_rate": round(len(repeat) / total_customers, 4),
        "total_orders": n_orders,
        "total_income": _money(income),
        "avg_order_value": _money(income / n_orders) if n_orders else 0.0,
        "value_tiers": {k: dict(v) for k, v in tiers.items()},
        "customer_list": customer_list,
    }


# ---------------------------------------------------------------- 报表3: 材料消耗分析
def material_consumption(consumption_rows):
    """按材料统计消耗量与消耗成本(材料消耗分析)。

    :param consumption_rows: 订单材料耗用行 dict:
        {material_name, material_category?, quantity_used, unit_cost}
    :return: {items: 按材料聚合(含品类), total_quantity, total_cost}
    """
    agg = defaultdict(lambda: {"category": "未分类", "quantity": 0.0, "cost": 0.0})
    for r in consumption_rows:
        name = r.get("material_name") or "未知材料"
        agg[name]["quantity"] = _money(agg[name]["quantity"] + float(r.get("quantity_used") or 0))
        agg[name]["cost"] = _money(
            agg[name]["cost"] + float(r.get("quantity_used") or 0) * _money(r.get("unit_cost")))
        if r.get("material_category"):
            agg[name]["category"] = r["material_category"]
    items = [{"material_name": k, "category": v["category"],
              "quantity_used": v["quantity"], "cost": v["cost"]}
             for k, v in agg.items()]
    items.sort(key=lambda x: -x["cost"])
    return {"items": items,
            "total_quantity": _money(sum(i["quantity_used"] for i in items)),
            "total_cost": _money(sum(i["cost"] for i in items))}


# ---------------------------------------------------------------- 文本渲染(演示/联调用)
def render_report(report, title):
    lines = ["==== %s ====" % title]
    if title.startswith("利润趋势"):
        lines.append("%-8s %6s %10s %10s %10s" % ("月份", "订单数", "收入", "成本", "利润"))
        for r in report:
            lines.append("%-8s %6d %10.2f %10.2f %10.2f" %
                         (r["period"], r["orders"], r["income"], r["cost"], r["profit"]))
    elif title.startswith("客户复购"):
        lines.append("有下单客户数: %d | 复购客户(>=2单): %d | 复购率: %.1f%%" % (
            report["total_customers"], report["repeat_customers"],
            report["repurchase_rate"] * 100))
        lines.append("订单总数: %d | 总收入: %.2f | 客单价(每单均价): %.2f" % (
            report["total_orders"], report["total_income"], report["avg_order_value"]))
        lines.append("价值分层: " + " | ".join(
            "%s %d人/%.2f" % (k, v["customers"], v["income"])
            for k, v in sorted(report["value_tiers"].items(),
                               key=lambda kv: -kv[1]["income"])))
        lines.append("%-12s %6s %12s  %s" % ("客户", "单数", "累计消费", "分层"))
        for c in report["customer_list"]:
            lines.append("%-12s %6d %12.2f  %s" %
                         (c["name"], c["orders"], c["total_spend"], c["tier"]))
    elif title.startswith("材料消耗"):
        lines.append("%-16s %-10s %12s %12s" % ("材料", "品类", "消耗量", "消耗成本"))
        for i in report["items"]:
            lines.append("%-16s %-10s %12.2f %12.2f" %
                         (i["material_name"], i["category"], i["quantity_used"], i["cost"]))
        lines.append("合计消耗成本: %.2f" % report["total_cost"])
    return "\n".join(lines)


def _run(conn_factory, json_out=False):
    """执行三张报表; conn_factory 返回已连接对象(需支持 Row 字典化)"""
    import sqlite3
    conn = conn_factory()
    if isinstance(conn, sqlite3.Connection):
        conn.row_factory = sqlite3.Row
    def q(sql):
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        return rows
    completed = q("SELECT o.customer_id, c.name AS customer_name, "
                  "       o.quantity, o.unit_price, o.material_cost, o.labor_cost, "
                  "       COALESCE(o.actual_complete_date, o.created_at) AS completed_date "
                  "FROM `orders` o JOIN customer c ON c.customer_id = o.customer_id "
                  "WHERE o.status = 'COMPLETED' OR (o.status = 'ARCHIVED' AND o.actual_complete_date IS NOT NULL)")
    materials = q("SELECT m.name AS material_name, mc.name AS material_category, "
                  "       om.quantity_used, om.unit_cost "
                  "FROM order_material om JOIN material m ON m.material_id=om.material_id "
                  "LEFT JOIN material_category mc ON mc.material_category_id=m.material_category_id")
    month = profit_trend(completed, "month")
    quarter = profit_trend(completed, "quarter")
    rep = repurchase_analysis(completed)
    mat = material_consumption(materials)
    if json_out:
        import json
        print(json.dumps({
            "profitTrendMonth": month, "profitTrendQuarter": quarter,
            "repurchase": rep, "materialConsumption": mat,
        }, ensure_ascii=False, default=str))
        return
    print(render_report(month, "利润趋势(月)"))
    print()
    print(render_report(quarter, "利润趋势(季度)"))
    print()
    print(render_report(rep, "客户复购与价值分析"))
    print()
    print(render_report(mat, "材料消耗分析"))


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    json_out = "--json" in args
    args = [a for a in args if a != "--json"]

    if args and args[0] == "--mysql":
        # MySQL 直连模式: python analytics.py --mysql [host] [user] [password] [db] [--json]
        host = args[1] if len(args) > 1 else "127.0.0.1"
        user = args[2] if len(args) > 2 else "handcraft"
        pwd = args[3] if len(args) > 3 else "handcraft123"
        db = args[4] if len(args) > 4 else "handcraft_order"
        try:
            import pymysql
        except ImportError:
            print("缺少 pymysql: pip install pymysql", file=sys.stderr)
            sys.exit(1)
        _run(lambda: pymysql.connect(host=host, user=user, password=pwd,
                                     database=db, charset="utf8mb4"), json_out)
    elif args and args[0].endswith(".db"):
        # SQLite 模式: python analytics.py demo.db [--json]
        import sqlite3
        _run(lambda: sqlite3.connect(args[0]), json_out)
    else:
        print("用法:")
        print("  python analytics.py --mysql [host] [user] [password] [db] [--json]   # MySQL 生产库")
        print("  python analytics.py demo.db [--json]                                 # SQLite 演示库")
        print("演示种子: python analytics_demo.py")
        sys.exit(0)