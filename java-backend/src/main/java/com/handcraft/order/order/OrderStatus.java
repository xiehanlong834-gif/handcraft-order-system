package com.handcraft.order.order;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

/**
 * 订单状态机 —— 与 sql/schema.sql orders.status 一致。
 * 流转规则集中定义在此, 防止任何接口直接"乱改状态"。
 *
 * 合法流转:
 *   待确认 → 制作中 / 已取消
 *   制作中 → 待发货 / 已取消
 *   待发货 → 已完成
 *   已完成 → 已归档
 *   已取消 → 已归档
 */
public enum OrderStatus {
    PENDING_CONFIRM("待确认"),
    IN_PRODUCTION("制作中"),
    PENDING_SHIPMENT("待发货"),
    COMPLETED("已完成"),
    CANCELLED("已取消"),
    ARCHIVED("已归档");

    private static final Map<OrderStatus, Set<OrderStatus>> TRANSITIONS = new EnumMap<>(OrderStatus.class);
    static {
        TRANSITIONS.put(PENDING_CONFIRM, EnumSet.of(IN_PRODUCTION, CANCELLED));
        TRANSITIONS.put(IN_PRODUCTION, EnumSet.of(PENDING_SHIPMENT, CANCELLED));
        TRANSITIONS.put(PENDING_SHIPMENT, EnumSet.of(COMPLETED));
        TRANSITIONS.put(COMPLETED, EnumSet.of(ARCHIVED));
        TRANSITIONS.put(CANCELLED, EnumSet.of(ARCHIVED));
        TRANSITIONS.put(ARCHIVED, EnumSet.noneOf(OrderStatus.class)); // 终态
    }

    private final String label;
    OrderStatus(String label) { this.label = label; }
    public String getLabel() { return label; }

    /** 是否允许从当前状态流转到 next */
    public boolean canTransitionTo(OrderStatus next) {
        return TRANSITIONS.getOrDefault(this, EnumSet.noneOf(OrderStatus.class)).contains(next);
    }
}