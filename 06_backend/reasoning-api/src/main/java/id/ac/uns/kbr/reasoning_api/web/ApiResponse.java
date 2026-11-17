package id.ac.uns.kbr.reasoning_api.web;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

public final class ApiResponse {

    private ApiResponse() {
    }

    public static Map<String, Object> ok(Object data) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("success", true);
        body.put("data", data);
        body.put("meta", meta());
        return body;
    }

    public static Map<String, Object> error(String code, String message) {
        Map<String, Object> error = new LinkedHashMap<>();
        error.put("code", code);
        error.put("message", message);
        error.put("details", null);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("success", false);
        body.put("data", null);
        body.put("error", error);
        body.put("meta", meta());
        return body;
    }

    public static Map<String, Object> meta() {
        Map<String, Object> meta = new LinkedHashMap<>();
        meta.put("service", "kbr-reasoning-api");
        meta.put("requestId", currentRequestId());
        meta.put("timestamp", Instant.now().toString());
        return meta;
    }

    private static String currentRequestId() {
        RequestAttributes attributes = RequestContextHolder.getRequestAttributes();

        if (attributes instanceof ServletRequestAttributes servletAttributes) {
            Object value = servletAttributes.getRequest()
                    .getAttribute(RequestIdFilter.ATTRIBUTE);
            return value == null ? null : value.toString();
        }

        return null;
    }
}
