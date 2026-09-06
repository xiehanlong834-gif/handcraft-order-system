package com.handcraft.order.order;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import com.handcraft.order.common.Role;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 订单 REST API (P0 核心闭环)
 *  创作者: 建单/列表/详情/状态流转/成本/取消/归档/提醒/排期
 *  客户:   我的订单/详情/提交定制需求
 */
@RestController
@RequestMapping("/api")
public class OrderController {
    private final OrderService service;

    public OrderController(OrderService service) { this.service = service; }

    // ---------- 订单列表/详情 ----------
    @GetMapping("/orders")
    public List<Map<String, Object>> list(@RequestParam(required = false) String status,
                                          @RequestParam(required = false) String keyword) {
        return service.list(status, keyword);
    }

    @GetMapping("/orders/{id}")
    public Map<String, Object> detail(@PathVariable long id) {
        return service.detail(id);
    }

    // ---------- 创作者: 建单/流转/成本/归档 ----------
    @PostMapping("/orders")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        return service.createByCreator(body);
    }

    @PatchMapping("/orders/{id}/status")
    public Map<String, Object> changeStatus(@PathVariable long id,
                                            @RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        return service.changeStatus(id, String.valueOf(body.get("toStatus")),
                body.get("note") == null ? null : body.get("note").toString());
    }

    @PostMapping("/orders/{id}/archive")
    public Map<String, Object> archive(@PathVariable long id) {
        AuthContext.requireRole(Role.CREATOR);
        return service.archive(id);
    }

    @PostMapping("/orders/{id}/cancel")
    public Map<String, Object> cancel(@PathVariable long id) {
        AuthContext.requireRole(Role.CREATOR);
        return service.cancel(id);
    }

    @PostMapping("/orders/{id}/materials")
    public Map<String, Object> addMaterial(@PathVariable long id, @RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        if (body.get("materialId") == null || body.get("quantityUsed") == null) {
            throw ApiException.badRequest("缺少 materialId / quantityUsed");
        }
        return service.addMaterial(id, ((Number) body.get("materialId")).longValue(),
                new BigDecimal(body.get("quantityUsed").toString()));
    }

    @PostMapping("/orders/{id}/labor-cost")
    public Map<String, Object> setLaborCost(@PathVariable long id, @RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CREATOR);
        if (body.get("laborCost") == null) throw ApiException.badRequest("缺少 laborCost");
        return service.setLaborCost(id, new BigDecimal(body.get("laborCost").toString()));
    }

    // ---------- 客户: 我的订单 + 定制需求提交 ----------
    @GetMapping("/my/orders")
    public List<Map<String, Object>> myOrders(@RequestParam(required = false) String status) {
        AuthContext.requireRole(Role.CUSTOMER);
        return service.list(status, null);
    }

    @PostMapping("/my/custom-requests")
    public Map<String, Object> submitCustomRequest(@RequestBody Map<String, Object> body) {
        AuthContext.requireRole(Role.CUSTOMER);
        return service.createByCustomer(body);
    }

    // ---------- 排期与提醒(创作者) ----------
    @GetMapping("/orders/due-reminders")
    public List<Map<String, Object>> dueReminders() {
        return service.dueReminders();
    }

    @GetMapping("/schedule")
    public List<Map<String, Object>> schedule(@RequestParam(required = false) String month) {
        return service.schedule(month);
    }
}