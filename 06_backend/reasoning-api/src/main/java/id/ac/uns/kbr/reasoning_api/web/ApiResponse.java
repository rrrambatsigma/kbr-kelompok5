package id.ac.uns.kbr.reasoning_api.web;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

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
        meta.put("timestamp", Instant.now().toString());
        return meta;
    }
}
