# -*- coding: utf-8 -*-
"""order_classifier 单元测试 —— 零依赖, 直接运行: python test_order_classifier.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from order_classifier import (
    classify, estimate_duration, estimate_due_date,
    needs_reminder, filter_reminder_orders,
    ORDER_TYPE_LABEL,
)
from datetime import date

failures = []

def check(name, actual, expected):
    if actual == expected:
        print("  PASS  %s" % name)
    else:
        failures.append(name)
        print("  FAIL  %s: expected=%r got=%r" % (name, expected, actual))

print("== 关键词识别 ==")
check("定制: '刻名字的定制银手镯'",
      classify("刻名字的定制银手镯")["order_type"], "CUSTOM")
check("定制: '专属款'",
      classify("专属款珐琅胸针")["order_type"], "CUSTOM")
check("定制: '个性化'",
      classify("个性化帆布包")["order_type"], "CUSTOM")
check("定制: '按需'",
      classify("按需制作陶艺花瓶")["order_type"], "CUSTOM")
check("现货: '现货'",
      classify("现货珍珠耳环")["order_type"], "READY")
check("现货: '现款'/'成品'",
      classify("现款成品皮手环")["order_type"], "READY")
check("批量: '批量'",
      classify("批量编织杯垫")["order_type"], "BATCH")
check("批量: '团购'",
      classify("团购50件帆布袋")["order_type"], "BATCH")
check("批量: '多件'",
      classify("多件皮具卡包")["order_type"], "BATCH")

print("== 兜底与优先级 ==")
r = classify("一个普通的帆布袋")
check("未命中关键词 → 通用类兜底", r["order_type"], "GENERAL")
check("兜底标记 is_fallback", r["is_fallback"], True)
check("兜底 matched_keyword=None", r["matched_keyword"], None)
check("空文本 → 通用类", classify("")["order_type"], "GENERAL")
check("None → 通用类", classify(None)["order_type"], "GENERAL")
# 优先级: 定制 > 现货 > 批量(规则表顺序)
check("'批量定制钥匙扣' → 定制优先", classify("批量定制钥匙扣")["order_type"], "CUSTOM")

print("== 工期计算 ==")
check("定制基准工期 7 天", estimate_duration("CUSTOM"), 7)
check("现货基准工期 2 天", estimate_duration("READY"), 2)
check("通用基准工期 3 天", estimate_duration("GENERAL"), 3)
check("批量 1 件 → 3+1=4 天", estimate_duration("BATCH", 1), 4)
check("批量 5 件 → 3+1=4 天", estimate_duration("BATCH", 5), 4)
check("批量 6 件 → 3+2=5 天", estimate_duration("BATCH", 6), 5)
check("批量 100 件 → 3+20=23 天", estimate_duration("BATCH", 100), 23)
check("数量<=0 时按 1 处理", estimate_duration("BATCH", 0), 4)
check("数量类型转换(字符串)", estimate_duration("BATCH", "50"), 13)

print("== 日期推算 ==")
check("工期4天 从2026-09-01起算 → 09-05",
      estimate_due_date(date(2026, 9, 1), 4).isoformat(), "2026-09-05")
check("classify 返回的日期与工期自洽",
      (date.fromisoformat(classify("现货耳环")["estimated_complete_date"])
       - date.today()).days, 2)

print("== 工期提醒(截止前3天内) ==")
today = date(2026, 9, 6)
def mk(due_iso, status="IN_PRODUCTION"):
    return {"estimated_complete_date": due_iso, "status": status}

check("今天到期 → 提醒", needs_reminder(mk("2026-09-06"), today), True)
check("还剩3天 → 提醒", needs_reminder(mk("2026-09-09"), today), True)
check("还剩4天 → 不提醒", needs_reminder(mk("2026-09-10"), today), False)
check("超期7天 → 仍提醒(未交付)", needs_reminder(mk("2026-08-30"), today), True)
check("超期1天 → 提醒(督促交付)", needs_reminder(mk("2026-09-05"), today), True)
check("已完成 → 不提醒", needs_reminder(mk("2026-09-07", "COMPLETED"), today), False)
check("无截止日期 → 不提醒", needs_reminder({"status": "IN_PRODUCTION"}, today), False)

orders = [mk("2026-09-06"), mk("2026-09-10"), mk("2026-09-08"), mk("2026-09-30")]
check("批量筛选: 2 单需提醒(09-06到期/09-08临期)", len(filter_reminder_orders(orders, today)), 2)

print()
if failures:
    print("总计: %d 项失败 -> %s" % (len(failures), failures))
    sys.exit(1)
print("全部测试通过 ✓ (order_classifier)")