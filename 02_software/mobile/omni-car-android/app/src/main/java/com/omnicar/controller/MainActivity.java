package com.omnicar.controller;

import android.app.Activity;
import android.content.Context;
import android.content.pm.ActivityInfo;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

import java.util.Locale;

public class MainActivity extends Activity implements SensorEventListener {
    private static final long RSSI_POLL_INTERVAL_MS = 50L;
    private WebView webView;
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private Sensor rotationVector;
    private WifiManager wifiManager;
    private VoiceAssistant voiceAssistant;
    private volatile boolean sensorEnabled;
    private final Handler rssiHandler = new Handler(Looper.getMainLooper());
    private boolean rssiMonitorRunning;
    private final Runnable rssiPoll = new Runnable() {
        @Override public void run() {
            if (!rssiMonitorRunning) return;
            int rssi = readWifiRssi();
            if (webView != null) {
                webView.evaluateJavascript("window.onNativeWifiSample&&window.onNativeWifiSample("
                        + rssi + "," + System.currentTimeMillis() + ")", null);
            }
            rssiHandler.postDelayed(this, RSSI_POLL_INTERVAL_MS);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        rotationVector = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
        wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
        webView.setVerticalScrollBarEnabled(true);
        webView.setScrollbarFadingEnabled(false);
        webView.setNestedScrollingEnabled(true);
        webView.setOverScrollMode(View.OVER_SCROLL_ALWAYS);
        webView.addJavascriptInterface(new SensorBridge(), "AndroidSensors");
        webView.addJavascriptInterface(new DisplayBridge(), "AndroidDisplay");
        voiceAssistant = new VoiceAssistant(this);
        voiceAssistant.setEnabled(false);
        webView.addJavascriptInterface(new VoiceBridge(), "AndroidVoice");
        WebView.setWebContentsDebuggingEnabled(true);
        setContentView(webView);
        webView.loadUrl("file:///android_asset/index.html");
        startRssiMonitor();
    }

    private int readWifiRssi() {
        if (wifiManager == null) return -127;
        WifiInfo info = wifiManager.getConnectionInfo();
        return info == null ? -127 : info.getRssi();
    }

    private void startRssiMonitor() {
        if (rssiMonitorRunning) return;
        rssiMonitorRunning = true;
        rssiHandler.post(rssiPoll);
    }

    private void stopRssiMonitor() {
        rssiMonitorRunning = false;
        rssiHandler.removeCallbacks(rssiPoll);
    }

    private void startSensors() {
        runOnUiThread(() -> {
            if (sensorEnabled || accelerometer == null) {
                if (accelerometer == null) {
                    webView.evaluateJavascript("window.onNativeSensorError&&window.onNativeSensorError()", null);
                }
                return;
            }
            boolean accelerationStarted = sensorManager.registerListener(
                    this, accelerometer, SensorManager.SENSOR_DELAY_GAME);
            boolean headingStarted = rotationVector != null && sensorManager.registerListener(
                    this, rotationVector, SensorManager.SENSOR_DELAY_GAME);
            sensorEnabled = accelerationStarted;
            if (!headingStarted) {
                webView.evaluateJavascript(
                        "window.onNativeHeadingUnavailable&&window.onNativeHeadingUnavailable()", null);
            }
        });
    }

    private void stopSensors() {
        runOnUiThread(() -> {
            sensorManager.unregisterListener(this);
            sensorEnabled = false;
        });
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (!sensorEnabled) return;
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            double x = event.values[0] / SensorManager.GRAVITY_EARTH;
            double y = event.values[1] / SensorManager.GRAVITY_EARTH;
            double z = event.values[2] / SensorManager.GRAVITY_EARTH;
            String script = String.format(Locale.US,
                    "window.onNativeAcceleration&&window.onNativeAcceleration(%.6f,%.6f,%.6f,%d)",
                    x, y, z, System.currentTimeMillis());
            webView.evaluateJavascript(script, null);
        } else if (event.sensor.getType() == Sensor.TYPE_ROTATION_VECTOR) {
            float[] matrix = new float[9];
            float[] orientation = new float[3];
            SensorManager.getRotationMatrixFromVector(matrix, event.values);
            SensorManager.getOrientation(matrix, orientation);
            double heading = Math.toDegrees(orientation[0]);
            if (heading < 0) heading += 360.0;
            String script = String.format(Locale.US,
                    "window.onNativeHeading&&window.onNativeHeading(%.3f,%d)",
                    heading, System.currentTimeMillis());
            webView.evaluateJavascript(script, null);
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}

    @Override
    protected void onPause() {
        stopRssiMonitor();
        if (voiceAssistant != null) voiceAssistant.pause();
        if (webView != null) {
            webView.evaluateJavascript("window.onNativePause&&window.onNativePause()", null);
            webView.onPause();
        }
        stopSensors();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.onResume();
            webView.evaluateJavascript("window.onNativeResume&&window.onNativeResume()", null);
        }
        if (voiceAssistant != null) voiceAssistant.resume();
        startRssiMonitor();
    }

    @Override
    protected void onDestroy() {
        stopRssiMonitor();
        stopSensors();
        if (voiceAssistant != null) voiceAssistant.release();
        if (webView != null) {
            webView.evaluateJavascript("window.onNativeDestroy&&window.onNativeDestroy()", null);
            webView.destroy();
        }
        super.onDestroy();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == VoiceAssistant.MICROPHONE_REQUEST && voiceAssistant != null) {
            boolean granted = grantResults.length > 0 && grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED;
            voiceAssistant.onMicrophonePermissionResult(granted);
        }
    }

    void emitVoiceState(String state, String detail) {
        runOnUiThread(() -> {
            if (webView == null) return;
            String script = "window.onNativeVoiceState&&window.onNativeVoiceState("
                    + JSONObject.quote(state) + "," + JSONObject.quote(detail) + ")";
            webView.evaluateJavascript(script, null);
        });
    }

    void emitVoiceTranscript(String transcript, boolean complete) {
        runOnUiThread(() -> {
            if (webView == null) return;
            String script = "window.onNativeVoiceTranscript&&window.onNativeVoiceTranscript("
                    + JSONObject.quote(transcript) + "," + complete + ")";
            webView.evaluateJavascript(script, null);
        });
    }

    void emitVoicePlan(String planJson) {
        runOnUiThread(() -> {
            if (webView == null) return;
            String script = "window.onNativeVoicePlan&&window.onNativeVoicePlan(" + JSONObject.quote(planJson) + ")";
            webView.evaluateJavascript(script, null);
        });
    }

    public class SensorBridge {
        @JavascriptInterface
        public void startAccelerometer() {
            startSensors();
        }

        @JavascriptInterface
        public void stopAccelerometer() {
            stopSensors();
        }

        @JavascriptInterface
        public boolean hasAccelerometer() {
            return accelerometer != null;
        }

        @JavascriptInterface
        public boolean hasHeadingSensor() {
            return rotationVector != null;
        }

        @JavascriptInterface
        public int getWifiRssi() {
            return readWifiRssi();
        }

        @JavascriptInterface
        public boolean isOmniCarNetwork() {
            if (wifiManager == null) return false;
            WifiInfo info = wifiManager.getConnectionInfo();
            if (info == null) return false;
            int address = info.getIpAddress();
            return (address & 0xff) == 192
                    && ((address >> 8) & 0xff) == 168
                    && ((address >> 16) & 0xff) == 4;
        }
    }

    public class DisplayBridge {
        @JavascriptInterface
        public void setDualLandscape(boolean enabled) {
            runOnUiThread(() -> setRequestedOrientation(enabled
                    ? ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
                    : ActivityInfo.SCREEN_ORIENTATION_PORTRAIT));
        }
    }

    public class VoiceBridge {
        @JavascriptInterface
        public boolean isAvailable() {
            return true;
        }

        @JavascriptInterface
        public String getConfigurationState() {
            return voiceAssistant == null ? "{}" : voiceAssistant.getConfigurationState();
        }

        @JavascriptInterface
        public void saveConfiguration(String aliyunKey, String deepSeekKey) {
            runOnUiThread(() -> voiceAssistant.saveConfiguration(aliyunKey, deepSeekKey));
        }

        @JavascriptInterface
        public void setEnabled(boolean enabled) {
            runOnUiThread(() -> voiceAssistant.setEnabled(enabled));
        }

        @JavascriptInterface
        public void submitText(String text) {
            runOnUiThread(() -> voiceAssistant.submitText(text));
        }

        @JavascriptInterface
        public void simulateWake() {
            runOnUiThread(() -> voiceAssistant.simulateWake());
        }
    }
}
