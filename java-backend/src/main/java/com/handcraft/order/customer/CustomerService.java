package com.handcraft.order.customer;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** 客户管理服务(P1): 创作者维护自己的客户档案(敏感字段脱敏) */
@Service
public class CustomerService {
    private final JdbcTemplate jdbc;

    public CustomerService(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public List<Map<String, Object>> list(String keyword) {
        long me = AuthContext.current().userId();
        List<Object> args = new ArrayList<>();
        String kw = "";
        if (keyword != null && !keyword.isBlank()) {
            kw = "%" + keyword.trim() + "%";
            args.add(kw); args.add(kw);
        }
        String sql = "SELECT customer_id AS customerId, name, " +
                "       CONCAT(LEFT(phone,3),'****',RIGHT(phone,4)) AS phoneMasked, phone, " +
                "       wechat_id AS wechatId, tags, " +
                "       (SELECT COUNT(*) FROM `orders` o WHERE o.customer_id = c.customer_id) AS orderCount, " +
                "       (SELECT COUNT(*) FROM `orders` o WHERE o.customer_id = c.customer_id " +
                "          AND o.status IN ('COMPLETED','ARCHIVED')) AS completedCount, " +
                "       c.created_at AS createdAt " +
                "FROM customer c WHERE c.creator_id = ? " +
                (args.isEmpty() ? "" : "AND (c.name LIKE ? OR c.phone LIKE ?)") +
                " ORDER BY c.customer_id DESC";
        args.add(0, me);
        return jdbc.queryForList(sql, args.toArray());
    }

    public Map<String, Object> detail(long customerId) {
        long me = AuthContext.current().userId();
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT customer_id AS customerId, name, phone, wechat_id AS wechatId, tags, " +
                "       creator_id AS creatorId, created_at AS createdAt " +
                "FROM customer WHERE customer_id = ? AND creator_id = ?", customerId, me);
        if (rows.isEmpty()) throw ApiException.notFound("客户不存在");
        Map<String, Object> c = rows.get(0);
        c.put("orders", jdbc.queryForList(
                "SELECT o.order_id AS orderId, o.order_no AS orderNo, o.product_name AS productName, " +
                "       o.order_type AS orderType, o.status, o.quantity, o.unit_price AS unitPrice, " +
                "       o.quantity * o.unit_price AS income, o.created_at AS createdAt " +
                "FROM `orders` o WHERE o.customer_id = ? ORDER BY o.created_at DESC", customerId));
        return c;
    }

    @Transactional
    public Map<String, Object> create(Map<String, Object> body) {
        long me = AuthContext.current().userId();
        String name = str(body.get("name"));
        if (name.isEmpty()) throw ApiException.badRequest("客户称呼不能为空");
        jdbc.update("INSERT INTO customer (name, phone, wechat_id, tags, creator_id) VALUES (?,?,?,?,?)",
                name, str(body.get("phone")), str(body.get("wechatId")),
                str(body.get("tags")), me);
        return Map.of("customerId", jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class),
                "message", "客户已添加");
    }

    @Transactional
    public Map<String, Object> update(long customerId, Map<String, Object> body) {
        long me = AuthContext.current().userId();
        Integer n = jdbc.queryForObject(
                "SELECT COUNT(*) FROM customer WHERE customer_id = ? AND creator_id = ?",
                Integer.class, customerId, me);
        if (n == null || n == 0) throw ApiException.notFound("客户不存在");
        List<String> sets = new ArrayList<>();
        List<Object> args = new ArrayList<>();
        if (body.containsKey("name")) { sets.add("name = ?"); args.add(str(body.get("name"))); }
        if (body.containsKey("phone")) { sets.add("phone = ?"); args.add(str(body.get("phone"))); }
        if (body.containsKey("wechatId")) { sets.add("wechat_id = ?"); args.add(str(body.get("wechatId"))); }
        if (body.containsKey("tags")) { sets.add("tags = ?"); args.add(str(body.get("tags"))); }
        if (sets.isEmpty()) return Map.of("message", "无更新字段");
        args.add(customerId);
        jdbc.update("UPDATE customer SET " + String.join(", ", sets) + " WHERE customer_id = ?",
                args.toArray());
        return Map.of("message", "客户信息已更新");
    }

    private String str(Object o) { return o == null ? "" : o.toString().trim(); }
}