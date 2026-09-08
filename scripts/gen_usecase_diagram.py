# -*- coding: utf-8 -*-
"""用例图美化: 系统边界 + 实心小人 + 白底蓝边投影胶囊 + include 虚线"""
from PIL import Image, ImageDraw, ImageFont

OUT = "D:/Hermes Agent CN Desktop/data/versions/0.19.0-cn.7/handcraft-order-system/docs/diagrams"
F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"
def f(sz, b=False): return ImageFont.truetype(FB if b else F, sz)

W, H = 2000, 1260
img = Image.new("RGBA", (W, H), (247, 251, 255, 255))
d = ImageDraw.Draw(img)
INK = (30, 41, 59)
BLUE = (29, 78, 216)
LINE = (148, 163, 184)
DASH = (100, 116, 139)

# 标题
d.text((40, 34), "用例图 · 四类角色", font=f(40, True), fill=INK)

# 系统边界
d.rounded_rectangle([60, 96, 1940, 1210], radius=24, outline=(203, 213, 225), width=4, fill=(255, 255, 255, 120))
d.text((120, 132), "独立手作创作者订单管理系统", font=f(30, True), fill=BLUE)

def actor(x, y, name):
    # 实心小人(现代 silhouette)
    d.ellipse([x-24, y-74, x+24, y-26], fill=INK)               # 头
    d.rounded_rectangle([x-36, y-24, x+36, y+42], radius=20, fill=INK)  # 身体
    d.text((x, y+66), name, font=f(28, True), fill=INK, anchor="mm")

def uc(cx, cy, text, w=340):
    d.ellipse([cx-w//2+5, cy-34+6, cx+w//2+5, cy+34+6], fill=(15, 23, 42, 40))  # 阴影
    d.ellipse([cx-w//2, cy-34, cx+w//2, cy+34], fill=(255, 255, 255, 255), outline=BLUE, width=4)
    d.text((cx, cy), text, font=f(26, False), fill=BLUE, anchor="mm")
    return (cx, cy)

def link(ax, ay, ux, uy):
    d.line([ax, ay, ux, uy], fill=LINE, width=3)

def dashlink(x1, y1, x2, y2):
    import math
    seg = 14
    dist = math.hypot(x2-x1, y2-y1)
    steps = int(dist // (seg*2))
    for i in range(steps):
        t0 = i*seg*2/dist; t1 = (i*seg*2+seg)/dist
        d.line([x1+(x2-x1)*t0, y1+(y2-y1)*t0, x1+(x2-x1)*t1, y1+(y2-y1)*t1], fill=DASH, width=3)

# 角色位置
actors = [("创作者", 220), ("客户", 560), ("管理员", 890), ("财务查看者", 1140)]
for name, y in actors:
    actor(180, y, name)

# 用例(各角色横带)
creator_cases = [("登录认证", 620, 150), ("创建订单 *", 620, 250), ("状态机流转 *", 620, 350),
                 ("录入耗料 / 工时 *", 1050, 150), ("库存出入库 *", 1050, 250), ("客户管理", 1050, 350),
                 ("排期日历 / 提醒", 620, 450), ("智能订单分类 <<system>>", 1050, 450)]
for t, x, y in creator_cases:
    ux, uy = uc(x, y, t, 360 if len(t) > 12 else 320)
    link(205, 220, ux, uy)

customer_cases = [("我的订单 / 进度", 640, 600), ("提交定制需求 *", 1040, 600), ("追踪预计完成", 640, 700)]
for t, x, y in customer_cases:
    ux, uy = uc(x, y, t, 340)
    link(205, 560, ux, uy)

admin_cases = [("用户管理", 640, 940), ("品类 / 分类管理", 1040, 940), ("公告发布", 640, 1040), ("经营总览", 1040, 1040)]
for t, x, y in admin_cases:
    ux, uy = uc(x, y, t, 320)
    link(205, 890, ux, uy)

ux, uy = uc(850, 1165, "经营报表(收支 / 趋势 / 复购 / 材料)", 480)
link(205, 1140, ux, uy)

# include 关系: 创建订单* -> 智能分类
dashlink(620+160, 250, 1050-170, 450)
d.text((760, 330), "<<include>>", font=f(24), fill=DASH)

# 图例
d.text((60, 1230), "* 与智能分类联动: 建单自动识别类型与工期    ·    虚线 = include(包含)关系", font=f(22), fill=(100, 116, 139))

img = img.convert("RGB")
img.save(OUT + "/usecase-diagram.png")
print("usecase saved")