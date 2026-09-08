# -*- coding: utf-8 -*-
"""E-R 图: dbdiagram.io 风格(深色表头白卡片 + 主键金标 + 外键蓝标 + 投影/斑马纹)"""
from PIL import Image, ImageDraw, ImageFont

OUT = "D:/Hermes Agent CN Desktop/data/versions/0.19.0-cn.7/handcraft-order-system/docs/diagrams"
F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"
def f(sz, b=False): return ImageFont.truetype(FB if b else F, sz)

# 画布
W, H = 2000, 1560
img = Image.new("RGBA", (W, H), (247, 251, 255, 255))
d = ImageDraw.Draw(img)

INK = (30, 41, 59)      # slate-800
HEAD = (30, 41, 59)     # 表头深色
MUT = (100, 116, 139)   # slate-500
TYPE = (148, 163, 184)  # slate-400 类型
LINE = (203, 213, 225)  # 边线
GOLD = (245, 158, 11)
BLUE = (59, 130, 246)

TITLE = "E-R 图 · handcraft_order 数据库（11 张表）"
d.text((40, 32), TITLE, font=f(40, True), fill=INK)

# 表定义: (表名, [(字段名, 类型, pk, fk), ...])
tables = [
    ("role", [("role_id", "int", 1, 0), ("role_code", "varchar", 0, 0), ("role_name", "varchar", 0, 0)]),
    ("user", [("user_id", "int", 1, 0), ("username", "varchar", 0, 0), ("password_hash", "varchar", 0, 0),
              ("role_id", "int", 0, 1), ("customer_id", "int", 0, 1)]),
    ("customer", [("customer_id", "int", 1, 0), ("name", "varchar", 0, 0), ("phone", "varchar", 0, 0),
                  ("creator_id", "int", 0, 1)]),
    ("product_category", [("id", "int", 1, 0), ("name", "varchar", 0, 0)]),
    ("orders", [("order_id", "int", 1, 0), ("order_no", "varchar", 0, 0), ("customer_id", "int", 0, 1),
                ("creator_id", "int", 0, 1), ("order_type", "varchar", 0, 0), ("status", "varchar", 0, 0),
                ("income", "decimal", 0, 0), ("cost", "decimal", 0, 0), ("profit", "decimal", 0, 0)]),
    ("order_status_log", [("log_id", "int", 1, 0), ("order_id", "int", 0, 1), ("from_status", "varchar", 0, 0),
                          ("to_status", "varchar", 0, 0), ("operator_id", "int", 0, 1)]),
    ("material_category", [("id", "int", 1, 0), ("name", "varchar", 0, 0)]),
    ("material", [("material_id", "int", 1, 0), ("name", "varchar", 0, 0), ("spec", "varchar", 0, 0),
                  ("unit", "varchar", 0, 0), ("stock_qty", "decimal", 0, 0), ("low_threshold", "decimal", 0, 0),
                  ("unit_price", "decimal", 0, 0)]),
    ("stock_movement", [("id", "int", 1, 0), ("material_id", "int", 0, 1), ("direction", "varchar", 0, 0),
                        ("quantity", "decimal", 0, 0), ("order_id", "int", 0, 1)]),
    ("order_material", [("id", "int", 1, 0), ("order_id", "int", 0, 1), ("material_id", "int", 0, 1),
                        ("qty_used", "decimal", 0, 0), ("unit_cost", "decimal", 0, 0)]),
    ("announcement", [("id", "int", 1, 0), ("title", "varchar", 0, 0), ("content", "text", 0, 0),
                      ("publisher_id", "int", 0, 1)]),
]

CW = 360            # 卡宽
HEADH = 46          # 表头高
ROWH = 44           # 字段行高
COLS = 3            # 3 列
colx = [80, 820, 1560]
row_gap = 90

def draw_card(title, fields, x, y):
    h = HEADH + len(fields) * ROWH
    # 阴影
    d.rounded_rectangle([x+6, y+8, x+CW+6, y+h+8], radius=10, fill=(15, 23, 42, 36))
    # 卡片底
    d.rounded_rectangle([x, y, x+CW, y+h], radius=10, fill=(255, 255, 255, 255), outline=LINE, width=2)
    # 表头(只顶部圆角)
    d.rounded_rectangle([x, y, x+CW, y+HEADH], radius=10, fill=HEAD)
    d.rectangle([x, y+HEADH-12, x+CW, y+HEADH], fill=HEAD)
    d.text((x+18, y+HEADH//2), title, font=f(28, True), fill=(255, 255, 255), anchor="lm")
    # 字段行
    for i, (name, typ, pk, fk) in enumerate(fields):
        ry = y + HEADH + i * ROWH
        if i % 2 == 1:
            d.rectangle([x+2, ry, x+CW-2, ry+ROWH], fill=(248, 250, 252, 255))
        if i < len(fields)-1:
            d.line([x, ry+ROWH, x+CW, ry+ROWH], fill=(241, 245, 249, 255), width=1)
        cx = x + 18
        if pk:  # 金色主键圆点
            d.ellipse([cx, ry+ROWH//2-7, cx+14, ry+ROWH//2+7], fill=GOLD)
            cx += 24
        nm = name
        col = INK
        if fk: col = (37, 99, 235)   # 外键字段名蓝色
        d.text((cx, ry+ROWH//2), nm, font=f(24), fill=col, anchor="lm")
        # 类型右对齐
        d.text((x+CW-18, ry+ROWH//2), typ, font=f(20), fill=TYPE, anchor="rm")
    return h

# 布局
pos = {}   # name -> (x, y, h, cx, cy)
y = 90
for r in range(4):
    row_tables = []
    if r == 0: row_tables = [0, 1, 2]
    elif r == 1: row_tables = [3, 4, 5]
    elif r == 2: row_tables = [6, 7, 8]
    else: row_tables = [9, 10]
    maxh = 0
    placed = []
    for ci, ti in enumerate(row_tables):
        name, fields = tables[ti][0], tables[ti][1]
        x = colx[ci] if ci < COLS else colx[0]
        h = draw_card(name, fields, x, y)
        pos[name] = (x, y, h)
        placed.append((name, x, y, h))
        maxh = max(maxh, h)
    y += maxh + row_gap

def ctr(name):
    x, y, h = pos[name]
    return (x + CW//2, y + h//2)

def rel(a, b, label, labdx=0, labdy=-16):
    ax, ay = ctr(a); bx, by = ctr(b)
    d.line([ax, ay, bx, by], fill=(148, 163, 184, 255), width=3)
    d.text(((ax+bx)//2 + labdx, (ay+by)//2 + labdy), label, font=f(22), fill=MUT)

# 关系
rel("role", "user", "1 : N", -30, -18)
rel("user", "customer", "N : 1", -30, -18)
rel("product_category", "orders", "1 : N", -30, -18)
rel("orders", "order_status_log", "1 : N", -30, -18)
rel("material_category", "material", "1 : N", -30, -18)
rel("material", "stock_movement", "1 : N", -30, -18)
# 竖关系(跨行): 从卡底/顶
def vrel(a, b, label):
    ax, ay = ctr(a); bx, by = ctr(b)
    y1 = pos[a][1] + pos[a][2]; y2 = pos[b][1]
    x1 = pos[a][0] + CW//2; x2 = pos[b][0] + CW//2
    d.line([x1, y1, x2, y2], fill=(148, 163, 184, 255), width=3)
    d.text((x1 + 16, (y1+y2)//2), label, font=f(22), fill=MUT)
vrel("user", "orders", "N:1 创作者")
vrel("customer", "orders", "1:N 客户")
vrel("orders", "order_material", "N:M 耗料")
vrel("material", "order_material", "1:N")

img = img.convert("RGB")
img.save(OUT + "/er-diagram.png")
print("ER(diagram.io style) saved")