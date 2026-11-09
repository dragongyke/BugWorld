package com.bugworld.app.garden

import android.os.Debug
import android.os.Trace
import android.util.Log
import java.util.Locale
import java.util.concurrent.atomic.AtomicInteger

/** Stage-only diagnostics; asynchronous spans are valid across coroutine suspension. */
object StageDiagnostics {
    private const val TAG="BugWorldStagePerf"
    private val sequence=AtomicInteger()

    fun <T> measure(phase: String,action: ()->T): T {
        val start=System.nanoTime()
        val cpu=Debug.threadCpuTimeNanos()
        Trace.beginSection("BugWorldStage:$phase")
        try { return action() }
        finally {
            Trace.endSection()
            Log.i(TAG,String.format(Locale.US,"phase=%s wall_ms=%.3f thread_cpu_ms=%.3f",
                phase,(System.nanoTime()-start)/1e6,(Debug.threadCpuTimeNanos()-cpu)/1e6))
        }
    }

    suspend fun <T> awaitPhase(phase: String,action: suspend ()->T): T {
        val start=System.nanoTime(); val cookie=sequence.incrementAndGet()
        Trace.beginAsyncSection("BugWorldStage:$phase",cookie)
        var completed=false
        try { return action().also { completed=true } }
        finally {
            Trace.endAsyncSection("BugWorldStage:$phase",cookie)
            Log.i(TAG,String.format(Locale.US,"phase=%s wall_ms=%.3f completed=%s",
                phase,(System.nanoTime()-start)/1e6,completed))
        }
    }

    fun frames(sample: StageFrameStats.Sample) {
        Log.i(TAG,String.format(Locale.US,
            "app_callback n=%d p50_ms=%.3f p95_ms=%.3f max_ms=%.3f over_90hz=%d over_72hz=%d logic_wall_mean_ms=%.3f logic_thread_cpu_mean_ms=%.3f (not GPU/compositor FPS)",
            sample.frames,sample.callbackP50Ms,sample.callbackP95Ms,sample.callbackMaxMs,
            sample.over90HzBudget,sample.over72HzBudget,sample.logicWallMeanMs,sample.logicCpuMeanMs))
    }
}
