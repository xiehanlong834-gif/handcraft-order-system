# -*- coding: utf-8 -*-
"""PPT 演示模拟数据(可重复运行: 先清理旧 ppt_ 数据再重建)。 用法: python scripts/ppt_demo_data.py"""
import json, sys, urllib.request, urllib.error
BASE = "http://127.0.0.1:8080"

def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")

def login(u, p):
    c, r = call("POST", "/api/auth/login", body={"username": u, "password": p})
    assert c == 200, (u, r)
    return r["token"]

# 清理旧 ppt_ 模拟数据(外键逆序)
import pymysql
con = pymysql.connect(host="127.0.0.1", user="root", password="", database="handcraft_order", charset="utf8mb4")
with con.cursor() as cur:
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("DELETE FROM order_material WHERE order_id IN (SELECT order_id FROM `orders` o JOIN customer c ON c.customer_id=o.customer_id WHERE c.name LIKE 'ppt%' OR c.name IN ('小美','老张','李姐'))")
    cur.execute("DELETE FROM order_status_log WHERE order_id IN (SELECT order_id FROM `orders` o JOIN customer c ON c.customer_id=o.customer_id WHERE c.name LIKE 'ppt%' OR c.name IN ('小美','老张','李姐'))")
    cur.execute("DELETE FROM stock_movement WHERE note LIKE 'ppt%'")
    cur.execute("DELETE FROM `orders` WHERE customer_id IN (SELECT customer_id FROM customer WHERE name LIKE 'ppt%' OR name IN ('小美','老张','李姐'))")
    cur.execute("DELETE FROM material WHERE name IN ('ppt_925银链','ppt_植鞣革','ppt_黄铜扣','ppt_棉麻线')")
    cur.execute("DELETE FROM customer WHERE name IN ('小美','老张','李姐') OR name LIKE 'ppt%'")
    cur.execute("DELETE FROM `user` WHERE username IN ('ppt_cust','ppt_fin')")
    cur.execute("DELETE FROM material_category WHERE name IN ('ppt_金属','ppt_皮革','ppt_线材')")
    cur.execute("DELETE FROM announcement WHERE title LIKE 'ppt%'")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")
con.commit(); con.close()
print("已清理旧 ppt_ 模拟数据")

cr = login("zhangtianyu", "888888")
ad = login("admin", "888888")

# 品类(creator 可建)
cat = {}
for n in ("ppt_金属", "ppt_皮革", "ppt_线材"):
    call("POST", "/api/admin/material-categories", cr, {"name": n})
_, r = call("GET", "/api/admin/material-categories", cr)
for x in r:
    if x["name"] in ("ppt_金属", "ppt_皮革", "ppt_线材"): cat[x["name"]] = x["id"]

# 材料(带初始库存)
mats = [("ppt_925银链", "ppt_金属", "45cm 项链", "条", 60, 10, 12),
        ("ppt_植鞣革", "ppt_皮革", "A4 原色", "平方尺", 30, 8, 18),
        ("ppt_黄铜扣", "ppt_皮革", "20mm", "个", 120, 20, 3),
        ("ppt_棉麻线", "ppt_线材", "5mm 亚麻色", "卷", 20, 5, 6)]
mat_id = {}
for name, cn, spec, unit, stk, thr, up in mats:
    c, r = call("POST", "/api/materials", cr, {"materialCategoryId": cat[cn], "name": name, "spec": spec, "unit": unit, "stockQty": stk, "lowStockThreshold": thr, "unitPrice": up})
    assert c == 200, r
    mat_id[name] = r["materialId"]
    call("POST", "/api/materials/%d/in" % r["materialId"], cr, {"quantity": stk, "note": "ppt 期初入库"})

# 客户: 注册客户(小美, 用于客户视图) + 建档 老张/李姐
c, r = call("POST", "/api/auth/register", body={"username": "ppt_cust", "password": "ppt123456", "nickname": "小美", "phone": "13800001234"})
assert c == 200, r
_, r = call("GET", "/api/customers", cr)
cust = {x["name"]: x["customerId"] for x in r if x["name"] in ("小美",)}
for nm, ph in (("老张", "13900005678"), ("李姐", "13700009012")):
    c, r = call("POST", "/api/customers", cr, {"name": nm, "phone": ph})
    cust[nm] = r["customerId"]
print("客户:", cust)

# 订单 1: 小美 定制银手镯 → 制作中(耗料+工时)
c, r = call("POST", "/api/orders", cr, {"customerId": cust["小美"], "productName": "定制银手镯(刻字心形)", "requirement": "专属定制刻字", "quantity": 1, "unitPrice": 500})
o1 = r["orderId"]; print("订单1 类型:", r["classify"]["orderType"], "工期", r["classify"]["estimateDays"])
call("POST", "/api/orders/%d/materials" % o1, cr, {"materialId": mat_id["ppt_925银链"], "quantityUsed": 2})
call("POST", "/api/orders/%d/labor-cost" % o1, cr, {"laborCost": 80})
call("PATCH", "/api/orders/%d/status" % o1, cr, {"toStatus": "IN_PRODUCTION"})

# 订单 2: 老张 现货帆布包 → 待发货
c, r = call("POST", "/api/orders", cr, {"customerId": cust["老张"], "productName": "现货帆布托特包", "requirement": "现货直发", "quantity": 1, "unitPrice": 120})
o2 = r["orderId"]
call("POST", "/api/orders/%d/labor-cost" % o2, cr, {"laborCost": 20})
call("PATCH", "/api/orders/%d/status" % o2, cr, {"toStatus": "IN_PRODUCTION"})
call("PATCH", "/api/orders/%d/status" % o2, cr, {"toStatus": "PENDING_SHIPMENT"})

# 订单 3: 李姐 批量钥匙扣 → 已完成
c, r = call("POST", "/api/orders", cr, {"customerId": cust["李姐"], "productName": "黄铜钥匙扣(批量团购)", "requirement": "批量团购100个", "quantity": 100, "unitPrice": 6})
o3 = r["orderId"]
call("POST", "/api/orders/%d/materials" % o3, cr, {"materialId": mat_id["ppt_黄铜扣"], "quantityUsed": 100})
call("POST", "/api/orders/%d/labor-cost" % o3, cr, {"laborCost": 150})
for st in ("IN_PRODUCTION", "PENDING_SHIPMENT", "COMPLETED"):
    call("PATCH", "/api/orders/%d/status" % o3, cr, {"toStatus": st})

# 订单 4: 小美 定制皮卡包(新单, 待确认→提醒横幅)
c, r = call("POST", "/api/orders", cr, {"customerId": cust["小美"], "productName": "定制植鞣革皮卡包", "requirement": "专属定制压印名字", "quantity": 1, "unitPrice": 680})
o4 = r["orderId"]; print("订单4(提醒示例) 类型:", r["classify"]["orderType"], "预估完成:", r["classify"]["estimatedCompleteDate"])

# 财务账号 + 公告(ppt 前缀, 截完图即可清理)
call("POST", "/api/admin/users", ad, {"username": "ppt_fin", "password": "ppt123456", "realName": "财务小陈", "roleCode": "finance"})
call("POST", "/api/admin/announcements", ad, {"title": "ppt_中秋节手作周: 全场定制 9 折", "content": "9月第二周, 定制订单享9折优惠, 新客立减20元。"})

# 验证
_, r = call("GET", "/api/reports/summary", login("ppt_fin", "ppt123456"))
print("财务总览:", {k: r[k] for k in ("income", "cost", "profit", "totalOrders", "completedOrders") if k in r})
_, r = call("GET", "/api/orders", cr)
print("订单列表数:", len(r), "| 各状态:", [x["status"] for x in r])
_, r = call("GET", "/api/materials", cr)
print("材料数:", len(r), "| 低库存预警:", [x["name"] for x in r if x.get("lowStock")])
print("模拟数据就绪: 客户小美/老张/李姐, 材料4种, 订单4单(制作中/待发货/已完成/新单)")