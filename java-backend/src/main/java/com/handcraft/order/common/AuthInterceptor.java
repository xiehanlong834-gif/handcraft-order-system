package com.handcraft.order.common;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AuthInterceptor implements HandlerInterceptor {
    private final TokenStore tokenStore;

    public AuthInterceptor(TokenStore tokenStore) { this.tokenStore = tokenStore; }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) return true;

        String auth = request.getHeader("Authorization");
        if (auth == null || !auth.startsWith("Bearer ")) {
            throw new ApiException(401, "缺少 Authorization: Bearer <token>");
        }
        TokenStore.Session s = tokenStore.get(auth.substring(7).trim());
        if (s == null) throw new ApiException(401, "未登录或登录已过期");
        AuthContext.set(new AuthContext.CurrentUser(
                s.userId(), s.username(), s.realName(), s.roleCode()));
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                Object handler, Exception ex) {
        AuthContext.clear();
    }
}