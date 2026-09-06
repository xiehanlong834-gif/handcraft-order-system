# -*- coding: utf-8 -*-
"""
真实环境四角色全流程冒烟测试(独立于演示种子, 自建自清理)
前置: 后端 8080 运行; 库中至少存在 creator(zhangtianyu) 与 admin 账号。
测试会临时创建 smoke_* 数据, 结束自动清理, 不污染业务数据。
用法: python scripts/full_roles_smoke.py [creator账号] [creator密码] [admin账号] [admin密码]
"""
import json, sys, time
import urllib.request, urllib.error

CREATOR_U = sys.argv[1] if len(sys.argv) > 1 else "zhangtianyu"
CREATOR_P = sys.argv[2] if len(sys.argv) > 2 else "888888"
ADMIN_U   = sys.argv[3] if len(sys.argv) > 3 else "admin"
ADMIN_P   = sys.argv[4] if len(sys.argv) > 4 else "888888"
BASE = "http://127.0.0.1:8080"
PASS = FAIL = 0
CREATED = {"cats": [], "mats": [], "custs": [], "orders": [], "users": [], "anns": []}

def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=12) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode() or "{}")
        except Exception: return e.code, {}

def check(name, ok, extra=""):
    global PASS, FAIL
    if ok: PASS += 1; print("  [OK] " + name)
    else:  FAIL += 1; print("  [XX] " + name + "  " + extra)

def login(u, p):
    c, r = call("POST", "/api/auth/login", body={"username": u, "password": p})
    if c != 200: raise SystemExit("登录失败 %s: %s" % (u, r))
    return r["token"]

print("=" * 60); print("四角色全流程冒烟: 真实环境(自建自清理)"); print("=" * 60)
creator = login(CREATOR_U, CREATOR_P)
admin = login(ADMIN_U, ADMIN_P)
print("[角色登录] creator=%s admin=%s OK" % (CREATOR_U, ADMIN_U))

def cleanup():
    """幂等清理 smoke_* 测试痕迹(单连接, FK 关闭)"""
    import pymysql
    con = pymysql.connect(host="127.0.0.1", user="root", password="", database="handcraft_order", charset="utf8mb4")
    with con.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("DELETE FROM order_material WHERE order_id IN (SELECT o.order_id FROM `orders` o JOIN customer c ON c.customer_id=o.customer_id WHERE c.name LIKE 'smoke%' OR c.name='冒烟客户' OR c.phone LIKE '135%')")
        cur.execute("DELETE FROM order_status_log WHERE order_id IN (SELECT o.order_id FROM `orders` o JOIN customer c ON c.customer_id=o.customer_id WHERE c.name LIKE 'smoke%' OR c.name='冒烟客户' OR c.phone LIKE '135%')")
        cur.execute("DELETE FROM stock_movement WHERE note LIKE '冒烟%' OR order_id IN (SELECT o.order_id FROM `orders` o JOIN customer c ON c.customer_id=o.customer_id WHERE c.name LIKE 'smoke%' OR c.name='冒烟客户')")
        cur.execute("DELETE FROM `orders` WHERE customer_id IN (SELECT customer_id FROM customer WHERE name LIKE 'smoke%' OR name='冒烟客户' OR phone LIKE '135%')")
        cur.execute("DELETE FROM material WHERE name='smoke_mat'")
        cur.execute("DELETE FROM customer WHERE name LIKE 'smoke%' OR name='冒烟客户' OR phone LIKE '135%'")
        cur.execute("DELETE FROM `user` WHERE username LIKE 'smoke%'")
        cur.execute("DELETE FROM announcement WHERE title='smoke_ann'")
        cur.execute("DELETE FROM material_category WHERE name='smoke_cat'")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    con.commit(); con.close()

cleanup()  # 预清理: 保证可重复运行

# ---------- 管理员 ----------
print("\n[管理员]")
c, r = call("GET", "/api/admin/users", admin)
check("用户列表", c == 200 and isinstance(r, list))
c, r = call("POST", "/api/admin/material-categories", admin, {"name": "smoke_cat"})
check("建品类", c == 200, str(r)); cat_id = r.get("message") and (c == 200)
_, r = call("GET", "/api/admin/material-categories", admin)
cat_id = next((x["id"] for x in r if x["name"] == "smoke_cat"), None)
CREATED["cats"].append(cat_id)
c, r = call("POST", "/api/admin/users", admin, {"username": "smoke_fin", "password": "fin123456", "realName": "冒烟财务", "roleCode": "finance"})
check("建财务账号", c == 200 and r.get("userId"), str(r)); CREATED["users"].append(r.get("userId"))
c, r = call("POST", "/api/admin/announcements", admin, {"title": "smoke_ann", "content": "冒烟公告"})
check("发布公告", c == 200 and r.get("announcementId"), str(r)); CREATED["anns"].append(r.get("announcementId"))
c, r = call("GET", "/api/admin/overview", admin)
check("经营总览", c == 200 and "totalOrders" in r, str(r)[:120])
finance = login("smoke_fin", "fin123456")

# ---------- 创作者 ----------
print("\n[创作者]")
c, r = call("POST", "/api/customers", creator, {"name": "smoke_cust", "phone": "13500000001", "tags": "smoke"})
check("建档客户", c == 200 and r.get("customerId"), str(r)); cust_id = r["customerId"]; CREATED["custs"].append(cust_id)
c, r = call("POST", "/api/materials", creator, {"materialCategoryId": cat_id, "name": "smoke_mat", "spec": "1m", "unit": "卷", "stockQty": 10, "lowStockThreshold": 2, "unitPrice": 5})
check("建材料", c == 200 and r.get("materialId"), str(r)); mat_id = r["materialId"]; CREATED["mats"].append(mat_id)
c, r = call("POST", "/api/materials/%d/in" % mat_id, creator, {"quantity": 20, "note": "冒烟入库"})
check("入库+20", c == 200, str(r))
c, r = call("POST", "/api/materials/%d/out" % mat_id, creator, {"quantity": 3, "note": "冒烟出库"})
check("出库-3", c == 200, str(r))
_, r = call("GET", "/api/materials", creator)
stk = next((x["stockQty"] for x in r if x["materialId"] == mat_id), None)
check("库存 10+20-3=27", stk == 27, "stock=%s" % stk)
c, r = call("POST", "/api/orders", creator, {"customerId": cust_id, "productName": "冒烟定制银手镯", "requirement": "专属定制刻字", "quantity": 1, "unitPrice": 500})
check("建定制单(CUSTOM)", c == 200 and r.get("classify", {}).get("orderType") == "CUSTOM", str(r)[:150])
oid = r.get("orderId"); CREATED["orders"].append(oid)
check("预估工期7天", r.get("classify", {}).get("estimateDays") == 7)
c, r = call("POST", "/api/orders/%d/materials" % oid, creator, {"materialId": mat_id, "quantityUsed": 2})
check("登记耗料2件", c == 200, str(r))
c, r = call("POST", "/api/orders/%d/labor-cost" % oid, creator, {"laborCost": 80})
check("录入工时80", c == 200, str(r))
for st in ("IN_PRODUCTION", "PENDING_SHIPMENT", "COMPLETED"):
    c, r = call("PATCH", "/api/orders/%d/status" % oid, creator, {"toStatus": st})
    check("流转→%s" % st, c == 200, str(r))
_, r = call("GET", "/api/orders/%d" % oid, creator)
income = float(r.get("income", 0)); mc = float(r.get("materialCost", 0)); lc = float(r.get("laborCost", 0)); pf = float(r.get("profit", 0))
check("利润=500-10-80=410", abs(pf - (500 - 10 - 80)) < 0.01, "income=%s mc=%s lc=%s profit=%s" % (income, mc, lc, pf))
check("完成写入实际日期", bool(r.get("actualCompleteDate")))
c, r = call("GET", "/api/orders/due-reminders", creator)
check("工期提醒接口", c == 200 and isinstance(r, list))
c, r = call("GET", "/api/schedule", creator)
check("排期接口", c == 200 and isinstance(r, list))

# ---------- 客户(自助注册) ----------
print("\n[客户]")
uname = "smoke_cust_u"
c, r = call("POST", "/api/auth/register", body={"username": uname, "password": "cust123456", "nickname": "冒烟客户", "phone": "13500000002"})
check("自助注册客户", c == 200 and r.get("roleCode") == "customer", str(r))
_, r = call("GET", "/api/admin/users", admin)
cu = next((x for x in r if x["username"] == uname), None)
if cu: CREATED["users"].append(cu["userId"])
cust_tok = login(uname, "cust123456")
c, r = call("GET", "/api/my/orders", cust_tok)
check("新客户看不到他人订单(数据隔离)", c == 200 and not r, str(r)[:100])
c, r = call("POST", "/api/my/custom-requests", cust_tok, {"productName": "冒烟定制卡包", "requirement": "按需定制", "quantity": 1})
check("提交定制需求(CUSTOM)", c == 200 and r.get("classify", {}).get("orderType") == "CUSTOM", str(r)[:150])
oid2 = r.get("orderId"); CREATED["orders"].append(oid2)
c, r = call("GET", "/api/my/orders", cust_tok)
check("提交后本人可见该定制单", c == 200 and any(o.get("orderId") == oid2 for o in r), str(r)[:120])
c, r = call("PATCH", "/api/orders/%d/status" % oid2, creator, {"toStatus": "IN_PRODUCTION"})
check("创作者确认开工", c == 200, str(r))
st, _ = call("PATCH", "/api/orders/%d/status" % oid2, cust_tok, {"toStatus": "COMPLETED"})
check("客户无权流转订单 403", st == 403, "status=%s" % st)
# 客户归属创作者可见
_, r = call("GET", "/api/customers", creator)
check("创作者可见注册客户", any(x["name"] == "冒烟客户" for x in r), str(r)[:100])

# ---------- 财务 ----------
print("\n[财务查看者]")
c, r = call("GET", "/api/reports/summary", finance)
check("收支总览(含1完成单)", c == 200 and float(r.get("income", 0)) >= 499, str(r)[:120])
c, r = call("GET", "/api/reports/profit-trend?group=month", finance)
check("利润趋势(月)", c == 200 and len(r) >= 1, str(r)[:120])
c, r = call("GET", "/api/reports/repurchase", finance)
check("客户复购/分层", c == 200 and "valueTiers" in r, str(r)[:100])
c, r = call("GET", "/api/reports/materials", finance)
check("材料消耗(含10元)", c == 200 and float(r.get("totalCost", 0)) >= 9.9, str(r)[:100])
st, _ = call("POST", "/api/orders", finance, body={})
check("财务不可建单 403", st == 403, "status=%s" % st)

print("\n" + "=" * 60)
print("冒烟结果: 通过 %d, 失败 %d" % (PASS, FAIL))

cleanup()  # 结尾清理: 还原测试数据

_, r = call("GET", "/api/admin/users", admin)
left_users = [x["username"] for x in r]
_, r = call("GET", "/api/materials", creator)
left_mats = [x["name"] for x in r]
print("清理后账号:", left_users)
print("清理后材料:", left_mats)
print("冒烟完成(数据已还原)")
sys.exit(1 if FAIL else 0)