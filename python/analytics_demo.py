# -*- coding: utf-8 -*-
"""
经营分析模块演示: 无需 MySQL, 用 SQLite 种子数据跑通三张报表。
同时内置断言, 校验统计口径正确性。

运行: python analytics_demo.py
"""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analytics import profit_trend, repurchase_analysis, material_consumption, render_report

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.db")
if os.path.exists(DB):
    os.remove(DB)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# ------------------------------------------------------------ 建表(仅演示所需列)
c.executescript("""
CREATE TABLE customer (customer_id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT,
  quantity INTEGER, unit_price REAL, material_cost REAL, labor_cost REAL,
  created_at TEXT, actual_complete_date TEXT);
CREATE TABLE material (material_id INTEGER PRIMARY KEY, name TEXT, material_category TEXT);
CREATE TABLE material_category (material_category_id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE order_material (
  order_material_id INTEGER PRIMARY KEY, order_id INTEGER, material_id INTEGER,
  quantity_used REAL, unit_cost REAL);
""")

customers = [(1, "小林"), (2, "阿May"), (3, "王姐")]
c.executemany("INSERT INTO customer VALUES (?,?)", customers)

# 订单: (客户, 描述, 数量x单价, 材料成本, 工时成本, 完成日期)
orders = [
    (1, "定制皮包", 1, 4200, 900, 1200, "2026-01-12"),
    (1, "定制银手链", 1, 600, 80, 200, "2026-01-28"),
    (2, "现货珍珠耳环", 1, 200, 50, 100, "2026-02-05"),
    (3, "批量编织杯垫", 10, 45, 150, 180, "2026-02-20"),
    (1, "定制皮靴", 2, 2300, 1000, 1500, "2026-03-10"),
    (2, "皮具卡包", 3, 900, 300, 800, "2026-05-14"),
    (2, "现货珐琅杯", 2, 260, 140, 160, "2026-08-16"),
]
c.executemany("INSERT INTO orders (customer_id, status, quantity, unit_price, "
              "material_cost, labor_cost, created_at, actual_complete_date) "
              "VALUES (?, 'COMPLETED', ?, ?, ?, ?, ?, ?)",
              [(cid, qty, up, mc, lc, d, d) for cid, _, qty, up, mc, lc, d in orders])

cat_names = {1: "金属配件", 2: "皮革", 3: "烘焙原料", 4: "陶土", 5: "线材"}
mats = [(1, "925银链", 1), (2, "龙虾扣", 1), (3, "植鞣革", 2), (4, "低筋面粉", 3), (5, "白陶泥", 4)]
c.executemany("INSERT INTO material VALUES (?,?,?)",
              [(i, n, cat_names[cid]) for i, n, cid in mats])

# 耗用: (order_id, material_id, 消耗量, 单价快照)
#   1-925银链 2-龙虾扣 3-植鞣革 4-低筋面粉 5-白陶泥
consumption = [
    (1, 1, 2, 8.00),    # 16
    (1, 2, 2, 0.50),    # 1
    (1, 3, 4, 12.00),   # 48
    (1, 4, 10, 6.50),   # 65
    (1, 5, 3, 28.00),   # 84  → 合计数量21 / 成本214
]
c.executemany("INSERT INTO order_material (order_id, material_id, quantity_used, unit_cost) "
              "VALUES (?,?,?,?)", consumption)
conn.commit()

def q(sql):
    return [dict(r) for r in conn.execute(sql)]

completed = q("SELECT o.customer_id, c.name AS customer_name, "
              "       o.quantity, o.unit_price, o.material_cost, o.labor_cost, "
              "       COALESCE(o.actual_complete_date, o.created_at) AS completed_date "
              "FROM orders o JOIN customer c ON c.customer_id = o.customer_id "
              "WHERE o.status IN ('COMPLETED','ARCHIVED')")
mat_rows = q("SELECT m.name AS material_name, m.material_category AS material_category, "
             "       om.quantity_used, om.unit_cost "
             "FROM order_material om JOIN material m ON m.material_id = om.material_id")

# ------------------------------------------------------------ 断言(统计口径自检)
def approx(a, b):
    return abs(a - b) < 0.01

monthly = profit_trend(completed, "month")
assert [r["period"] for r in monthly] == ["2026-01", "2026-02", "2026-03", "2026-05", "2026-08"]
assert approx(monthly[0]["income"], 4800) and approx(monthly[0]["profit"], 2420)   # 1月
assert approx(monthly[1]["income"], 650) and approx(monthly[1]["profit"], 170)     # 2月
assert approx(monthly[-1]["income"], 520) and approx(monthly[-1]["profit"], 220)   # 8月
assert sum(r["orders"] for r in monthly) == 7

quarterly = profit_trend(completed, "quarter")
assert [r["period"] for r in quarterly] == ["2026-Q1", "2026-Q2", "2026-Q3"]
assert approx(quarterly[0]["income"], 10050)                                       # Q1=4800+650+4600

rep = repurchase_analysis(completed)
assert rep["total_customers"] == 3 and rep["repeat_customers"] == 2
assert approx(rep["repurchase_rate"], 0.6667)
assert approx(rep["total_income"], 13270) and approx(rep["avg_order_value"], 13270 / 7)
tier_map = {c["name"]: c["tier"] for c in rep["customer_list"]}
assert tier_map["小林"] == "高价值" and tier_map["阿May"] == "中价值" and tier_map["王姐"] == "普通"

mat = material_consumption(mat_rows)
assert approx(mat["total_cost"], 214.0) and approx(mat["total_quantity"], 21.0)
assert mat["items"][0]["material_name"] == "白陶泥"    # 消耗成本最高者排首位

# ------------------------------------------------------------ 输出报表
print(render_report(monthly, "利润趋势(月)"))
print()
print(render_report(profit_trend(completed, "quarter"), "利润趋势(季度)"))
print()
print(render_report(rep, "客户复购与价值分析"))
print()
print(render_report(mat, "材料消耗分析"))
print()
print("所有断言通过 ✓ (analytics 统计口径正确)")
conn.close()