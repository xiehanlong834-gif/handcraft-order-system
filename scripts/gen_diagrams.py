# -*- coding: utf-8 -*-
"""生成课程答辩图: E-R 图 + 用例图 (docs/diagrams/*.svg, 浏览器/GitHub 可直接查看)"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "diagrams")
os.makedirs(OUT, exist_ok=True)

FONT = 'font-family="Microsoft YaHei, sans-serif"'

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;")

# ---------------- E-R 图 ----------------
# (x, y) 左上角; 盒宽220 高92
ER = []
def erbox(x, y, title, lines, pk=None, fill="#ffffff"):
    ER.append(f'<g><rect x="{x}" y="{y}" width="220" height="92" rx="8" fill="{fill}" stroke="#1d4ed8" stroke-width="1.4"/>')
    ER.append(f'<text x="{x+110}" y="{y+20}" text-anchor="middle" font-size="13" font-weight="700" fill="#1d4ed8" {FONT}>{esc(title)}</text>')
    ty = y + 38
    for ln in lines:
        ER.append(f'<text x="{x+12}" y="{ty}" font-size="11" fill="#475569" {FONT}>{esc(ln)}</text>')
        ty += 17
    ER.append('</g>')

def erline(x1, y1, x2, y2, label):
    ER.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#94a3b8" stroke-width="1.2"/>')
    mx, my = (x1+x2)/2, (y1+y2)/2
    ER.append(f'<text x="{mx+6}" y="{my-6}" font-size="11" fill="#64748b" {FONT}>{esc(label)}</text>')

# 布局: 三列两行 + 底部
erbox(40, 40, "role 角色", ["role_id PK", "role_code", "role_name"])
erbox(320, 40, "user 用户", ["user_id PK", "username", "password_hash(BCrypt)", "role_id FK", "customer_id FK"])
erbox(600, 40, "customer 客户", ["customer_id PK", "name", "phone(脱敏)", "creator_id FK"])
erbox(40, 220, "product_category", ["id PK", "name"])
erbox(320, 210, "orders 订单", ["order_id PK", "order_no", "customer/creator FK", "order_type/status", "cost/profit 字段", "estimate_dates"])
erbox(600, 210, "order_status_log", ["log_id PK", "order_id FK", "from/to", "operator_id FK"])
erbox(40, 420, "material_category", ["id PK", "name"])
erbox(320, 410, "material 材料", ["material_id PK", "name/spec/unit", "stock_qty", "low_threshold", "unit_price"])
erbox(600, 410, "stock_movement", ["movement_id PK", "material_id FK", "direction IN/OUT", "order_id FK?", "quantity"])
erbox(320, 590, "order_material", ["id PK", "order_id FK", "material_id FK", "qty_used", "unit_cost 快照"])
erbox(600, 590, "announcement", ["id PK", "title/content", "publisher_id FK"])

# 关系
erline(260, 86, 320, 86, "1:N 角色分配")
erline(540, 86, 600, 86, "N:1 归属档案")
erline(430, 132, 430, 210, "1:N 客户下单")
erline(320, 132, 320, 210, "N:1 创作者接单")
erline(150, 132, 150, 220, "1:N 分类")          # product_category -> orders? 实际orders N:1 category: from orders到category方向
erline(540, 256, 600, 256, "1:N 审计")
erline(260, 464, 320, 464, "1:N 品类")
erline(540, 464, 600, 464, "1:N 流水")
erline(340, 502, 180, 590, "N:M 耗料")
erline(280, 540, 180, 590, "1:N 归属")
erline(430, 502, 430, 590, "N:M 耗料")          # orders-order_material(实际在material列)

head = ['<svg xmlns="http://www.w3.org/2000/svg" width="880" height="730" viewBox="0 0 880 730">',
        f'<rect width="880" height="730" fill="#f7fbff"/>',
        '<text x="20" y="26" font-size="16" font-weight="700" fill="#0f172a" ' + FONT + '>E-R 图 · handcraft_order 数据库(11 表, 简化展示核心字段)</text>']
svg = "\n".join(head + ER + ["</svg>"])
open(os.path.join(OUT, "er-diagram.svg"), "w", encoding="utf-8").write(svg)
print("ER svg:", len(ER), "primitives")

# ---------------- 用例图 ----------------
U = []
U.append('<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="640" viewBox="0 0 1080 640">')
U.append('<rect width="1080" height="640" fill="#f7fbff"/>')
U.append(f'<text x="20" y="26" font-size="16" font-weight="700" fill="#0f172a" {FONT}>用例图 · 四类角色</text>')

def actor(x, y, name):
    U.append(f'<g stroke="#0f172a" stroke-width="1.6" fill="none">'
             f'<circle cx="{x}" cy="{y-38}" r="12"/><line x1="{x}" y1="{y-26}" x2="{x}" y2="{y+4}"/>'
             f'<line x1="{x-14}" y1="{y-14}" x2="{x+14}" y2="{y-14}"/>'
             f'<line x1="{x}" y1="{y+4}" x2="{x-14}" y2="{y+24}"/><line x1="{x}" y1="{y+4}" x2="{x+14}" y2="{y+24}"/>'
             f'<line x1="{x}" y1="{y+24}" x2="{x-16}" y2="{y+46}"/><line x1="{x}" y1="{y+24}" x2="{x+16}" y2="{y+46}"/></g>')
    U.append(f'<text x="{x}" y="{y+64}" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a" {FONT}>{esc(name)}</text>')

def usecase(x, y, text, w=150):
    U.append(f'<ellipse cx="{x}" cy="{y}" rx="{w/2}" ry="20" fill="#ffffff" stroke="#1d4ed8" stroke-width="1.3"/>')
    U.append(f'<text x="{x}" y="{y+4}" text-anchor="middle" font-size="12" fill="#1d4ed8" {FONT}>{esc(text)}</text>')
    return (x, y)

def ucline(ax, ay, ux, uy):
    U.append(f'<line x1="{ax}" y1="{ay}" x2="{ux}" y2="{uy}" stroke="#94a3b8" stroke-width="1.2"/>')

# 角色(左侧)
actor(70, 90, "创作者"); actor(70, 250, "客户"); actor(70, 420, "管理员"); actor(70, 580, "财务查看者")

# 用例列(x≈300 / 620 两列)
creator_ucs = [(330, 60, "登录认证"), (330, 120, "创建订单*"), (330, 180, "状态机流转*"), (330, 240, "录入耗料/工时*"),
               (640, 60, "库存出入库*"), (640, 120, "客户管理"), (640, 180, "排期日历/提醒"), (640, 240, "智能订单分类 <<system>>")]
for i, (x, y, t) in enumerate(creator_ucs):
    ucline(95, 110 if i < 4 else 170, x - 0, y) if False else None
    cx, cy = usecase(x, y, t, 170 if x < 400 else 190)
    ucline(110, 90 if i < 4 else 0, cx, cy) if False else None

# 简单起见: 手动画线到 creator actor (y~105)
for (x, y, t) in creator_ucs[:4]:
    ux, uy = usecase(x, y, t, 170); ucline(100, 100, ux, uy)
for (x, y, t) in creator_ucs[4:]:
    ux, uy = usecase(x, y, t, 190); ucline(100, 140, ux, uy)

cust_ucs = [(300, 330, "我的订单/进度"), (610, 330, "提交定制需求*"), (610, 390, "追踪预计完成")]
for (x, y, t) in cust_ucs:
    ux, uy = usecase(x, y, t, 180); ucline(100, 270, ux, uy)

adm_ucs = [(300, 480, "用户管理"), (610, 470, "产品/材料分类"), (610, 530, "公告发布"), (300, 545, "经营总览")]
for (x, y, t) in adm_ucs:
    ux, uy = usecase(x, y, t, 150 if x < 400 else 170); ucline(100, 440, ux, uy)

fin_ucs = [(450, 610, "经营报表(收支/趋势/复购/材料) <<finance+admin>>")]
for (x, y, t) in fin_ucs:
    ux, uy = usecase(x, y, t, 320); ucline(100, 600, ux, uy)

U.append(f'<text x="20" y="632" font-size="11" fill="#64748b" {FONT}>* 与智能分类联动: 建单自动识别类型与工期</text>')
U.append('</svg>')
open(os.path.join(OUT, "usecase-diagram.svg"), "w", encoding="utf-8").write("\n".join(U))
print("UseCase svg done")