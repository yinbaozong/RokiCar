package com.omnicar.controller;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;

import com.alibaba.idst.nui.AsrResult;
import com.alibaba.idst.nui.Constants;
import com.alibaba.idst.nui.INativeNuiCallback;
import com.alibaba.idst.nui.KwsResult;
import com.alibaba.idst.nui.NativeNui;

import org.json.JSONObject;

import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.atomic.AtomicBoolean;

final class AliyunRecognizer implements INativeNuiCallback {
    interface Listener {
        void onPartial(String text);
        void onResult(String text);
        void onError(String message);
    }

    private static final int SAMPLE_RATE = 16000;
    private final Context context;
    private final ExecutorService executor;
    private NativeNui nui;
    private AudioRecord recorder;
    private Listener listener;
    private String configuredKey = "";
    private boolean initialized;
    private final AtomicBoolean completed = new AtomicBoolean(true);

    AliyunRecognizer(Context context, ExecutorService executor) {
        this.context = context.getApplicationContext();
        this.executor = executor;
    }

    void start(String apiKey, Listener nextListener) {
        listener = nextListener;
        completed.set(false);
        executor.execute(() -> {
            try {
                if (!ensureInitialized(apiKey)) return;
                JSONObject nls = new JSONObject();
                nls.put("sample_rate", SAMPLE_RATE);
                nls.put("sr_format", "pcm");
                nls.put("model", "paraformer-realtime-v2");
                nls.put("language_hints", new org.json.JSONArray().put("zh"));
                nls.put("enable_voice_detection", true);
                nls.put("max_start_silence", 7000);
                nls.put("max_end_silence", 900);
                nls.put("enable_punctuation_prediction", true);
                JSONObject params = new JSONObject();
                params.put("nls_config", nls);
                params.put("service_type", Constants.kServiceTypeASR);
                nui.setParams(params.toString());
                int result = nui.startDialog(Constants.VadMode.TYPE_VAD, "{}");
                if (result != Constants.NuiResultCode.SUCCESS) fail("阿里云识别启动失败：" + result);
            } catch (Exception error) {
                fail("阿里云识别启动失败：" + safeMessage(error));
            }
        });
    }

    void stop() {
        completed.set(true);
        executor.execute(() -> {
            try { if (nui != null) nui.cancelDialog(); } catch (Exception ignored) {}
            closeRecorder();
        });
    }

    void resetConfiguration() {
        executor.execute(() -> {
            initialized = false;
            configuredKey = "";
            try { if (nui != null) nui.release(); } catch (Exception ignored) {}
            nui = null;
        });
    }

    void release() {
        completed.set(true);
        closeRecorder();
        try { if (nui != null) nui.release(); } catch (Exception ignored) {}
        nui = null;
        initialized = false;
    }

    private boolean ensureInitialized(String apiKey) {
        if (initialized && apiKey.equals(configuredKey)) return true;
        try { if (nui != null) nui.release(); } catch (Exception ignored) {}
        nui = new NativeNui();
        try {
            JSONObject ticket = new JSONObject();
            ticket.put("apikey", apiKey);
            ticket.put("device_id", UUID.nameUUIDFromBytes(context.getPackageName().getBytes()).toString());
            ticket.put("url", "wss://dashscope.aliyuncs.com/api-ws/v1/inference");
            ticket.put("service_mode", "1");
            ticket.put("save_wav", "false");
            int result = nui.initialize(this, ticket.toString(), Constants.LogLevel.LOG_LEVEL_ERROR, false);
            initialized = result == Constants.NuiResultCode.SUCCESS;
            if (!initialized) {
                fail("阿里云 SDK 初始化失败：" + result);
                return false;
            }
            configuredKey = apiKey;
            return true;
        } catch (Exception error) {
            fail("阿里云 SDK 初始化失败：" + safeMessage(error));
            return false;
        }
    }

    @Override
    public void onNuiEventCallback(Constants.NuiEvent event, int resultCode, int arg2,
                                   KwsResult kwsResult, AsrResult asrResult) {
        if (event == Constants.NuiEvent.EVENT_ASR_PARTIAL_RESULT) {
            String text = extractText(asrResult);
            if (!text.isEmpty() && listener != null) listener.onPartial(text);
        } else if (event == Constants.NuiEvent.EVENT_ASR_RESULT || event == Constants.NuiEvent.EVENT_SENTENCE_END) {
            String text = extractText(asrResult);
            if (!text.isEmpty() && completed.compareAndSet(false, true) && listener != null) {
                listener.onResult(text);
                executor.execute(() -> { try { nui.stopDialog(); } catch (Exception ignored) {} });
            }
        } else if (event == Constants.NuiEvent.EVENT_ASR_ERROR ||
                event == Constants.NuiEvent.EVENT_DIALOG_ERROR ||
                event == Constants.NuiEvent.EVENT_ONESHOT_TIMEOUT ||
                event == Constants.NuiEvent.EVENT_VAD_TIMEOUT ||
                event == Constants.NuiEvent.EVENT_MIC_ERROR) {
            fail("语音识别失败：" + resultCode);
        }
    }

    private String extractText(AsrResult result) {
        if (result == null) return "";
        for (String candidate : new String[]{result.asrResult, result.allResponse}) {
            if (candidate == null || candidate.isEmpty()) continue;
            try {
                JSONObject json = new JSONObject(candidate);
                JSONObject payload = json.optJSONObject("payload");
                String text = payload == null ? json.optString("result") : payload.optString("result");
                if (!text.isEmpty()) return text.trim();
            } catch (Exception ignored) {}
        }
        return "";
    }

    private void fail(String message) {
        if (completed.compareAndSet(false, true) && listener != null) listener.onError(message);
        closeRecorder();
    }

    @Override
    public int onNuiNeedAudioData(byte[] buffer, int len) {
        AudioRecord active = recorder;
        if (active == null || active.getState() != AudioRecord.STATE_INITIALIZED) return -1;
        return active.read(buffer, 0, len);
    }

    @Override
    public synchronized void onNuiAudioStateChanged(Constants.AudioState state) {
        if (state == Constants.AudioState.STATE_OPEN) {
            if (context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                fail("没有麦克风权限");
                return;
            }
            int minimum = AudioRecord.getMinBufferSize(
                    SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
            recorder = new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, SAMPLE_RATE,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, Math.max(minimum * 2, 6400));
            recorder.startRecording();
        } else if (state == Constants.AudioState.STATE_CLOSE) {
            closeRecorder();
        }
    }

    private synchronized void closeRecorder() {
        AudioRecord active = recorder;
        recorder = null;
        try { if (active != null) active.stop(); } catch (Exception ignored) {}
        if (active != null) active.release();
    }

    @Override public void onNuiAudioRMSChanged(float value) {}
    @Override public void onNuiVprEventCallback(Constants.NuiVprEvent event) {}

    private static String safeMessage(Throwable error) {
        return error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
    }
}
