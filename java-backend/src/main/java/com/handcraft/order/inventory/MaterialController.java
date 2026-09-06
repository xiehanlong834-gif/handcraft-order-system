package com.handcraft.order.inventory;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import com.handcraft.order.common.Role;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/** 材料库存 REST API (P0) —— 仅创作者 */
@RestController
@RequestMapping("/api/materials")
public class MaterialController {
    private final MaterialService service;

    public MaterialController(MaterialService service) { this.service = service; }

    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(required = false) Boolean lowOnly) {
        AuthContext.requireRole(Role.CREATOR);
        return service.list(lowOnly);
    }

    @GetMapping("/low-stock")
    public List<Map<String, Object>> lowStock() {
        AuthContext.requireRole(Role.CREATOR);
        return service.lowStock();
    }

    @PostMapping
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        return service.create(body);
    }

    @PutMapping("/{id}")
    public Map<String, Object> update(@PathVariable long id, @RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        return service.update(id, body);
    }

    @PostMapping("/{id}/in")
    public Map<String, Object> stockIn(@PathVariable long id, @RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        return service.stockIn(id, num(body.get("quantity")), note(body));
    }

    @PostMapping("/{id}/out")
    public Map<String, Object> stockOut(@PathVariable long id, @RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        Long orderId = body.get("orderId") == null ? null : ((Number) body.get("orderId")).longValue();
        return service.stockOut(id, num(body.get("quantity")), orderId, note(body));
    }

    @GetMapping("/{id}/movements")
    public List<Map<String, Object>> movements(@PathVariable long id) {
        AuthContext.requireRole(Role.CREATOR);
        return service.movements(id);
    }

    private BigDecimal num(Object o) {
        if (o == null) throw ApiException.badRequest("缺少 quantity");
        return new BigDecimal(o.toString());
    }
    private String note(Map<String, Object> body) {
        return body.get("note") == null ? null : body.get("note").toString();
    }
}