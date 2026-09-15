package com.rokicar.controller

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Handler
import android.os.Looper
import com.k2fsa.sherpa.onnx.FeatureConfig
import com.k2fsa.sherpa.onnx.KeywordSpotter
import com.k2fsa.sherpa.onnx.KeywordSpotterConfig
import com.k2fsa.sherpa.onnx.OnlineModelConfig
import com.k2fsa.sherpa.onnx.OnlineTransducerModelConfig
import java.util.concurrent.atomic.AtomicInteger

class WakeWordEngine(
    private val context: Context,
    private val onWake: (String) -> Unit,
    private val onError: (String) -> Unit,
) {
    private val main = Handler(Looper.getMainLooper())
    private val generation = AtomicInteger(0)
    @Volatile private var running = false
    @Volatile private var released = false
    private var spotter: KeywordSpotter? = null
    private var recorder: AudioRecord? = null

    fun start() {
        if (released || running) return
        if (context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            onError("需要麦克风权限")
            return
        }
        running = true
        val run = generation.incrementAndGet()
        Thread({ runLoop(run) }, "Xiaomai-Wake").start()
    }

    fun stop() {
        running = false
        generation.incrementAndGet()
        try { recorder?.stop() } catch (_: Exception) {}
    }

    fun release() {
        released = true
        stop()
        spotter?.release()
        spotter = null
    }

    private fun runLoop(run: Int) {
        try {
            val detector = spotter ?: createSpotter().also { spotter = it }
            val stream = detector.createStream()
            if (stream.ptr == 0L) throw IllegalStateException("无法创建唤醒流")
            val sampleRate = 16000
            val minimum = AudioRecord.getMinBufferSize(
                sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
            )
            val audio = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(minimum * 2, 6400)
            )
            recorder = audio
            audio.startRecording()
            val pcm = ShortArray(1600)
            while (running && generation.get() == run && !released) {
                val count = audio.read(pcm, 0, pcm.size)
                if (count <= 0) continue
                val samples = FloatArray(count) { pcm[it] / 32768.0f }
                stream.acceptWaveform(samples, sampleRate)
                while (detector.isReady(stream)) {
                    detector.decode(stream)
                    val keyword = detector.getResult(stream).keyword
                    if (keyword.isNotBlank()) {
                        detector.reset(stream)
                        running = false
                        main.post { onWake(keyword) }
                        break
                    }
                }
            }
            stream.release()
        } catch (error: Throwable) {
            if (!released) main.post { onError(error.message ?: "本地唤醒失败") }
        } finally {
            val audio = recorder
            recorder = null
            try { audio?.stop() } catch (_: Exception) {}
            audio?.release()
            if (generation.get() == run) running = false
        }
    }

    private fun createSpotter(): KeywordSpotter {
        val model = OnlineModelConfig(
            transducer = OnlineTransducerModelConfig(
                encoder = "kws/encoder.int8.onnx",
                decoder = "kws/decoder.onnx",
                joiner = "kws/joiner.int8.onnx",
            ),
            tokens = "kws/tokens.txt",
            numThreads = 2,
            provider = "cpu",
            modelingUnit = "cjkchar",
        )
        return KeywordSpotter(
            context.assets,
            KeywordSpotterConfig(
                featConfig = FeatureConfig(sampleRate = 16000, featureDim = 80),
                modelConfig = model,
                keywordsFile = "kws/keywords.txt",
                keywordsScore = 1.5f,
                keywordsThreshold = 0.25f,
                numTrailingBlanks = 1,
            )
        )
    }
}
