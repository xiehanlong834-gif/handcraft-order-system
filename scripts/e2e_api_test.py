# -*- coding: utf-8 -*-
"""
端到端 API 测试: 覆盖规划文档全部四角色需求(P0+P1+简化P2)。
运行前提: 后端已启动(8080), MySQL handcraft_order 已建库, 种子数据就位。
用法: python scripts/e2e_api_test.py [base_url]
"""
import json
import sys
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
PASS = 0
FAIL = 0


def call(method, path, token=None, body=None, expect=200):
    """发请求; 返回 (ok, code, payload)"""
    global PASS, FAIL
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=15) as resp:
            code = resp.status
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        code = e.code
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"message": e.reason}
    ok = (expect is None) or (code == expect)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("  ! %s %s -> HTTP %d (期望 %d) %s" % (method, path, code, expect, str(payload)[:150]))
    return ok, code, payload


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [OK] %s" % name)
    else:
        FAIL += 1
        print("  [XX] %s %s" % (name, extra))


def login(u, p="123456"):
    ok, code, data = call("POST", "/api/auth/login", body={"username": u, "password": p}, expect=200)
    assert ok and data and data.get("token"), "登录失败: %s" % u
    return data


print("=" * 62)
print("E2E: 四角色全流程(创作者/客户/管理员/财务查看者)")
print("=" * 62)

print("\n[1] 登录与 RBAC 越权拦截")
creator = login("creator01"); admin = login("admin01"); finance = login("finance01")
xiaolin = login("xiaolin"); may = login("may")
ct, at, ft, xt, mt = creator["token"], admin["token"], finance["token"], xiaolin["token"], may["token"]
ok, _, me = call("GET", "/api/auth/me", ct)
check("creator /auth/me 角色正确", ok and me.get("roleCode") == "creator", str(me))
ok, code, _ = call("GET", "/api/auth/me", "bad-token", expect=401)
check("无效 token 拦截 401", ok)
ok, code, _ = call("POST", "/api/orders", xt, body={"customerId": 1, "productName": "x"}, expect=403)
check("越权拦截: 客户建单 403", ok)
ok, code, _ = call("POST", "/api/orders", ft, body={"customerId": 1, "productName": "x"}, expect=403)
check("越权拦截: 财务建单 403", ok)

print("\n[2] 建单 + 智能订单分类(创新点一)")
ok, _, r = call("POST", "/api/orders", ct, body={
    "customerId": 1, "productName": "刻名字的定制银手镯", "requirement": "刻 LOVE, 专属款",
    "quantity": 1, "unitPrice": 680, "remark": "急单"})
check("创作者建单成功", ok and r.get("orderId"), str(r))
order1 = r["orderId"]
check("定制类识别 CUSTOM", r.get("classify", {}).get("orderType") == "CUSTOM", str(r))
check("定制类预估工期 7 天", r.get("classify", {}).get("estimateDays") == 7, str(r))
ok, _, r2 = call("POST", "/api/orders", ct, body={"customerId": 2, "productName": "现货珍珠耳环", "quantity": 3, "unitPrice": 120})
check("现货 → READY 工期2天", ok and r2["classify"]["orderType"] == "READY", str(r2))
order2 = r2["orderId"]
ok, _, r3 = call("POST", "/api/orders", ct, body={"customerId": 2, "productName": "批量编织杯垫 团购", "quantity": 60, "unitPrice": 45})
check("批量 → BATCH 工期随数量 15 天", ok and r3["classify"]["orderType"] == "BATCH" and r3["classify"]["estimateDays"] == 15, str(r3))
order3 = r3["orderId"]
ok, _, r4 = call("POST", "/api/orders", ct, body={"customerId": 1, "productName": "普通帆布袋", "quantity": 1, "unitPrice": 99})
check("未命中 → 通用类兜底 + warn", ok and r4["classify"]["isFallback"] is True and "warn" in r4, str(r4))
order4 = r4["orderId"]

print("\n[3] 订单状态机(待确认→制作中→待发货→已完成)")
for to in ("IN_PRODUCTION", "PENDING_SHIPMENT", "COMPLETED"):
    ok, _, r = call("PATCH", "/api/orders/%d/status" % order1, ct, body={"toStatus": to, "note": "流转"})
    check("状态流转到 %s" % to, ok and r.get("toStatus") == to, str(r))
ok, code, _ = call("PATCH", "/api/orders/%d/status" % order1, ct, body={"toStatus": "PENDING_CONFIRM"}, expect=400)
check("非法流转(已完成→待确认) 400", ok)
ok, _, detail = call("GET", "/api/orders/%d" % order1, ct)
check("详情含 4 条审计日志", ok and len(detail.get("statusLogs", [])) >= 4, str(detail.get("statusLogs"))[:150])
check("完成自动写 actualCompleteDate", ok and detail.get("actualCompleteDate"))

print("\n[4] 材料库存 + 成本利润(P0)")
ok, _, mats = call("GET", "/api/materials", ct)
silver = next(m for m in mats if m["name"] == "925银链")
before = float(silver["stockQty"])
ok, _, r = call("POST", "/api/orders/%d/materials" % order2, ct, body={"materialId": silver["materialId"], "quantityUsed": 2})
check("订单登记耗料成功", ok, str(r))
ok, code, _ = call("POST", "/api/orders/%d/materials" % order2, ct, body={"materialId": silver["materialId"], "quantityUsed": 99999}, expect=400)
check("库存不足拒绝 400", ok)
ok, _, mats = call("GET", "/api/materials", ct)
after = float(next(m for m in mats if m["name"] == "925银链")["stockQty"])
check("触发器扣库存 %.0f→%.0f" % (before, before - 2), abs(after - (before - 2)) < 0.001, "after=%s" % after)
ok, _, r = call("POST", "/api/orders/%d/labor-cost" % order2, ct, body={"laborCost": 60})
check("录入工时成本", ok)
ok, _, detail = call("GET", "/api/orders/%d" % order2, ct)
income = float(detail["income"]); mc = float(detail["materialCost"]); profit = float(detail["profit"])
check("材料成本自动汇总 2×8=16", abs(mc - 16.0) < 0.01, str(mc))
check("利润 = 收入-材料-工时", abs(profit - (income - mc - 60)) < 0.01, "profit=%s" % profit)
ok, _, mv = call("GET", "/api/materials/%d/movements" % silver["materialId"], ct)
check("流水含订单关联出库", ok and any(x.get("orderId") == order2 for x in mv), str(mv[:2]))
ok, _, r = call("POST", "/api/materials/%d/in" % silver["materialId"], ct, body={"quantity": 50, "note": "补货"})
check("入库 +50", ok, str(r))
ok, _, low = call("GET", "/api/materials/low-stock", ct)
check("低库存预警列表", ok and isinstance(low, list), str(low)[:120])

print("\n[5] 客户角色(追踪/定制)")
ok, _, my = call("GET", "/api/my/orders", xt)
check("客户A 可见订单含 order1", ok and any(o["orderId"] == order1 for o in my), str(my)[:150])
ok, code, _ = call("GET", "/api/orders/%d" % order1, mt, expect=403)
check("数据隔离: 客户B 访问客户A 订单 403", code == 403)
ok, _, r = call("POST", "/api/my/custom-requests", xt, body={"productName": "定制真皮卡包", "requirement": "刻字 小林 专属", "quantity": 1})
check("客户提交定制(CUSTOM 自动分类)", ok and r["classify"]["orderType"] == "CUSTOM", str(r))
order5 = r["orderId"]
ok, _, detail = call("GET", "/api/orders/%d" % order5, xt)
check("定制单待确认", ok and detail.get("status") == "PENDING_CONFIRM")
ok, code, _ = call("PATCH", "/api/orders/%d/status" % order5, xt, body={"toStatus": "IN_PRODUCTION"}, expect=403)
check("客户无权流转订单 403", ok)
ok, _, r = call("PATCH", "/api/orders/%d/status" % order5, ct, body={"toStatus": "IN_PRODUCTION"})
check("创作者确认定制单开工", ok and r.get("toStatus") == "IN_PRODUCTION", str(r))

print("\n[6] 排期与工期提醒")
ok, _, schedule = call("GET", "/api/schedule", ct)
check("排期日历数据", ok and isinstance(schedule, list))
ok, _, reminders = call("GET", "/api/orders/due-reminders", ct)
check("工期提醒列表", ok and isinstance(reminders, list))

print("\n[7] 客户管理(P1)")
ok, _, cust = call("GET", "/api/customers", ct)
check("客户列表含脱敏电话", ok and "phoneMasked" in cust[0], str(cust)[:150])
ok, _, r = call("POST", "/api/customers", ct, body={"name": "测试新客", "phone": "13900009999", "tags": "新客"})
check("新增客户", ok and r.get("customerId"), str(r))
new_cid = r["customerId"]
ok, _, r = call("PUT", "/api/customers/%d" % new_cid, ct, body={"tags": "新客,高潜"})
check("更新客户", ok)
ok, _, detail = call("GET", "/api/customers/%d" % new_cid, ct)
check("客户详情含订单历史", ok and isinstance(detail.get("orders"), list))

print("\n[8] 管理员后台")
ok, _, users = call("GET", "/api/admin/users", at)
check("用户列表(电话脱敏)", ok and "phoneMasked" in users[0], str(users)[:150])
ok, code, r = call("POST", "/api/admin/users", at, body={"username": "temp_fin", "password": "pass123", "realName": "临时财务", "roleCode": "finance"}, expect=None)
if ok and r.get("userId"):
    uid = r["userId"]
    check("管理员创建财务账号", True)
elif code == 400 and "已存在" in str(r):
    uid = next(u["userId"] for u in call("GET", "/api/admin/users?roleCode=finance", at)[2] if u["username"] == "temp_fin")
    check("管理员创建财务账号(幂等: 已存在则复用)", True)
else:
    check("管理员创建财务账号", False, str(r)); uid = None
# 幂等: 复用旧账号时先恢复启用状态
if uid:
    call("PUT", "/api/admin/users/%d" % uid, at, body={"status": 1})
tmp = login("temp_fin", "pass123")
check("新账号登录成功(BCrypt)", bool(tmp.get("token")))
ok, _, r = call("PUT", "/api/admin/users/%d" % uid, at, body={"status": 0})
check("禁用账号", ok)
ok, code, _ = call("POST", "/api/auth/login", body={"username": "temp_fin", "password": "pass123"}, expect=400)
check("禁用账号不可登录", ok)
ok, code, r = call("POST", "/api/admin/product-categories", at, body={"name": "押花"}, expect=None)
check("新增产品分类", (ok or (code == 400 and "已存在" in str(r))), str(r))
ok, _, r = call("POST", "/api/admin/announcements", at, body={"title": "国庆放假通知", "content": "10.1-10.3 暂停接单"})
check("发布公告", ok and r.get("announcementId"), str(r))
ok, _, ann = call("GET", "/api/admin/announcements", ct)
check("创作者可看公告", ok and len(ann) >= 1)

print("\n[9] 财务查看者(经营报表)")
ok, _, s = call("GET", "/api/reports/summary", ft)
check("收支总览", ok and "profit" in s, str(s)[:150])
ok, _, trend = call("GET", "/api/reports/profit-trend?group=month", ft)
check("利润趋势(月)", ok and isinstance(trend, list) and len(trend) >= 1, str(trend)[:180])
ok, _, rep = call("GET", "/api/reports/repurchase", ft)
check("客户复购/价值分层", ok and "repurchaseRate" in rep and "valueTiers" in rep, str(rep)[:180])
ok, _, mrep = call("GET", "/api/reports/materials", ft)
check("材料消耗分析", ok and "items" in mrep and "totalCost" in mrep, str(mrep)[:180])
ok, _, ov = call("GET", "/api/admin/overview", at)
check("管理员经营总览", ok and "totalProfit" in ov, str(ov)[:180])
ok, code, _ = call("GET", "/api/admin/users", ct, expect=403)
check("客户访问管理接口 403", ok)
ok, code, _ = call("POST", "/api/orders", ft, body={}, expect=403)
check("财务不可写订单 403", ok)

print("\n[10] 收尾闭环")
call("PATCH", "/api/orders/%d/status" % order5, ct, body={"toStatus": "PENDING_SHIPMENT"})
ok, _, r = call("PATCH", "/api/orders/%d/status" % order5, ct, body={"toStatus": "COMPLETED"})
check("定制单完成", ok, str(r))
ok, _, r = call("POST", "/api/orders/%d/archive" % order1, ct)
check("订单1 归档", ok and r.get("status") == "ARCHIVED", str(r))
call("POST", "/api/orders/%d/cancel" % order4, ct)
ok, _, r = call("POST", "/api/orders/%d/archive" % order4, ct)
check("订单4 取消并归档", ok and r.get("status") == "ARCHIVED", str(r))

print()
print("=" * 62)
print("E2E 结果: 通过 %d 项, 失败 %d 项" % (PASS, FAIL))
print("=" * 62)
sys.exit(1 if FAIL else 0)