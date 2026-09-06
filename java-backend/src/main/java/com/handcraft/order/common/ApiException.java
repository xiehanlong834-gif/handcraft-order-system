package com.handcraft.order.common;

/** 业务异常: 由 GlobalExceptionHandler 统一转为 {code,message} JSON */
public class ApiException extends RuntimeException {
    private final int code;

    public ApiException(int code, String message) {
        super(message);
        this.code = code;
    }

    public static ApiException badRequest(String msg) { return new ApiException(400, msg); }
    public static ApiException forbidden(String msg)   { return new ApiException(403, msg); }
    public static ApiException notFound(String msg)    { return new ApiException(404, msg); }

    public int getCode() { return code; }
}