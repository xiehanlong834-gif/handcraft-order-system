package com.handcraft.order.inventory;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.Role;
import com.handcraft.order.common.AuthContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 材料库存服务(P0): 入库/出库(关联订单)/列表/低库存预警。
 * 出入库写入 stock_movement, 由数据库触发器维护 material.stock_qty,
 * 保证流水与库存永远一致(单点写)。
 */
@Service
public class MaterialService {
    private final JdbcTemplate jdbc;

    public MaterialService(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    /** 材料列表(可含库存预警标记) */
    public List<Map<String, Object>> list(Boolean lowOnly) {
        AuthContext.requireRole(Role.CREATOR);
        String sql = "SELECT m.material_id AS materialId, m.name, m.spec, m.unit, " +
                "       m.stock_qty AS stockQty, m.low_stock_threshold AS lowStockThreshold, " +
                "       m.unit_price AS unitPrice, mc.material_category_id AS materialCategoryId, " +
                "       mc.name AS materialCategory, " +
                "       CASE WHEN m.stock_qty <= m.low_stock_threshold THEN 1 ELSE 0 END AS lowStockFlag " +
                "FROM material m JOIN material_category mc ON mc.material_category_id = m.material_category_id ";
        if (Boolean.TRUE.equals(lowOnly)) {
            sql += "WHERE m.stock_qty <= m.low_stock_threshold ";
        }
        return jdbc.queryForList(sql + "ORDER BY m.material_id");
    }

    /** 新建材料(初始库存直接写入主档) */
    @Transactional
    public Map<String, Object> create(Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        String name = str(body.get("name"));
        if (name.isEmpty()) throw ApiException.badRequest("材料名称不能为空");
        Long catId = body.get("materialCategoryId") == null ? null
                : ((Number) body.get("materialCategoryId")).longValue();
        if (catId == null) throw ApiException.badRequest("必须指定材料品类");
        BigDecimal stock = bd(body.get("stockQty"), BigDecimal.ZERO);
        BigDecimal threshold = bd(body.get("lowStockThreshold"), BigDecimal.ZERO);
        BigDecimal price = bd(body.get("unitPrice"), BigDecimal.ZERO);
        jdbc.update("INSERT INTO material (material_category_id, name, spec, unit, stock_qty, " +
                        "low_stock_threshold, unit_price) VALUES (?,?,?,?,?,?,?)",
                catId, name, str(body.get("spec")), str(body.getOrDefault("unit", "件")),
                stock, threshold, price);
        long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return Map.of("materialId", id, "message", "材料已创建");
    }

    /** 入库 */
    @Transactional
    public Map<String, Object> stockIn(long materialId, BigDecimal quantity, String note) {
        AuthContext.requireRole(Role.CREATOR);
        requireMaterial(materialId);
        if (quantity == null || quantity.compareTo(BigDecimal.ZERO) <= 0) {
            throw ApiException.badRequest("入库数量必须 > 0");
        }
        jdbc.update("INSERT INTO stock_movement (material_id, direction, quantity, operator_id, note) " +
                "VALUES (?, 'IN', ?, ?, ?)", materialId, quantity,
                AuthContext.current().userId(), note);
        return Map.of("message", "入库成功, 库存 +" + quantity);
    }

    /** 出库(可关联订单; 库存不足拒绝) */
    @Transactional
    public Map<String, Object> stockOut(long materialId, BigDecimal quantity, Long orderId, String note) {
        AuthContext.requireRole(Role.CREATOR);
        requireMaterial(materialId);
        if (quantity == null || quantity.compareTo(BigDecimal.ZERO) <= 0) {
            throw ApiException.badRequest("出库数量必须 > 0");
        }
        BigDecimal stock = jdbc.queryForObject(
                "SELECT stock_qty FROM material WHERE material_id = ?", BigDecimal.class, materialId);
        if (stock.compareTo(quantity) < 0) {
            throw ApiException.badRequest("库存不足: 当前 " + stock + ", 需出库 " + quantity);
        }
        jdbc.update("INSERT INTO stock_movement (material_id, direction, quantity, order_id, operator_id, note) " +
                "VALUES (?, 'OUT', ?, ?, ?, ?)", materialId, quantity, orderId,
                AuthContext.current().userId(), note);
        return Map.of("message", "出库成功, 库存 -" + quantity);
    }

    /** 低库存预警列表(视图 v_low_stock) */
    public List<Map<String, Object>> lowStock() {
        AuthContext.requireRole(Role.CREATOR);
        return jdbc.queryForList("SELECT material_id AS materialId, name, spec, unit, " +
                "stock_qty AS stockQty, low_stock_threshold AS lowStockThreshold, unit_price AS unitPrice " +
                "FROM v_low_stock ORDER BY (stock_qty - low_stock_threshold)");
    }

    /** 流水(某材料) */
    public List<Map<String, Object>> movements(long materialId) {
        AuthContext.requireRole(Role.CREATOR);
        requireMaterial(materialId);
        return jdbc.queryForList(
                "SELECT movement_id AS movementId, direction, quantity, order_id AS orderId, " +
                "       note, created_at AS createdAt " +
                "FROM stock_movement WHERE material_id = ? ORDER BY movement_id DESC", materialId);
    }

    /** 更新材料(阈值/单价/规格) */
    @Transactional
    public Map<String, Object> update(long materialId, Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        requireMaterial(materialId);
        List<String> sets = new java.util.ArrayList<>();
        List<Object> args = new java.util.ArrayList<>();
        if (body.containsKey("lowStockThreshold")) {
            sets.add("low_stock_threshold = ?"); args.add(bd(body.get("lowStockThreshold"), BigDecimal.ZERO));
        }
        if (body.containsKey("unitPrice")) {
            sets.add("unit_price = ?"); args.add(bd(body.get("unitPrice"), BigDecimal.ZERO));
        }
        if (body.containsKey("spec")) {
            sets.add("spec = ?"); args.add(str(body.get("spec")));
        }
        if (body.containsKey("name")) {
            sets.add("name = ?"); args.add(str(body.get("name")));
        }
        if (sets.isEmpty()) return Map.of("message", "无更新字段");
        args.add(materialId);
        jdbc.update("UPDATE material SET " + String.join(", ", sets) + " WHERE material_id = ?",
                args.toArray());
        return Map.of("message", "材料信息已更新");
    }

    private void requireMaterial(long id) {
        Integer n = jdbc.queryForObject("SELECT COUNT(*) FROM material WHERE material_id = ?",
                Integer.class, id);
        if (n == null || n == 0) throw ApiException.notFound("材料不存在: " + id);
    }

    private BigDecimal bd(Object o, BigDecimal def) {
        return o == null ? def : new BigDecimal(o.toString());
    }
    private String str(Object o) { return o == null ? "" : o.toString().trim(); }
    private String str(Object o, String def) { return o == null ? def : o.toString().trim(); }
}