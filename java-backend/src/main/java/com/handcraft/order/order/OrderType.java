package com.handcraft.order.order;

/**
 * 订单类型 —— 与 sql/schema.sql orders.order_type 枚举一致。
 * 由 Python 智能分类模块(order_classifier.py)判定后写入。
 */
public enum OrderType {
    CUSTOM("定制类", "工期较长, 需人工确认需求"),
    READY("现货类", "工期较短"),
    BATCH("批量类", "按数量计算工期"),
    GENERAL("通用类", "关键词未命中兜底, 创作者手动调整");

    private final String label;
    private final String note;

    OrderType(String label, String note) {
        this.label = label;
        this.note = note;
    }

    public String getLabel() { return label; }
    public String getNote() { return note; }
}