package com.handcraft.order.common;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 轻量会话存储(课程简化版, 内存态):
 * 生产可替换为 JWT(无状态) 或 Redis, 接口语义不变。
 * Token 有效期 24 小时。
 */
@Component
public class TokenStore {
    public record Session(long userId, String username, String realName,
                          String roleCode, Instant expireAt) {}

    private static final long TTL_SECONDS = 24 * 3600;
    private final Map<String, Session> store = new ConcurrentHashMap<>();

    public String create(long userId, String username, String realName, String roleCode) {
        String token = UUID.randomUUID().toString().replace("-", "");
        store.put(token, new Session(userId, username, realName, roleCode,
                Instant.now().plusSeconds(TTL_SECONDS)));
        return token;
    }

    public Session get(String token) {
        Session s = store.get(token);
        if (s == null) return null;
        if (s.expireAt().isBefore(Instant.now())) {
            store.remove(token);
            return null;
        }
        return s;
    }

    public void revoke(String token) { store.remove(token); }
}