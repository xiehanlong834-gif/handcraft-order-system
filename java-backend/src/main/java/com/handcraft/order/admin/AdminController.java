package com.handcraft.order.admin;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import com.handcraft.order.common.Role;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 管理员后台(P0/P1): 用户管理 / 基础数据配置 / 公告(简化) / 经营总览 */
@RestController
@RequestMapping("/api/admin")
public class AdminController {
    private final JdbcTemplate jdbc;
    private final BCryptPasswordEncoder encoder;

    public AdminController(JdbcTemplate jdbc, BCryptPasswordEncoder encoder) {
        this.jdbc = jdbc;
        this.encoder = encoder;
    }

    // ---------------- 用户管理 ----------------
    @GetMapping("/users")
    public List<Map<String, Object>> users(@RequestParam(required = false) String roleCode) {
        AuthContext.requireRole(Role.ADMIN);
        String sql = "SELECT u.user_id AS userId, u.username, u.real_name AS realName, " +
                "       CONCAT(LEFT(u.phone,3),'****',RIGHT(u.phone,4)) AS phoneMasked, u.phone, " +
                "       r.role_code AS roleCode, r.role_name AS roleName, u.status, u.created_at AS createdAt " +
                "FROM `user` u JOIN role r ON r.role_id = u.role_id ";
        if (roleCode != null && !roleCode.isBlank()) {
            sql += "WHERE r.role_code = '" + roleCode.trim().replace("'", "''") + "' ";
        }
        return jdbc.queryForList(sql + "ORDER BY u.user_id");
    }

    @PostMapping("/users")
    @Transactional
    public Map<String, Object> createUser(@RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.ADMIN);
        String username = str(body.get("username"));
        String password = str(body.get("password"));
        String roleCode = str(body.get("roleCode"));
        if (username.isEmpty() || password.isEmpty()) throw ApiException.badRequest("用户名/密码必填");
        if (password.length() < 6) throw ApiException.badRequest("密码长度至少 6 位");
        Long roleId = roleIdByCode(roleCode);
        Integer dup = jdbc.queryForObject("SELECT COUNT(*) FROM `user` WHERE username = ?",
                Integer.class, username);
        if (dup != null && dup > 0) throw ApiException.badRequest("用户名已存在");
        jdbc.update("INSERT INTO `user` (username, password_hash, real_name, phone, role_id, status) " +
                "VALUES (?,?,?,?,?,1)", username, encoder.encode(password),
                str(body.get("realName")), str(body.get("phone")), roleId);
        long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return Map.of("userId", id, "message", "用户已创建, 默认启用");
    }

    @PutMapping("/users/{id}")
    @Transactional
    public Map<String, Object> updateUser(@PathVariable long id, @RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.ADMIN);
        requireUser(id);
        StringBuilder sets = new StringBuilder();
        java.util.List<Object> args = new java.util.ArrayList<>();
        if (body.containsKey("roleCode")) { sets.append("role_id = ?,"); args.add(roleIdByCode(str(body.get("roleCode")))); }
        if (body.containsKey("realName")) { sets.append("real_name = ?,"); args.add(str(body.get("realName"))); }
        if (body.containsKey("phone")) { sets.append("phone = ?,"); args.add(str(body.get("phone"))); }
        if (body.containsKey("status")) { sets.append("status = ?,"); args.add(((Number) body.get("status")).intValue()); }
        if (body.containsKey("password") && !str(body.get("password")).isEmpty()) {
            sets.append("password_hash = ?,"); args.add(encoder.encode(str(body.get("password"))));
        }
        if (sets.length() == 0) return Map.of("message", "无更新字段");
        args.add(id);
        jdbc.update("UPDATE `user` SET " + sets.substring(0, sets.length() - 1) + " WHERE user_id = ?",
                args.toArray());
        return Map.of("message", "用户已更新");
    }

    // ---------------- 基础数据: 产品分类/材料品类 ----------------
    @GetMapping("/product-categories")
    public List<Map<String, Object>> productCategories() {
        AuthContext.requireRole(Role.ADMIN, Role.CREATOR);
        return jdbc.queryForList("SELECT product_category_id AS id, name, sort_no AS sortNo " +
                "FROM product_category ORDER BY sort_no");
    }

    @PostMapping("/product-categories")
    public Map<String, Object> createProductCategory(@RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.ADMIN);
        return createCategory("product_category", body, "name");
    }

    @GetMapping("/material-categories")
    public List<Map<String, Object>> materialCategories() {
        AuthContext.requireRole(Role.ADMIN, Role.CREATOR);
        return jdbc.queryForList("SELECT material_category_id AS id, name FROM material_category ORDER BY material_category_id");
    }

    @PostMapping("/material-categories")
    public Map<String, Object> createMaterialCategory(@RequestBody Map<String, Object> body) {
        // 材料品类允许创作者自建(单人工作室无专职管理员时保证库存可用)
        AuthContext.requireRole(Role.ADMIN, Role.CREATOR);
        return createCategory("material_category", body, "material_category_id");
    }

    private Map<String, Object> createCategory(String table, Map<String, Object> body, String key) {
        String name = str(body.get("name"));
        if (name.isEmpty()) throw ApiException.badRequest("分类名称不能为空");
        try {
            jdbc.update("INSERT INTO " + table + " (name) VALUES (?)", name);
        } catch (Exception e) {
            throw ApiException.badRequest("分类已存在或写入失败: " + e.getMessage());
        }
        return Map.of("message", "分类已创建");
    }

    // ---------------- 公告(简化版, P2) ----------------
    @GetMapping("/announcements")
    public List<Map<String, Object>> announcements() {
        // 全员可看已发布公告(登录即可)
        return jdbc.queryForList(
                "SELECT a.announcement_id AS id, a.title, a.content, u.real_name AS publisher, " +
                "       a.status, a.created_at AS createdAt " +
                "FROM announcement a JOIN `user` u ON u.user_id = a.publisher_id " +
                "WHERE a.status = 1 ORDER BY a.announcement_id DESC");
    }

    @PostMapping("/announcements")
    public Map<String, Object> createAnnouncement(@RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.ADMIN);
        String title = str(body.get("title"));
        if (title.isEmpty()) throw ApiException.badRequest("公告标题不能为空");
        jdbc.update("INSERT INTO announcement (title, content, publisher_id, status) VALUES (?,?,?,1)",
                title, str(body.get("content")), AuthContext.current().userId());
        return Map.of("announcementId", jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class),
                "message", "公告已发布");
    }

    // ---------------- 经营总览(管理员) ----------------
    @GetMapping("/overview")
    public Map<String, Object> overview() {
        AuthContext.requireRole(Role.ADMIN, Role.FINANCE);
        Integer totalOrders = jdbc.queryForObject("SELECT COUNT(*) FROM `orders`", Integer.class);
        Integer inProgress = jdbc.queryForObject(
                "SELECT COUNT(*) FROM `orders` WHERE status IN ('PENDING_CONFIRM','IN_PRODUCTION','PENDING_SHIPMENT')", Integer.class);
        Integer completed = jdbc.queryForObject(
                "SELECT COUNT(*) FROM `orders` WHERE status IN ('COMPLETED','ARCHIVED')", Integer.class);
        Integer lowStock = jdbc.queryForObject("SELECT COUNT(*) FROM v_low_stock", Integer.class);
        Integer dueSoon = jdbc.queryForObject("SELECT COUNT(*) FROM v_due_reminder", Integer.class);
        Map<String, Object> profit = jdbc.queryForMap(
                "SELECT COALESCE(SUM(quantity*unit_price),0) AS income, " +
                "       COALESCE(SUM(material_cost+labor_cost),0) AS cost, " +
                "       COALESCE(SUM(quantity*unit_price-material_cost-labor_cost),0) AS profit " +
                "FROM `orders` WHERE status = 'COMPLETED' OR (status = 'ARCHIVED' AND actual_complete_date IS NOT NULL)");
        return Map.of(
                "totalOrders", totalOrders, "inProgressOrders", inProgress, "completedOrders", completed,
                "lowStockMaterials", lowStock, "dueSoonOrders", dueSoon,
                "totalIncome", profit.get("income"), "totalCost", profit.get("cost"),
                "totalProfit", profit.get("profit"));
    }

    private Long roleIdByCode(String roleCode) {
        try {
            Role r = Role.fromCode(roleCode == null ? "" : roleCode.trim());
            return jdbc.queryForObject("SELECT role_id FROM role WHERE role_code = ?", Long.class, r.getCode());
        } catch (Exception e) {
            throw ApiException.badRequest("非法角色编码: " + roleCode);
        }
    }

    private void requireUser(long id) {
        Integer n = jdbc.queryForObject("SELECT COUNT(*) FROM `user` WHERE user_id = ?", Integer.class, id);
        if (n == null || n == 0) throw ApiException.notFound("用户不存在");
    }

    private String str(Object o) { return o == null ? "" : o.toString().trim(); }
}