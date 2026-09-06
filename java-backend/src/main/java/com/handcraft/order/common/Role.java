package com.handcraft.order.common;

/** 四类角色 —— 与 role 表 role_code 对应 */
public enum Role {
    CREATOR("creator", "创作者"),
    CUSTOMER("customer", "客户"),
    ADMIN("admin", "管理员"),
    FINANCE("finance", "财务查看者");

    private final String code;
    private final String label;

    Role(String code, String label) {
        this.code = code;
        this.label = label;
    }
    public String getCode() { return code; }
    public String getLabel() { return label; }

    public static Role fromCode(String code) {
        for (Role r : values()) {
            if (r.code.equals(code)) return r;
        }
        throw new ApiException(403, "未知角色: " + code);
    }
}