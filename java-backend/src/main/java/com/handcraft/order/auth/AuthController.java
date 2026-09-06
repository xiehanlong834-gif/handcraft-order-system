package com.handcraft.order.auth;

import com.handcraft.order.common.ApiException;
import com.handcraft.order.common.AuthContext;
import com.handcraft.order.common.TokenStore;
import org.springframework.jdbc.core.JdbcTemplate;
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