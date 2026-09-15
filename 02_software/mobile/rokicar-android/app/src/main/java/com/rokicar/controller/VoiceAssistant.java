package com.rokicar.controller;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

final class VoiceAssistant {
    static final int MICROPHONE_REQUEST = 7001;
    private static final String ALIYUN_KEY = "aliyun_dashscope_key";
    private static final String DEEPSEEK_KEY = "deepseek_key";
    private final MainActivity activity;
    private final SecureStore secrets;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final WakeWordEngine wakeWord;
    private final AliyunRecognizer recognizer;
    private final DeepSeekClient deepSeek = new DeepSeekClient();
    private final List<JSONObject> history = new ArrayList<>();
    private final Map<String, Runnable> speechCallbacks = new HashMap<>();
    private TextToSpeech tts;
    private boolean ttsReady;
    private boolean enabled;
    private boolean paused;
    private long sessionUntil;

    VoiceAssistant(MainActivity activity) {
        this.activity = activity;
        secrets = new SecureStore(activity);
        enabled = activity.getSharedPreferences("voice_state", Context.MODE_PRIVATE)
                .getBoolean("enabled", false);
        wakeWord = new WakeWordEngine(activity,
                keyword -> { onWakeWord(keyword); return kotlin.Unit.INSTANCE; },
                message -> { onWakeError(message); return kotlin.Unit.INSTANCE; });
        recognizer = new AliyunRecognizer(activity, executor);
        tts = new TextToSpeech(activity.getApplicationContext(), status -> {
            ttsReady = status == TextToSpeech.SUCCESS;
            if (ttsReady) {
                tts.setLanguage(Locale.SIMPLIFIED_CHINESE);
                tts.setSpeechRate(1.05f);
                tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                    @Override public void onStart(String utteranceId) {}
                    @Override public void onError(String utteranceId) { finishSpeech(utteranceId); }
                    @Override public void onDone(String utteranceId) { finishSpeech(utteranceId); }
                });
            }
        });
    }

    void setEnabled(boolean next) {
        enabled = next;
        activity.getSharedPreferences("voice_state", Context.MODE_PRIVATE).edit()
                .putBoolean("enabled", next).apply();
        if (!next) {
            stopListening();
            activity.emitVoicePlan("{\"action\":\"stop\",\"reply\":\"语音控制已关闭\"}");
            emitState("off", "语音控制已关闭");
            return;
        }
        if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            activity.requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MICROPHONE_REQUEST);
            emitState("permission", "请允许麦克风权限");
            return;
        }
        startWakeListening();
    }

    void onMicrophonePermissionResult(boolean granted) {
        if (granted && enabled) startWakeListening();
        else {
            enabled = false;
            emitState("error", "没有麦克风权限，无法监听小麦小麦");
        }
    }

    void saveConfiguration(String aliyunKey, String deepSeekKey) {
        if (aliyunKey != null && !aliyunKey.trim().isEmpty()) secrets.put(ALIYUN_KEY, aliyunKey.trim());
        if (deepSeekKey != null && !deepSeekKey.trim().isEmpty()) secrets.put(DEEPSEEK_KEY, deepSeekKey.trim());
        recognizer.resetConfiguration();
        emitState("configured", "语音配置已安全保存");
    }

    String getConfigurationState() {
        try {
            return new JSONObject()
                    .put("wakeWord", "小麦小麦")
                    .put("enabled", enabled)
                    .put("aliyunKey", !secrets.get(ALIYUN_KEY).isEmpty())
                    .put("deepSeekKey", !secrets.get(DEEPSEEK_KEY).isEmpty())
                    .toString();
        } catch (Exception error) {
            return "{}";
        }
    }

    void submitText(String text) {
        if (text == null || text.trim().isEmpty()) return;
        sessionUntil = System.currentTimeMillis() + 30000;
        processRecognized(text.trim(), false);
    }

    void simulateWake() {
        onWakeWord("小麦小麦（测试）");
    }

    void pause() {
        paused = true;
        stopListening();
        activity.emitVoicePlan("{\"action\":\"stop\",\"reply\":\"\",\"silent\":true}");
    }

    void resume() {
        paused = false;
        if (enabled && activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            main.postDelayed(this::startWakeListening, 300);
        }
    }

    void release() {
        enabled = false;
        stopListening();
        wakeWord.release();
        recognizer.release();
        if (tts != null) tts.shutdown();
        executor.shutdownNow();
    }

    private void startWakeListening() {
        if (!enabled || paused) return;
        recognizer.stop();
        emitState("wake", "正在本地等待“小麦小麦”");
        wakeWord.start();
    }

    private void onWakeWord(String keyword) {
        if (!enabled || paused) return;
        sessionUntil = System.currentTimeMillis() + 30000;
        emitState("woken", "已唤醒：" + keyword);
        speakThen("我在", () -> main.postDelayed(this::startCloudRecognition, 120));
    }

    private void onWakeError(String message) {
        emitState("error", message);
        if (enabled && !paused) main.postDelayed(this::startWakeListening, 1500);
    }

    private void startCloudRecognition() {
        if (!enabled || paused) return;
        String apiKey = secrets.get(ALIYUN_KEY);
        if (apiKey.isEmpty()) {
            emitState("config", "请先填写阿里云百炼 API Key");
            speakThen("请先配置阿里云语音识别", this::startWakeListening);
            return;
        }
        emitState("asr", "请说话");
        recognizer.start(apiKey, new AliyunRecognizer.Listener() {
            @Override public void onPartial(String text) { activity.emitVoiceTranscript(text, false); }
            @Override public void onResult(String text) {
                main.post(() -> processRecognized(text, true));
            }
            @Override public void onError(String message) {
                main.post(() -> {
                    emitState("error", message);
                    speakThen("这次没听清", VoiceAssistant.this::startWakeListening);
                });
            }
        });
    }

    private void processRecognized(String text, boolean continueConversation) {
        activity.emitVoiceTranscript(text, true);
        emitState("thinking", "小麦正在判断动作");
        executor.execute(() -> {
            try {
                JSONObject plan = deepSeek.decide(text, secrets.get(DEEPSEEK_KEY), new ArrayList<>(history));
                history.add(new JSONObject().put("role", "user").put("content", text));
                history.add(new JSONObject().put("role", "assistant").put("content", plan.optString("reply", "")));
                while (history.size() > 8) history.remove(0);
                main.post(() -> deliverPlan(plan, continueConversation));
            } catch (Exception error) {
                main.post(() -> {
                    emitState("error", error.getMessage() == null ? "AI 请求失败" : error.getMessage());
                    activity.emitVoicePlan("{\"action\":\"stop\",\"reply\":\"\"}");
                    speakThen("网络请求失败，小车已经停车", this::startWakeListening);
                });
            }
        });
    }

    private void deliverPlan(JSONObject plan, boolean continueConversation) {
        activity.emitVoicePlan(plan.toString());
        String reply = plan.optString("reply", "收到");
        emitState("reply", reply);
        int duration = Math.max(0, Math.min(5000, plan.optInt("duration_ms", 0)));
        speakThen(reply, () -> {
            if (continueConversation && enabled && !paused && System.currentTimeMillis() < sessionUntil) {
                main.postDelayed(this::startCloudRecognition, duration + 250L);
            } else if (enabled && !paused) {
                main.postDelayed(this::startWakeListening, duration + 250L);
            }
        });
    }

    private void stopListening() {
        wakeWord.stop();
        recognizer.stop();
        if (tts != null) tts.stop();
        speechCallbacks.clear();
    }

    private void speakThen(String text, Runnable next) {
        if (!ttsReady || tts == null || text == null || text.isEmpty()) {
            if (next != null) main.post(next);
            return;
        }
        String id = UUID.randomUUID().toString();
        if (next != null) speechCallbacks.put(id, next);
        int result = tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, id);
        if (result == TextToSpeech.ERROR) finishSpeech(id);
    }

    private void finishSpeech(String id) {
        main.post(() -> {
            Runnable next = speechCallbacks.remove(id);
            if (next != null) next.run();
        });
    }

    private void emitState(String state, String detail) {
        activity.emitVoiceState(state, detail);
    }
}
