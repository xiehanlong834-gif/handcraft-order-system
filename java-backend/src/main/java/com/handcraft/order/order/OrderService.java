package com.handcraft.order.order;

import com.fasterxml.jackson.databind.JsonNode;
import com.handcraft.order.classifier.OrderClassifierClient;
import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 订单核心服务(P0): 建单(自动智能分类+工期) / 状态机流转 / 成本核算 / 客户定制提交。
 * 数据权限: 创作者只操作自己的订单; 客户只看自己的订单。
 */
@Service
public class OrderService {
    private final JdbcTemplate jdbc;
    private final OrderClassifierClient classifier;

    public OrderService(JdbcTemplate jdbc, OrderClassifierClient classifier) {
        this.jdbc = jdbc;
        this.classifier = classifier;
    }

    // ==================== 查询 ====================

    /** 创作者: 订单列表(可按状态/关键词筛选), 客户: 只看本人 */
    public List<Map<String, Object>> list(String status, String keyword) {
        AuthContext.CurrentUser me = AuthContext.current();
        List<String> cond = new ArrayList<>();
        List<Object> args = new ArrayList<>();

        if ("creator".equals(me.roleCode())) {
            cond.add("o.creator_id = ?");
            args.add(me.userId());
        } else if ("customer".equals(me.roleCode())) {
            cond.add("o.customer_id = (SELECT customer_id FROM `user` WHERE user_id = ?)");
            args.add(me.userId());
        } else {
            throw ApiException.forbidden("订单管理仅限创作者/客户角色");
        }
        if (status != null && !status.isBlank()) {
            cond.add("o.status = ?");
            args.add(status.trim());
        }
        if (keyword != null && !keyword.isBlank()) {
            cond.add("(o.product_name LIKE ? OR c.name LIKE ? OR o.order_no LIKE ?)");
            String kw = "%" + keyword.trim() + "%";
            args.add(kw); args.add(kw); args.add(kw);
        }
        String sql = "SELECT o.order_id AS orderId, o.order_no AS orderNo, o.customer_id AS customerId, " +
                "       c.name AS customerName, o.product_name AS productName, o.requirement, " +
                "       o.order_type AS orderType, o.quantity, o.unit_price AS unitPrice, o.status, " +
                "       o.material_cost AS materialCost, o.labor_cost AS laborCost, " +
                "       o.quantity * o.unit_price AS income, " +
                "       o.quantity * o.unit_price - o.material_cost - o.labor_cost AS profit, " +
                "       o.estimate_days AS estimateDays, o.estimated_complete_date AS estimatedCompleteDate, " +
                "       o.actual_complete_date AS actualCompleteDate, o.source, o.remark, o.created_at AS createdAt " +
                "FROM `orders` o JOIN customer c ON c.customer_id = o.customer_id " +
                (cond.isEmpty() ? "" : "WHERE " + String.join(" AND ", cond)) +
                " ORDER BY o.created_at DESC LIMIT 500";
        return jdbc.queryForList(sql, args.toArray());
    }

    public Map<String, Object> detail(long orderId) {
        AuthContext.CurrentUser me = AuthContext.current();
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT o.order_id AS orderId, o.order_no AS orderNo, o.customer_id AS customerId, " +
                "       o.creator_id AS creatorOwner, c.name AS customerName, c.phone AS customerPhone, " +
                "       o.product_name AS productName, o.requirement, o.order_type AS orderType, " +
                "       o.quantity, o.unit_price AS unitPrice, o.status, " +
                "       o.material_cost AS materialCost, o.labor_cost AS laborCost, " +
                "       o.quantity * o.unit_price AS income, " +
                "       o.quantity * o.unit_price - o.material_cost - o.labor_cost AS profit, " +
                "       o.estimate_days AS estimateDays, o.estimated_complete_date AS estimatedCompleteDate, " +
                "       o.actual_complete_date AS actualCompleteDate, o.source, o.remark, o.created_at AS createdAt " +
                "FROM `orders` o JOIN customer c ON c.customer_id = o.customer_id WHERE o.order_id = ?", orderId);
        if (rows.isEmpty()) throw ApiException.notFound("订单不存在: " + orderId);
        Map<String, Object> order = rows.get(0);
        checkOrderVisible(me, orderId, ((Number) order.get("customerId")).longValue(), order);
        // 状态流转日志
        order.put("statusLogs", jdbc.queryForList(
                "SELECT log_id AS logId, from_status AS fromStatus, to_status AS toStatus, " +
                "       u.real_name AS operator, sl.note, sl.created_at AS createdAt " +
                "FROM order_status_log sl LEFT JOIN `user` u ON u.user_id = sl.operator_id " +
                "WHERE sl.order_id = ? ORDER BY sl.log_id", orderId));
        // 材料耗用明细(成本构成)
        order.put("materials", jdbc.queryForList(
                "SELECT om.order_material_id AS orderMaterialId, m.name AS materialName, " +
                "       om.quantity_used AS quantityUsed, om.unit_cost AS unitCost, " +
                "       om.quantity_used * om.unit_cost AS subtotal " +
                "FROM order_material om JOIN material m ON m.material_id = om.material_id " +
                "WHERE om.order_id = ?", orderId));
        return order;
    }

    /** 数据可见性: 创作者看自己的单; 客户看自己的单 */
    private void checkOrderVisible(AuthContext.CurrentUser me, long orderId,
                                   long customerId, Map<String, Object> order) {
        boolean ok;
        if ("creator".equals(me.roleCode())) {
            ok = ((Number) order.getOrDefault("creatorOwner", 0)).longValue() == me.userId();
        } else if ("customer".equals(me.roleCode())) {
            Number mine = jdbc.queryForObject(
                    "SELECT customer_id FROM `user` WHERE user_id = ?", Number.class, me.userId());
            ok = mine != null && mine.longValue() == customerId;
        } else {
            ok = false;
        }
        if (!ok) throw ApiException.forbidden("无权访问该订单");
    }

    // ==================== 创建 ====================

    /** 创作者手动建单: 自动调 Python 智能分类 → 类型+工期+预估完成日期 */
    @Transactional
    public Map<String, Object> createByCreator(Map<String, Object> body) {
        AuthContext.CurrentUser me = AuthContext.current();
        long customerId = ((Number) body.get("customerId")).longValue();
        verifyCustomerOwned(customerId, me.userId());
        return createOrder(me.userId(), customerId, body, "MANUAL");
    }

    /** 客户提交定制需求(source=CUSTOMER, 归属其创作者) */
    @Transactional
    public Map<String, Object> createByCustomer(Map<String, Object> body) {
        AuthContext.CurrentUser me = AuthContext.current();
        Number customerIdNum = jdbc.queryForObject(
                "SELECT customer_id FROM `user` WHERE user_id = ?", Number.class, me.userId());
        if (customerIdNum == null) throw ApiException.badRequest("当前客户账号未关联客户档案");
        long customerId = customerIdNum.longValue();
        Map<String, Object> row = jdbc.queryForMap(
                "SELECT creator_id AS creatorId FROM customer WHERE customer_id = ?", customerId);
        return createOrder(((Number) row.get("creatorId")).longValue(), customerId, body, "CUSTOMER");
    }

    private Map<String, Object> createOrder(long creatorId, long customerId,
                                            Map<String, Object> body, String source) {
        String productName = str(body.get("productName"));
        String requirement = str(body.get("requirement"));
        int quantity = body.get("quantity") == null ? 1 : ((Number) body.get("quantity")).intValue();
        BigDecimal unitPrice = body.get("unitPrice") == null ? BigDecimal.ZERO
                : new BigDecimal(body.get("unitPrice").toString());
        if (productName.isEmpty()) throw ApiException.badRequest("产品名称不能为空");
        if (quantity < 1) throw ApiException.badRequest("数量必须 >= 1");
        if (unitPrice.compareTo(BigDecimal.ZERO) < 0) throw ApiException.badRequest("单价不能为负");

        // 智能分类(创新点一): 关键词规则识别类型 + 预估工期 + 预估完成日期
        JsonNode clz = classifier.classify(productName + " " + requirement, quantity);
        String orderType = clz.get("order_type").asText("GENERAL");
        int days = clz.get("duration_days").asInt(3);
        String dueDate = clz.get("estimated_complete_date").asText(LocalDate.now().plusDays(days).toString());
        String remark = str(body.get("remark"));
        if (!"MANUAL".equals(source) && requirement.isEmpty()) {
            throw ApiException.badRequest("定制需求描述不能为空");
        }
        String note = null;
        if ("CUSTOMER".equals(source)) note = "客户在线提交定制需求, 待创作者确认";

        jdbc.update("INSERT INTO `orders` (order_no, customer_id, creator_id, product_category_id, " +
                        "product_name, requirement, order_type, quantity, unit_price, status, " +
                        "estimate_days, estimated_complete_date, source, remark) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                nextOrderNo(), customerId, creatorId,
                body.get("productCategoryId") == null ? null : ((Number) body.get("productCategoryId")).longValue(),
                productName, requirement, orderType, quantity, unitPrice,
                "PENDING_CONFIRM", days, dueDate, source, remark);
        Long orderId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        jdbc.update("INSERT INTO order_status_log (order_id, from_status, to_status, operator_id, note) " +
                "VALUES (?, NULL, 'PENDING_CONFIRM', ?, ?)", orderId, creatorId,
                "MANUAL".equals(source) ? "创作者创建订单" : "客户提交定制需求");

        Map<String, Object> resp = new HashMap<>();
        resp.put("orderId", orderId);
        resp.put("message", "订单创建成功");
        resp.put("classify", Map.of(
                "orderType", orderType, "orderTypeLabel", clz.path("order_type_label").asText(),
                "matchedKeyword", clz.path("matched_keyword").asText(""),
                "isFallback", clz.path("is_fallback").asBoolean(),
                "estimateDays", days, "estimatedCompleteDate", dueDate));
        if (clz.path("is_fallback").asBoolean()) {
            resp.put("warn", "未命中分类规则, 已归为通用类, 请创作者手动调整类型");
        }
        return resp;
    }

    // ==================== 状态流转 ====================

    /** 状态机流转(校验合法性), 记录审计日志; 完成时写入实际完成日期 */
    @Transactional
    public Map<String, Object> changeStatus(long orderId, String toStatusStr, String note) {
        AuthContext.CurrentUser me = AuthContext.current();
        OrderStatus toStatus;
        try {
            toStatus = OrderStatus.valueOf(toStatusStr);
        } catch (Exception e) {
            throw ApiException.badRequest("非法目标状态: " + toStatusStr);
        }
        Map<String, Object> order = fetchOwnedOrder(orderId, me.userId());
        OrderStatus from = OrderStatus.valueOf((String) order.get("status"));
        if (!from.canTransitionTo(toStatus)) {
            throw ApiException.badRequest("非法状态流转: " + from + " → " + toStatus
                    + " (合法规则见 OrderStatus)");
        }
        String completedDateSql = toStatus == OrderStatus.COMPLETED ? ", actual_complete_date = CURDATE()" : "";
        jdbc.update("UPDATE `orders` SET status = ?" + completedDateSql + " WHERE order_id = ?",
                toStatus.name(), orderId);
        jdbc.update("INSERT INTO order_status_log (order_id, from_status, to_status, operator_id, note) " +
                        "VALUES (?,?,?,?,?)", orderId, from.name(), toStatus.name(), me.userId(),
                (note == null || note.isBlank()) ? null : note.trim());
        return Map.of("orderId", orderId, "fromStatus", from.name(), "toStatus", toStatus.name(),
                "message", "状态已更新为: " + toStatus.getLabel());
    }

    /** 归档(已完成/已取消 → 已归档), 终态 */
    @Transactional
    public Map<String, Object> archive(long orderId) {
        AuthContext.CurrentUser me = AuthContext.current();
        Map<String, Object> order = fetchOwnedOrder(orderId, me.userId());
        OrderStatus from = OrderStatus.valueOf((String) order.get("status"));
        OrderStatus to = OrderStatus.ARCHIVED;
        if (!from.canTransitionTo(to)) {
            throw ApiException.badRequest("仅已完成/已取消的订单可归档, 当前: " + from.getLabel());
        }
        jdbc.update("UPDATE `orders` SET status = ? WHERE order_id = ?", to.name(), orderId);
        jdbc.update("INSERT INTO order_status_log (order_id, from_status, to_status, operator_id, note) " +
                "VALUES (?,?,?,?,?)", orderId, from.name(), to.name(), me.userId(), "归档");
        return Map.of("orderId", orderId, "status", to.name(), "message", "订单已归档");
    }

    /** 取消订单(软删除, 保留审计) */
    @Transactional
    public Map<String, Object> cancel(long orderId) {
        AuthContext.CurrentUser me = AuthContext.current();
        Map<String, Object> order = fetchOwnedOrder(orderId, me.userId());
        OrderStatus from = OrderStatus.valueOf((String) order.get("status"));
        OrderStatus to = OrderStatus.CANCELLED;
        if (!from.canTransitionTo(to)) {
            throw ApiException.badRequest("当前状态不可取消: " + from.getLabel());
        }
        jdbc.update("UPDATE `orders` SET status = ? WHERE order_id = ?", to.name(), orderId);
        jdbc.update("INSERT INTO order_status_log (order_id, from_status, to_status, operator_id, note) " +
                "VALUES (?,?,?,?,?)", orderId, from.name(), to.name(), me.userId(), "创作者取消");
        return Map.of("orderId", orderId, "status", to.name(), "message", "订单已取消");
    }

    private Map<String, Object> fetchOwnedOrder(long orderId, long creatorId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT o.* FROM `orders` o WHERE o.order_id = ? AND o.creator_id = ?",
                orderId, creatorId);
        if (rows.isEmpty()) throw ApiException.notFound("订单不存在或不属于当前创作者");
        return rows.get(0);
    }

    // ==================== 成本核算 ====================

    /** 登记订单耗用材料: 扣库存 + 记录耗用明细(单价快照) + 自动累加材料成本 */
    @Transactional
    public Map<String, Object> addMaterial(long orderId, long materialId, BigDecimal quantityUsed) {
        AuthContext.CurrentUser me = AuthContext.current();
        if (!"creator".equals(me.roleCode())) throw ApiException.forbidden("仅创作者可录入成本");
        Map<String, Object> order = fetchOwnedOrder(orderId, me.userId());
        String status = (String) order.get("status");
        if (!("PENDING_CONFIRM".equals(status) || "IN_PRODUCTION".equals(status))) {
            throw ApiException.badRequest("仅待确认/制作中的订单可登记耗料, 当前: " + status);
        }
        List<Map<String, Object>> mats = jdbc.queryForList(
                "SELECT material_id AS materialId, stock_qty AS stockQty, unit_price AS unitPrice " +
                "FROM material WHERE material_id = ?", materialId);
        if (mats.isEmpty()) throw ApiException.notFound("材料不存在: " + materialId);
        BigDecimal stock = (BigDecimal) mats.get(0).get("stockQty");
        BigDecimal price = (BigDecimal) mats.get(0).get("unitPrice");
        if (stock.compareTo(quantityUsed) < 0) {
            throw ApiException.badRequest("库存不足: 当前库存 " + stock + ", 需出库 " + quantityUsed);
        }
        jdbc.update("INSERT INTO order_material (order_id, material_id, quantity_used, unit_cost) " +
                "VALUES (?,?,?,?)", orderId, materialId, quantityUsed, price);
        // 出库流水(关联订单) → 触发器自动扣减 material.stock_qty
        jdbc.update("INSERT INTO stock_movement (material_id, direction, quantity, order_id, operator_id, note) " +
                "VALUES (?, 'OUT', ?, ?, ?, '订单耗料')", materialId, quantityUsed, orderId, me.userId());
        refreshMaterialCost(orderId);
        return Map.of("message", "耗料登记成功, 库存已扣减, 材料成本已刷新");
    }

    /** 录入工时成本 */
    @Transactional
    public Map<String, Object> setLaborCost(long orderId, BigDecimal laborCost) {
        AuthContext.CurrentUser me = AuthContext.current();
        if (!"creator".equals(me.roleCode())) throw ApiException.forbidden("仅创作者可录入成本");
        Map<String, Object> order = fetchOwnedOrder(orderId, me.userId());
        if (laborCost.compareTo(BigDecimal.ZERO) < 0) throw ApiException.badRequest("工时成本不能为负");
        jdbc.update("UPDATE `orders` SET labor_cost = ? WHERE order_id = ?", laborCost, orderId);
        return Map.of("message", "工时成本已保存", "laborCost", laborCost);
    }

    /** 重算并回写 orders.material_cost = Σ(耗用量 × 单价快照) */
    private void refreshMaterialCost(long orderId) {
        BigDecimal cost = jdbc.queryForObject(
                "SELECT COALESCE(SUM(quantity_used * unit_cost), 0) FROM order_material WHERE order_id = ?",
                BigDecimal.class, orderId);
        jdbc.update("UPDATE `orders` SET material_cost = ? WHERE order_id = ?",
                cost.setScale(2, RoundingMode.HALF_UP), orderId);
    }

    // ==================== 排期/提醒 ====================

    /** 截止前 3 天(含超期)未完成订单 —— 对应视图 v_due_reminder */
    public List<Map<String, Object>> dueReminders() {
        AuthContext.CurrentUser me = AuthContext.current();
        if (!"creator".equals(me.roleCode())) throw ApiException.forbidden("仅创作者可查看工期提醒");
        return jdbc.queryForList(
                "SELECT order_id AS orderId, order_no AS orderNo, customer_name AS customerName, " +
                "       product_name AS productName, order_type AS orderType, " +
                "       estimated_complete_date AS estimatedCompleteDate, status " +
                "FROM v_due_reminder WHERE creator_id = ? ORDER BY estimated_complete_date",
                me.userId());
    }

    /** 排期日历数据: 指定月份的预估工期订单 */
    public List<Map<String, Object>> schedule(String month) {
        AuthContext.CurrentUser me = AuthContext.current();
        if (!"creator".equals(me.roleCode())) throw ApiException.forbidden("仅创作者可查看排期");
        String m = (month == null || month.isBlank()) ? LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM")) : month;
        return jdbc.queryForList(
                "SELECT o.order_id AS orderId, o.order_no AS orderNo, c.name AS customerName, " +
                "       o.product_name AS productName, o.order_type AS orderType, o.status, " +
                "       o.estimate_days AS estimateDays, o.estimated_complete_date AS estimatedCompleteDate " +
                "FROM `orders` o JOIN customer c ON c.customer_id = o.customer_id " +
                "WHERE o.creator_id = ? AND DATE_FORMAT(o.estimated_complete_date, '%Y-%m') = ? " +
                "AND o.status NOT IN ('COMPLETED','CANCELLED','ARCHIVED') ORDER BY o.estimated_complete_date",
                me.userId(), m);
    }

    // ==================== 私有工具 ====================

    private void verifyCustomerOwned(long customerId, long creatorId) {
        Integer n = jdbc.queryForObject(
                "SELECT COUNT(*) FROM customer WHERE customer_id = ? AND creator_id = ?",
                Integer.class, customerId, creatorId);
        if (n == null || n == 0) throw ApiException.badRequest("客户不存在或不属于当前创作者");
    }

    private String nextOrderNo() {
        return "HC" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%03d", (int) (Math.random() * 1000));
    }

    private String str(Object o) { return o == null ? "" : o.toString().trim(); }
}