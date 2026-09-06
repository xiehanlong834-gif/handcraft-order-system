package com.handcraft.order.auth;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import com.handcraft.order.common.TokenStore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** 登录 / 登出 / 当前用户 —— 账号密码 BCrypt 校验, 返回 Bearer token */
@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final JdbcTemplate jdbc;
    private final BCryptPasswordEncoder encoder;
    private final TokenStore tokenStore;

    public AuthController(JdbcTemplate jdbc, BCryptPasswordEncoder encoder, TokenStore tokenStore) {
        this.jdbc = jdbc;
        this.encoder = encoder;
        this.tokenStore = tokenStore;
    }

    /**
     * 公开自助注册: 只能注册为客户角色。
     * 自动创建 customer 档案, 归属系统首个启用的创作者(单工作室场景)。
     * 禁止自助注册 creator/admin/finance(高权限账号仅管理员可建)。
     */
    @PostMapping("/register")
    @Transactional
    public Map<String, Object> register(@RequestBody Map<String, String> body) {
        String username = body.getOrDefault("username", "").trim();
        String password = body.getOrDefault("password", "");
        String nickname = body.getOrDefault("nickname", "").trim();
        String phone = body.getOrDefault("phone", "").trim();
        if (username.length() < 3 || username.length() > 20) {
            throw ApiException.badRequest("用户名长度需 3-20 位");
        }
        if (!username.matches("[A-Za-z0-9_]+")) {
            throw ApiException.badRequest("用户名仅允许字母/数字/下划线");
        }
        if (password.length() < 6) {
            throw ApiException.badRequest("密码长度至少 6 位");
        }
        if (nickname.isEmpty()) {
            throw ApiException.badRequest("请填写称呼(昵称)");
        }
        Integer dup = jdbc.queryForObject("SELECT COUNT(*) FROM `user` WHERE username = ?",
                Integer.class, username);
        if (dup != null && dup > 0) {
            throw ApiException.badRequest("用户名已存在");
        }
        // 归属创作者: 系统内第一个启用的 creator 账号
        List<Map<String, Object>> creators = jdbc.queryForList(
                "SELECT u.user_id AS userId FROM `user` u JOIN role r ON r.role_id = u.role_id " +
                "WHERE r.role_code = 'creator' AND u.status = 1 ORDER BY u.user_id LIMIT 1");
        if (creators.isEmpty()) {
            throw ApiException.badRequest("系统暂无可接单的创作者, 请联系管理员");
        }
        long creatorId = ((Number) creators.get(0).get("userId")).longValue();
        Long customerRoleId = jdbc.queryForObject(
                "SELECT role_id FROM role WHERE role_code = 'customer'", Long.class);

        // 事务内: 客户档案 + 账号(BCrypt)
        jdbc.update("INSERT INTO customer (name, phone, creator_id) VALUES (?,?,?)",
                nickname, phone, creatorId);
        long customerId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        jdbc.update("INSERT INTO `user` (username, password_hash, real_name, phone, role_id, customer_id, status) " +
                        "VALUES (?,?,?,?,?,?,1)",
                username, encoder.encode(password), nickname, phone, customerRoleId, customerId);
        long userId = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return Map.of(
                "userId", userId, "message", "注册成功, 默认角色: 客户",
                "roleCode", "customer");
    }

    @PostMapping("/login")
    public Map<String, Object> login(@RequestBody Map<String, String> body) {
        String username = body.getOrDefault("username", "").trim();
        String password = body.getOrDefault("password", "");
        if (username.isEmpty() || password.isEmpty()) {
            throw ApiException.badRequest("用户名与密码不能为空");
        }
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT u.user_id AS userId, u.username, u.password_hash AS passwordHash, " +
                "       u.real_name AS realName, u.phone, u.customer_id AS customerId, " +
                "       r.role_code AS roleCode, r.role_name AS roleName " +
                "FROM `user` u JOIN role r ON r.role_id = u.role_id " +
                "WHERE u.username = ? AND u.status = 1", username);
        if (rows.isEmpty() || !encoder.matches(password, String.valueOf(rows.get(0).get("passwordHash")))) {
            throw ApiException.badRequest("用户名或密码错误");
        }
        Map<String, Object> u = rows.get(0);
        String token = tokenStore.create(((Number) u.get("userId")).longValue(),
                (String) u.get("username"), (String) u.get("realName"), (String) u.get("roleCode"));

        Map<String, Object> user = new HashMap<>();
        user.put("userId", u.get("userId"));
        user.put("username", u.get("username"));
        user.put("realName", u.get("realName"));
        user.put("roleCode", u.get("roleCode"));
        user.put("roleName", u.get("roleName"));
        user.put("customerId", u.get("customerId"));

        Map<String, Object> resp = new HashMap<>();
        resp.put("token", token);
        resp.put("user", user);
        return resp;
    }

    @PostMapping("/logout")
    public Map<String, Object> logout(@RequestHeader("Authorization") String auth) {
        tokenStore.revoke(auth.replace("Bearer ", "").trim());
        return Map.of("message", "已退出登录");
    }

    @GetMapping("/me")
    public Map<String, Object> me() {
        AuthContext.CurrentUser u = AuthContext.current();
        return Map.of(
                "userId", u.userId(), "username", u.username(),
                "realName", u.realName(), "roleCode", u.roleCode());
    }
}