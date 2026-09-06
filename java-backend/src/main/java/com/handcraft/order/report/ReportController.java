package com.handcraft.order.report;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import com.handcraft.order.common.Role;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 经营报表 REST API —— 财务查看者/管理员 (数据权责分离: 财务只读经营数据)
 * 报表口径与 python/analytics.py 保持一致, 可交叉验证。
 */
@RestController
@RequestMapping("/api/reports")
public class ReportController {
    private final JdbcTemplate jdbc;

    public ReportController(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    private void requireViewer() {
        AuthContext.requireRole(Role.FINANCE, Role.ADMIN);
    }

    /** 报表1: 利润趋势(按 月/季), 对应 python analytics.profit_trend */
    @GetMapping("/profit-trend")
    public List<Map<String, Object>> profitTrend(@RequestParam(defaultValue = "month") String group) {
        requireViewer();
        String fmt = "month".equalsIgnoreCase(group)
                ? "DATE_FORMAT(COALESCE(actual_complete_date, created_at), '%Y-%m')"
                : "CONCAT(YEAR(COALESCE(actual_complete_date, created_at)), '-Q', QUARTER(COALESCE(actual_complete_date, created_at)))";
        return jdbc.queryForList(
                "SELECT " + fmt + " AS period, COUNT(*) AS orders, " +
                "       SUM(quantity*unit_price) AS income, " +
                "       SUM(material_cost + labor_cost) AS cost, " +
                "       SUM(quantity*unit_price - material_cost - labor_cost) AS profit " +
                "FROM `orders` WHERE status = 'COMPLETED' OR (status = 'ARCHIVED' AND actual_complete_date IS NOT NULL) " +
                "GROUP BY period ORDER BY period");
    }

    /** 报表2: 客户复购与价值分层, 对应 python analytics.repurchase_analysis */
    @GetMapping("/repurchase")
    public Map<String, Object> repurchase() {
        requireViewer();
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT c.customer_id AS customerId, c.name AS customerName, " +
                "       COUNT(o.order_id) AS orders, SUM(o.quantity*o.unit_price) AS totalSpend " +
                "FROM customer c JOIN `orders` o ON o.customer_id = c.customer_id " +
                "WHERE o.status = 'COMPLETED' OR (o.status = 'ARCHIVED' AND o.actual_complete_date IS NOT NULL) " +
                "GROUP BY c.customer_id, c.name ORDER BY totalSpend DESC");
        int total = rows.size();
        int repeat = 0;
        double income = 0;
        int orderTotal = 0;
        int high = 0, mid = 0, normal = 0;
        double highIncome = 0, midIncome = 0, normalIncome = 0;
        for (Map<String, Object> r : rows) {
            double spend = ((Number) r.get("totalSpend")).doubleValue();
            int n = ((Number) r.get("orders")).intValue();
            if (n >= 2) repeat++;
            income += spend;
            orderTotal += n;
            if (spend >= 8000) { high++; highIncome += spend; }
            else if (spend >= 2000) { mid++; midIncome += spend; }
            else { normal++; normalIncome += spend; }
        }
        return Map.of(
                "totalCustomers", total, "repeatCustomers", repeat,
                "repurchaseRate", total == 0 ? 0 : Math.round(repeat * 10000.0 / total) / 100.0,
                "totalOrders", orderTotal, "totalIncome", Math.round(income * 100) / 100.0,
                "avgOrderValue", orderTotal == 0 ? 0 : Math.round(income / orderTotal * 100) / 100.0,
                "valueTiers", Map.of(
                        "high", Map.of("customers", high, "income", Math.round(highIncome * 100) / 100.0),
                        "medium", Map.of("customers", mid, "income", Math.round(midIncome * 100) / 100.0),
                        "normal", Map.of("customers", normal, "income", Math.round(normalIncome * 100) / 100.0)),
                "customers", rows);
    }

    /** 报表3: 材料消耗分析, 对应 python analytics.material_consumption */
    @GetMapping("/materials")
    public Map<String, Object> materialConsumption() {
        requireViewer();
        List<Map<String, Object>> items = jdbc.queryForList(
                "SELECT m.name AS materialName, mc.name AS materialCategory, " +
                "       SUM(om.quantity_used) AS quantityUsed, SUM(om.quantity_used * om.unit_cost) AS cost " +
                "FROM order_material om JOIN material m ON m.material_id = om.material_id " +
                "LEFT JOIN material_category mc ON mc.material_category_id = m.material_category_id " +
                "GROUP BY m.material_id, m.name, mc.name ORDER BY cost DESC");
        List<Map<String, Object>> list = new ArrayList<>();
        double totalCost = 0;
        for (Map<String, Object> r : items) {
            totalCost += ((Number) r.get("cost")).doubleValue();
            list.add(r);
        }
        return Map.of("items", list, "totalCost", Math.round(totalCost * 100) / 100.0);
    }

    /** 报表4: 收入支出总览(财务首页), 对应 python 演示口径 */
    @GetMapping("/summary")
    public Map<String, Object> summary() {
        requireViewer();
        return jdbc.queryForMap(
                "SELECT COUNT(*) AS totalOrders, " +
                "       COALESCE(SUM(CASE WHEN status = 'COMPLETED' OR (status = 'ARCHIVED' AND actual_complete_date IS NOT NULL) THEN quantity*unit_price END),0) AS income, " +
                "       COALESCE(SUM(CASE WHEN status = 'COMPLETED' OR (status = 'ARCHIVED' AND actual_complete_date IS NOT NULL) THEN material_cost+labor_cost END),0) AS cost, " +
                "       COALESCE(SUM(CASE WHEN status = 'COMPLETED' OR (status = 'ARCHIVED' AND actual_complete_date IS NOT NULL) THEN quantity*unit_price-material_cost-labor_cost END),0) AS profit " +
                "FROM `orders`");
    }
}