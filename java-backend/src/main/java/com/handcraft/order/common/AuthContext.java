package com.handcraft.order.common;

/**
 * 线程级登录上下文: 由 AuthInterceptor 写入, Controller/Service 读取。
 */
public final class AuthContext {
    public record CurrentUser(long userId, String username, String realName, String roleCode) {}

    private static final ThreadLocal<CurrentUser> HOLDER = new ThreadLocal<>();

    private AuthContext() {}

    public static void set(CurrentUser u) { HOLDER.set(u); }
    public static void clear() { HOLDER.remove(); }

    public static CurrentUser current() {
        CurrentUser u = HOLDER.get();
        if (u == null) throw new ApiException(401, "未登录或登录已过期");
        return u;
    }

    public static boolean hasRole(Role role) {
        CurrentUser u = HOLDER.get();
        return u != null && u.roleCode().equals(role.getCode());
    }

    public static void requireRole(Role... roles) {
        CurrentUser u = current();
        for (Role r : roles) {
            if (u.roleCode().equals(r.getCode())) return;
        }
        throw ApiException.forbidden("当前角色[" + u.roleCode() + "]无权执行该操作(需要: "
                + java.util.Arrays.toString(roles) + ")");
    }
}