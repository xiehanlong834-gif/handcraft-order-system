package com.handcraft.order.customer;

import com.handcraft.order.common.AuthContext;
import com.handcraft.order.common.Role;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 客户管理 REST API (P1) —— 仅创作者 */
@RestController
@RequestMapping("/api/customers")
public class CustomerController {
    private final CustomerService service;

    public CustomerController(CustomerService service) { this.service = service; }

    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(required = false) String keyword) {
        AuthContext.requireRole(Role.CREATOR);
        return service.list(keyword);
    }

    @GetMapping("/{id}")
    public Map<String, Object> detail(@PathVariable long id) {
        AuthContext.requireRole(Role.CREATOR);
        return service.detail(id);
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
}