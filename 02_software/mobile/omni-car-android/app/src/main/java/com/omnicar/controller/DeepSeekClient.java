package com.omnicar.controller;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;

final class DeepSeekClient {
    JSONObject decide(String text, String apiKey, List<JSONObject> history) throws Exception {
        JSONObject immediate = immediateSafetyCommand(text);
        if (immediate != null) return immediate;
        if (apiKey == null || apiKey.trim().isEmpty()) return localFallback(text);

        JSONObject body = new JSONObject();
        body.put("model", "deepseek-chat");
        body.put("temperature", 0.2);
        JSONArray messages = new JSONArray();
        messages.put(new JSONObject().put("role", "system").put("content", systemPrompt()));
        int start = Math.max(0, history.size() - 6);
        for (int i = start; i < history.size(); i++) messages.put(history.get(i));
        messages.put(new JSONObject().put("role", "user").put("content", text));
        body.put("messages", messages);
        body.put("tools", new JSONArray().put(controlTool()));
        body.put("tool_choice", "auto");

        HttpURLConnection connection = (HttpURLConnection) new URL("https://api.deepseek.com/chat/completions").openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(12000);
        connection.setReadTimeout(20000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Authorization", "Bearer " + apiKey.trim());
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        try (OutputStream output = connection.getOutputStream()) {
            output.write(body.toString().getBytes(StandardCharsets.UTF_8));
        }
        int code = connection.getResponseCode();
        String response = readAll(code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream());
        if (code < 200 || code >= 300) throw new IllegalStateException("DeepSeek 请求失败：HTTP " + code);
        JSONObject message = new JSONObject(response).getJSONArray("choices").getJSONObject(0).getJSONObject("message");
        JSONArray calls = message.optJSONArray("tool_calls");
        if (calls != null && calls.length() > 0) {
            JSONObject function = calls.getJSONObject(0).getJSONObject("function");
            JSONObject plan = new JSONObject(function.getString("arguments"));
            return sanitize(plan);
        }
        String reply = message.optString("content", "我听到了，但这句话不需要移动。").trim();
        return new JSONObject().put("action", "chat").put("reply", limit(reply, 120));
    }

    private JSONObject immediateSafetyCommand(String text) throws Exception {
        String normalized = text.replaceAll("[，。！？,.!? ]", "");
        if (containsAny(normalized, "停止", "停下", "别动", "不要动", "急停")) {
            return plan("stop", "", "standard", 0, "已停车");
        }
        if (containsAny(normalized, "回来", "返航", "回到我这里", "回到原位")) {
            return plan("return_home", "", "standard", 0, "开始按轨迹返回");
        }
        return null;
    }

    private JSONObject localFallback(String text) throws Exception {
        String shape = containsAny(text, "心形", "爱心") ? "heart" : containsAny(text, "三角形") ? "triangle" : containsAny(text, "五角星", "五星") ? "star" : containsAny(text, "方形", "正方形") ? "square" : "";
        if (!shape.isEmpty()) return shapePlan(shape, "medium", "standard", "已生成轨迹，请确认后执行");
        String direction = "";
        if (containsAny(text, "左前")) direction = "left_forward";
        else if (containsAny(text, "右前")) direction = "right_forward";
        else if (containsAny(text, "左后")) direction = "left_backward";
        else if (containsAny(text, "右后")) direction = "right_backward";
        else if (containsAny(text, "前进", "向前", "出去")) direction = "forward";
        else if (containsAny(text, "后退", "倒退", "向后")) direction = "backward";
        else if (containsAny(text, "左移", "向左")) direction = "left";
        else if (containsAny(text, "右移", "向右")) direction = "right";
        int duration = parseDuration(text);
        String speed = containsAny(text, "极速", "最快") ? "extreme" : containsAny(text, "快速", "快点") ? "fast" : "standard";
        if (!direction.isEmpty()) return plan("move", direction, speed, duration, "按本地规则执行，默认两秒");
        if (containsAny(text, "左转")) return plan("rotate", "left", speed, duration, "向左转");
        if (containsAny(text, "右转")) return plan("rotate", "right", speed, duration, "向右转");
        return new JSONObject().put("action", "chat").put("reply", "请先配置 DeepSeek API Key，我现在只能执行基础移动指令。");
    }

    private JSONObject sanitize(JSONObject source) throws Exception {
        String action = source.optString("action", "chat").toLowerCase(Locale.ROOT);
        if (!isOneOf(action, "move", "rotate", "stop", "return_home", "draw_shape", "chat")) action = "chat";
        String direction = source.optString("direction", "").toLowerCase(Locale.ROOT);
        String speed = source.optString("speed", "standard").toLowerCase(Locale.ROOT);
        if (!isOneOf(speed, "slow", "standard", "fast", "extreme")) speed = "standard";
        int duration = Math.max(200, Math.min(5000, source.optInt("duration_ms", 2000)));
        if (action.equals("draw_shape")) {
            String shape = source.optString("shape", "square").toLowerCase(Locale.ROOT);
            String size = source.optString("size", "medium").toLowerCase(Locale.ROOT);
            if (!isOneOf(shape, "heart", "triangle", "square", "star")) shape = "square";
            if (!isOneOf(size, "small", "medium", "large")) size = "medium";
            return shapePlan(shape, size, speed, limit(source.optString("reply", "轨迹已生成，请确认"), 80));
        }
        if (action.equals("stop") || action.equals("return_home") || action.equals("chat")) duration = 0;
        String reply = limit(source.optString("reply", defaultReply(action, direction)), 80);
        return plan(action, direction, speed, duration, reply);
    }

    private static JSONObject controlTool() throws Exception {
        JSONObject properties = new JSONObject();
        properties.put("action", enumString("move", "rotate", "stop", "return_home", "draw_shape", "chat"));
        properties.put("direction", enumString("forward", "backward", "left", "right", "left_forward", "right_forward", "left_backward", "right_backward"));
        properties.put("speed", enumString("slow", "standard", "fast", "extreme"));
        properties.put("shape", enumString("heart", "triangle", "square", "star"));
        properties.put("size", enumString("small", "medium", "large"));
        properties.put("duration_ms", new JSONObject().put("type", "integer").put("minimum", 200).put("maximum", 5000));
        properties.put("reply", new JSONObject().put("type", "string").put("description", "简短中文口头回复"));
        JSONObject schema = new JSONObject().put("type", "object").put("properties", properties)
                .put("required", new JSONArray().put("action").put("reply"));
        JSONObject function = new JSONObject().put("name", "control_car")
                .put("description", "在安全限制内移动、旋转、停车、返航或请求本地生成闭合图形；纯聊天使用 chat")
                .put("parameters", schema);
        return new JSONObject().put("type", "function").put("function", function);
    }

    private static JSONObject enumString(String... values) throws Exception {
        JSONArray options = new JSONArray();
        for (String value : values) options.put(value);
        return new JSONObject().put("type", "string").put("enum", options);
    }

    private static String systemPrompt() {
        return "你是三轮全向小车小麦。理解中文口语并决定是否调用 control_car。"
                + "方向相对车头：forward前进、backward后退、left/right平移；转弯用rotate。"
                + "根据用户语气、距离词和上下文选择速度与时长；未说明时通常标准速度2秒。用户说出去时用move+forward并自行选择时长。"
                + "每次最多5秒，不得声称持续无限运动。回来必须用return_home。"
                + "画心形、三角形、方形或五角星必须用draw_shape，只选择shape、size和speed，由App本地生成轨迹。"
                + "闲聊用chat并给简短自然回复。不要输出PWM、GPIO或未定义动作。";
    }

    private static JSONObject plan(String action, String direction, String speed, int duration, String reply) throws Exception {
        return new JSONObject().put("action", action).put("direction", direction).put("speed", speed)
                .put("duration_ms", duration).put("reply", reply);
    }

    private static JSONObject shapePlan(String shape, String size, String speed, String reply) throws Exception {
        return new JSONObject().put("action", "draw_shape").put("shape", shape).put("size", size)
                .put("speed", speed).put("duration_ms", 0).put("reply", reply);
    }

    private static int parseDuration(String text) {
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*秒").matcher(text);
        if (matcher.find()) return Math.max(200, Math.min(5000, (int) (Double.parseDouble(matcher.group(1)) * 1000)));
        if (text.contains("一秒")) return 1000;
        if (text.contains("两秒") || text.contains("二秒")) return 2000;
        if (text.contains("三秒")) return 3000;
        if (text.contains("四秒")) return 4000;
        if (text.contains("五秒")) return 5000;
        return 2000;
    }

    private static String defaultReply(String action, String direction) {
        if (action.equals("move")) return "开始移动";
        if (action.equals("rotate")) return "开始转向";
        if (action.equals("stop")) return "已停车";
        if (action.equals("return_home")) return "开始返回";
        return "我在";
    }

    private static boolean containsAny(String source, String... values) {
        for (String value : values) if (source.contains(value)) return true;
        return false;
    }

    private static boolean isOneOf(String source, String... values) {
        for (String value : values) if (source.equals(value)) return true;
        return false;
    }

    private static String limit(String value, int max) {
        String text = value == null ? "" : value.trim();
        return text.length() <= max ? text : text.substring(0, max);
    }

    private static String readAll(InputStream stream) throws Exception {
        if (stream == null) return "";
        StringBuilder result = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) result.append(line);
        }
        return result.toString();
    }
}
