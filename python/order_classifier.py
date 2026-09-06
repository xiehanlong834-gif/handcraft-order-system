# -*- coding: utf-8 -*-
"""
智能订单分类与工期计算模块（创新点一）
======================================
定位: 独立手作创作者订单管理系统的"轻量化智能"模块。
不依赖任何第三方库 / 大模型 —— 关键词-规则匹配, 由 Java 后端以本地进程方式调用。

订单类型(与 sql/schema.sql 的 orders.order_type 枚举一致):
    CUSTOM  定制类 —— 命中词: 定制/专属/个性化/按需      (工期较长)
    READY   现货类 —— 命中词: 现货/现款/成品            (工期较短)
    BATCH   批量类 —— 命中词: 批量/团购/多件            (按数量计算工期)
    GENERAL 通用类 —— 未命中任何关键词的兜底, 由创作者手动调整

匹配优先级(显式声明, 先命中先得):
    CUSTOM > READY > BATCH
    例: "批量定制钥匙扣" 同时含"批量"与"定制", 判定为 CUSTOM(定制),
        因为定制需求最特殊、工期最不可控, 需要创作者人工介入确认。

作者: 课程项目组 | 日期: 2026-09
"""

from datetime import date, datetime, timedelta

# ---------------------------------------------------------------- 常量配置
ORDER_TYPES = ("CUSTOM", "READY", "BATCH", "GENERAL")

ORDER_TYPE_LABEL = {
    "CUSTOM": "定制类",
    "READY": "现货类",
    "BATCH": "批量类",
    "GENERAL": "通用类",
}

# 规则表: (订单类型, 关键词列表), 顺序即匹配优先级
KEYWORD_RULES = (
    ("CUSTOM", ("定制", "专属", "个性化", "按需")),
    ("READY", ("现货", "现款", "成品")),
    ("BATCH", ("批量", "团购", "多件")),
)

# 基准工期(天): 定制长 / 现货短 / 通用类兜底
BASE_DURATION_DAYS = {
    "CUSTOM": 7,
    "READY": 2,
    "GENERAL": 3,
}

# 批量类: 基础 3 天, 每满 N 件加 1 天
BATCH_BASE_DAYS = 3
BATCH_UNITS_PER_EXTRA_DAY = 5

# 提醒窗口: 截止日前 N 天提醒
REMINDER_DAYS_BEFORE = 3


# ---------------------------------------------------------------- 核心函数
def classify(description, quantity=1):
    """对订单描述做智能分类, 返回结构化结果。

    :param description: 产品名称/描述/定制要求文本
    :param quantity:    订单数量(批量类工期计算用)
    :return: dict {
        order_type: 订单类型编码, matched_keyword: 命中的关键词(未命中为 None),
        is_fallback: 是否兜底为通用类, duration_days: 预估工期(天),
        estimated_complete_date: 按今天推算的预估完成日期(ISO 字符串)
    }
    """
    text = (description or "").strip()
    order_type, matched = "GENERAL", None
    for typ, keywords in KEYWORD_RULES:
        for kw in keywords:
            if kw in text:
                order_type, matched = typ, kw
                break
        if order_type != "GENERAL":
            break

    duration = estimate_duration(order_type, quantity)
    due = date.today() + timedelta(days=duration)
    return {
        "order_type": order_type,
        "order_type_label": ORDER_TYPE_LABEL[order_type],
        "matched_keyword": matched,
        "is_fallback": order_type == "GENERAL",
        "quantity": quantity,
        "duration_days": duration,
        "estimated_complete_date": due.isoformat(),
    }


def estimate_duration(order_type, quantity=1):
    """按订单类型与数量计算预估工期(天)。

    CUSTOM/READY/GENERAL: 查基准工期表
    BATCH: 基础 3 天 + ceil(数量 / 5) 天
    """
    qty = max(1, int(quantity or 1))
    if order_type == "BATCH":
        extra = (qty + BATCH_UNITS_PER_EXTRA_DAY - 1) // BATCH_UNITS_PER_EXTRA_DAY
        return BATCH_BASE_DAYS + extra
    return BASE_DURATION_DAYS.get(order_type, BASE_DURATION_DAYS["GENERAL"])


def estimate_due_date(start_date, duration_days):
    """由起始日期与工期推算预估完成日期。"""
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    return start_date + timedelta(days=duration_days)


def needs_reminder(order, today=None):
    """工期提醒规则: 距预估完成日期 <= 3 天(含已超期)且订单未完结 → 需要提醒。

    :param order: dict, 至少含 estimated_complete_date(ISO) 与 status
    :param today: date, 默认今天(便于测试注入)
    """
    today = today or date.today()
    due = order.get("estimated_complete_date")
    if not due:
        return False
    if isinstance(due, str):
        due = date.fromisoformat(due)
    if order.get("status") in ("COMPLETED", "CANCELLED", "ARCHIVED"):
        return False
    days_left = (due - today).days
    # 提醒窗口 = 截止日 <= 今天+3天；已超期(days_left<0)未交付同样需要提醒
    return days_left <= REMINDER_DAYS_BEFORE


def filter_reminder_orders(orders, today=None):
    """批量筛选需要发送工期提醒的订单(截止前 3 天内)。"""
    return [o for o in orders if needs_reminder(o, today)]


def build_order_no(prefix="HC", when=None):
    """订单号生成规则: HC + yyyyMMdd + 4位序号(由调用方保证序号递增)。
    例: HC202609060001"""
    when = when or datetime.now()
    return "{}{}{:04d}".format(prefix, when.strftime("%Y%m%d"), 0)


if __name__ == "__main__":
    # 命令行演示: python order_classifier.py "定制刻字银手镯" 2
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "按需定制的皮具钱包"
    qty = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    import json
    print(json.dumps(classify(text, qty), ensure_ascii=False, indent=2))