package com.bugworld.app.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.SoundPool

class GardenAudio(context: Context) : AutoCloseable {
    private val players=mutableListOf<MediaPlayer>()
    private val tone=SoundPool.Builder().setMaxStreams(4).setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME).build()).build()
    private var touchId=0
    private var touchReady=false
    private var arrivalId=0
    private var arrivalReady=false
    private var arrivalFinishedLoading=false
    val ready get()=arrivalFinishedLoading
    private var touchVolume=.25f
    private var active=true
    private var closed=false
    init {
        try {
            tone.setOnLoadCompleteListener { _,id,status ->
                if(id==touchId) touchReady=status==0
                if(id==arrivalId) { arrivalReady=status==0; arrivalFinishedLoading=true }
            }
            context.assets.openFd("v3/audio/touch.wav").use { touchId=tone.load(it,1) }
            context.assets.openFd("v3/audio/arrival.wav").use { arrivalId=tone.load(it,1) }
            for(name in listOf("music","stream")) {
                val player=MediaPlayer(); players+=player
                player.setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                val path="v3/audio/$name.wav"
                context.assets.openFd(path).use { player.setDataSource(it.fileDescriptor,it.startOffset,it.length) }
                player.isLooping=true; player.setVolume(0f,0f); player.prepare(); player.start()
            }
        } catch(error: Exception) { close(); throw error }
    }
    fun volume(music: Float,nature: Float,fade: Float) {
        if(closed) return
        touchVolume=nature*.35f
        players.forEachIndexed { i,player -> val level=(if(i==0) music else nature)*fade.coerceIn(0f,1f); player.setVolume(level,level) }
    }
    fun active(value: Boolean) {
        if(closed || active==value) return
        active=value
        players.forEach { if(value) it.start() else it.pause() }
        if(!value) tone.autoPause()
        else tone.autoResume()
    }
    fun touch() { if(!closed && active && touchReady) tone.play(touchId,touchVolume,touchVolume,1,0,1f) }
    fun arrival(x: Float,z: Float) {
        if(closed || !active || !arrivalReady) return
        val pan=(x/kotlin.math.sqrt(x*x+z*z).coerceAtLeast(.1f)).coerceIn(-.8f,.8f)
        val level=(touchVolume*1.8f).coerceAtMost(.7f)
        tone.play(arrivalId,level*kotlin.math.sqrt((1-pan)/2),level*kotlin.math.sqrt((1+pan)/2),2,0,1f)
    }
    override fun close() {
        if(closed) return
        closed=true; players.forEach { runCatching { it.stop() }; it.release() }; players.clear(); tone.release()
    }
}
