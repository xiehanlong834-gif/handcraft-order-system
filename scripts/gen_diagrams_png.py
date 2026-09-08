# -*- coding: utf-8 -*-
"""用 Pillow 直接绘制高清 E-R 图 + 用例图 PNG(替代浏览器渲染 SVG 截图, 稳定可控)"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "diagrams")
os.makedirs(OUT, exist_ok=True)
FONT = "C:/Windows/Fonts/msyh.ttc"
FBOLD = "C:/Windows/Fonts/msyhbd.ttc"

def f(sz, bold=False):
    return ImageFont.truetype(FBOLD if bold else FONT, sz)

INK = (15, 23, 42)          # slate 900
MUTED = (71, 85, 105)       # slate 600
BLUE = (29, 78, 216)        # 主蓝
LINE = (148, 163, 184)      # 线
BG = (247, 251, 255)

# ==================== E-R 图 ====================
W, H = 1760, 1460
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
d.text((40, 30), "E-R 图 · handcraft_order 数据库(11 表)", font=f(40, True), fill=INK)

boxes = [  # (标题, [(字段..)], x, y, w, h)
    ("role 角色", ["role_id PK", "role_code", "role_name"], 80, 120),
    ("user 用户", ["user_id PK", "username", "password_hash", "role_id FK · customer_id FK"], 640, 120),
    ("customer 客户", ["customer_id PK", "name", "phone", "creator_id FK"], 1200, 120),
    ("product_category", ["id PK", "name"], 80, 560),
    ("orders 订单", ["order_id PK", "order_no", "customer_id/creator_id FK", "order_type · status", "income · cost · profit"], 640, 540),
    ("order_status_log", ["log_id PK", "order_id FK", "from→to", "operator_id FK"], 1200, 540),
    ("material_category", ["id PK", "name"], 80, 1000),
    ("material 材料", ["material_id PK", "name · spec · unit", "stock_qty", "low_threshold · unit_price"], 640, 980),
    ("stock_movement", ["id PK", "material_id FK", "IN/OUT · order_id?", "quantity"], 1200, 980),
    ("order_material", ["id PK", "order_id FK", "material_id FK", "qty_used · unit_cost"], 640, 1320),
    ("announcement", ["id PK", "title · content", "publisher_id FK"], 1200, 1320),
]
BW, BH = 440, 220
for title, fields, x, y in boxes:
    d.rounded_rectangle([x, y, x+BW, y+BH], radius=14, outline=BLUE, width=4)
    d.text((x+BW//2, y+28), title, font=f(30, True), fill=BLUE, anchor="mm")
    ty = y + 72
    for fd in fields:
        d.text((x+26, ty), fd, font=f(24), fill=MUTED, anchor="lm")
        ty += 36

def line(x1, y1, x2, y2, label=None, lx=None, ly=None):
    d.line([x1, y1, x2, y2], fill=LINE, width=3)
    if label:
        mx, my = (x1+x2)//2, (y1+y2)//2
        d.text((lx if lx else mx+14, ly if ly else my-14), label, font=f(22), fill=MUTED)

line(520, 230, 640, 230, "1:N 角色分配")
line(1080, 230, 1200, 230, "N:1 归属")
line(860, 340, 860, 540, "N:1 创作者接单")
line(1420, 340, 1420, 540, "1:N 客户下单")
line(300, 670, 640, 670, "1:N 分类", 300, 660)
line(1080, 650, 1420, 650, "1:N 审计")
line(300, 1110, 640, 1110, "1:N 品类")
line(1080, 1090, 1420, 1090, "1:N 流水")
line(860, 760, 860, 1320, "N:M 耗料", 900, 1000)
line(860, 1200, 640, 1320, "1:N 归属", 700, 1280)
img.save(os.path.join(OUT, "er-diagram.png"))
print("ER PNG ok")

# ==================== 用例图 ====================
W2, H2 = 1760, 1120
im = Image.new("RGB", (W2, H2), BG)
g = ImageDraw.Draw(im)
g.text((40, 30), "用例图 · 四类角色", font=f(40, True), fill=INK)

def actor(x, y, name):
    # 小人
    g.ellipse([x-24, y-70, x+24, y-22], outline=INK, width=4)          # 头
    g.line([x, y-22, x, y+10], fill=INK, width=4)                       # 身
    g.line([x-30, y-10, x+30, y-10], fill=INK, width=4)                 # 手
    g.line([x, y+10, x-26, y+46], fill=INK, width=4)                    # 腿
    g.line([x, y+10, x+26, y+46], fill=INK, width=4)
    g.text((x, y+66), name, font=f(26, True), fill=INK, anchor="mm")

def uc(cx, cy, text, w=340):
    g.ellipse([cx-w//2, cy-32, cx+w//2, cy+32], outline=BLUE, width=4)
    g.text((cx, cy), text, font=f(24), fill=BLUE, anchor="mm")
    return (cx, cy)

def alink(ax, ay, ux, uy):
    g.line([ax, ay, ux, uy], fill=LINE, width=3)

# 角色
actor(170, 190, "创作者")
actor(170, 500, "客户")
actor(170, 810, "管理员")
actor(170, 1040, "财务查看者")

# 创作者用例
cc = [("登录认证", 620, 130, 260), ("创建订单 *", 620, 220, 260), ("状态机流转 *", 620, 310, 280),
      ("录入耗料/工时 *", 1020, 130, 320), ("库存出入库 *", 1020, 220, 300), ("客户管理", 1020, 310, 260),
      ("排期/提醒", 620, 400, 260), ("智能订单分类 <<系统>>", 1020, 400, 340)]
for t, x, y, w in cc:
    ux, uy = uc(x, y, t, w)
    alink(200, 190, ux, uy)

# 客户用例
for t, x, y, w in [("我的订单/进度", 640, 560, 280), ("提交定制需求 *", 640, 660, 280), ("追踪预计完成", 1040, 610, 280)]:
    ux, uy = uc(x, y, t, w)
    alink(200, 500, ux, uy)

# 管理员用例
for t, x, y, w in [("用户管理", 640, 860, 260), ("品类/分类管理", 640, 950, 300), ("公告发布", 1040, 860, 260), ("经营总览", 1040, 950, 260)]:
    ux, uy = uc(x, y, t, w)
    alink(200, 810, ux, uy)

# 财务
ux, uy = uc(820, 1075, "经营报表(收支/趋势/复购/材料)", 460)
alink(200, 1040, ux, uy)

g.text((40, H2-40), "* 与智能分类联动: 建单自动识别类型与工期", font=f(22), fill=MUTED)
im.save(os.path.join(OUT, "usecase-diagram.png"))
print("UseCase PNG ok")