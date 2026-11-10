package com.bugworld.app.spatial

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import android.util.Log
import com.bugworld.app.data.Species
import com.bugworld.app.drawing.ArtworkRasterMapper
import com.bugworld.app.drawing.ArtworkTextureMapper
import com.bugworld.app.drawing.Template
import com.bugworld.app.garden.InsectAnimationController
import com.bugworld.app.garden.InsectAnimationFrame
import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.ecs.animation.*
import com.pico.spatial.core.ecs.resource.*
import com.pico.spatial.core.math.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/** Owns approved GLB source hierarchies; instances share geometry but have independent materials and rigs. */
class ModelLibrary(private val context: Context, templates: Map<Species,Template>? = null) : AutoCloseable {
    private val sources = linkedMapOf<String,Entity>()
    private val resources = linkedSetOf<Resource>()
    private val loading = Mutex()
    private var closed = false
    internal val mapper by lazy { templates?.let(::ArtworkTextureMapper) ?: ArtworkTextureMapper(context) }

    suspend fun preload(name: String) = withContext(Dispatchers.Main.immediate) {
        loading.withLock {
            check(!closed) { "Model library is closed" }
            val key = key(name)
            if (key in sources) return@withLock
            val path = "v3/models/$key.glb"
            val loaded = context.assets.openFd(path).use { Entity.loadSuspend(it,ModelFormat.GLTF) }
            val retained=linkedSetOf<Resource>()
            try {
                check(!closed) { "Model library closed during load" }
                loaded.enabled = false
                entities(loaded).forEach { node ->
                    node.components.get<ModelComponent>()?.let { model ->
                        model.mesh?.let { if (it !in resources) retained+=it }
                        model.materials.forEach { if (it !in resources) retained+=it }
                    }
                }
                retained.forEach { it.toGlobal() }
                resources+=retained
                sources[key] = loaded
                Log.i(TAG,"preloaded $path nodes=${entities(loaded).size}")
            } catch (failure: Throwable) {
                loaded.destroy()
                retained.forEach { it.close() }
                throw failure
            }
        }
    }

    internal fun instantiate(name: String): Entity {
        check(!closed) { "Model library is closed" }
        val source = checkNotNull(sources[key(name)]) { "Call ModelLibrary.preload($name) before creating InsectModel" }
        return requireNotNull(source.clone(Entity.CloneOptions(recursive=true,shouldShareMaterialInstance=false))) {
            "Unable to clone approved GLB $name"
        }.apply { enabled=true }
    }

    override fun close() {
        if (closed) return
        closed=true
        sources.values.forEach { it.destroy() }; sources.clear()
        resources.forEach { it.close() }; resources.clear()
    }

    companion object {
        private const val TAG="BugWorldModels"
        internal fun key(name: String): String = name.substringAfterLast('/').removeSuffix(".glb").also { key ->
            require(key=="garden" || Species.entries.any { it.asset==key }) { "Unknown approved GLB: $name" }
        }
        internal fun entities(root: Entity): List<Entity> = buildList {
            fun visit(node: Entity) { add(node); node.getChildren().forEach(::visit) }
            visit(root)
        }
    }
}

class InsectModel(private val library: ModelLibrary, name: String, bitmap: Bitmap? = null) : AutoCloseable {
    private val model=library.instantiate(name)
    val root=Entity()
    private val normalization=Entity()
    private val species=Species.entries.find { it.asset==ModelLibrary.key(name) }
    private var opacity: OpacityControllerComponent?=null
    private var appliedOpacity=1f
    private val painted=linkedMapOf<String,PhysicallyBasedMaterial>()
    private var textures=emptyMap<String,TextureResource>()
    private var textureBitmaps=emptyMap<String,Bitmap>()
    private val previewAnimation=species?.let(::InsectAnimationController)
    private var previousPreviewTime=Float.NaN
    private var closed=false
    private var active=true
    private data class Clip(val owner: Entity,val resource: AnimationResource)
    private val clips=linkedMapOf<String,Clip>()
    private val repeating=linkedMapOf<String,AnimationResource>()
    private var plan: AnimationClipPlan?=null
    private var player: AnimationPlaybackController?=null
    private val retiredPlayers=mutableListOf<AnimationPlaybackController>()
    private var scrubStart=0f
    private var scrubPhase=0f

    init {
        try {
            root.setName("v3/${ModelLibrary.key(name)}")
            root.addChild(normalization); normalization.addChild(model)
            if (species!=null) {
                normalize()
                isolatePaintMaterials(species)
                ModelLibrary.entities(model).forEach { owner ->
                    owner.getAnimationResources().forEach { resource ->
                        // Each reviewed GLB has one rig. Prefer the highest owner over mesh-child aliases.
                        clips.putIfAbsent(resource.getName(),Clip(owner,resource))
                    }
                }
                val missing=AnimationClipPolicy.clipNames(species)-clips.keys
                check(missing.isEmpty()) { "Missing native animation clips for ${species.asset}: $missing; imported=${clips.keys}" }
                Log.i(TAG,"${species.asset} clips=${clips.mapValues { it.value.owner.getName() }} paint=${painted.keys}")
            }
            bitmap?.let(::updateTexture)
        } catch (failure: Throwable) {
            close()
            throw failure
        }
    }

    private fun normalize() {
        val bounds=model.getVisualBounds(relativeTo=normalization,recursive=true,enabledOnly=false)
        val size=bounds.size; val center=bounds.center; val bottom=bounds.min.y
        val span=maxOf(size.x,size.z)
        require(span.isFinite() && span>.00001f && bottom.isFinite()) { "Invalid approved insect bounds: $bounds" }
        val scale=.48f/span
        normalization.components.get<TransformComponent>()!!.apply {
            setScaleVector(Vector3(scale))
            setPosition(Vector3(-center.x*scale,-bottom*scale,-center.z*scale))
        }
    }

    private fun isolatePaintMaterials(species: Species) {
        val eligible=ArtworkRasterMapper.materialMeshes(species)
        ModelLibrary.entities(model).forEach { node ->
            val component=node.components.get<ModelComponent>() ?: return@forEach
            for (index in 0 until component.materials.size) {
                val original=component.materials[index] as? PhysicallyBasedMaterial ?: continue
                val name=original.getName()
                if (node.getName() !in eligible[name].orEmpty()) continue
                val material=painted.getOrPut(name) {
                    // Clone natively to retain imported PBR fields beyond the public setter surface.
                    val temporary=requireNotNull(node.clone(Entity.CloneOptions(recursive=false,shouldShareMaterialInstance=false)))
                    try {
                        temporary.enabled=false
                        val copy=temporary.components.get<ModelComponent>()!!.materials[index] as PhysicallyBasedMaterial
                        copy.toGlobal()
                        copy
                    } finally { temporary.destroy() }
                }
                component.materials[index]=material
            }
        }
        check(painted.keys.containsAll(eligible.keys)) {
            "Missing approved paint meshes/materials for ${species.asset}: ${eligible.keys-painted.keys}"
        }
    }

    /** Compatibility entry point. Prefer updateTextureSuspend so projection work stays off the UI thread. */
    fun updateTexture(bitmap: Bitmap) {
        check(!closed)
        val species=species ?: return
        applyMapped(library.mapper.map(species,bitmap))
    }

    suspend fun updateTextureSuspend(bitmap: Bitmap) {
        check(!closed)
        val species=species ?: return
        val started=SystemClock.elapsedRealtime()
        val input=requireNotNull(bitmap.copy(Bitmap.Config.ARGB_8888,false))
        var mapped=emptyMap<String,Bitmap>()
        try {
            withContext(Dispatchers.Default) { mapped=library.mapper.map(species,input) }
            val mappedAt=SystemClock.elapsedRealtime()
            withContext(Dispatchers.Main.immediate) {
                check(!closed) { "Model closed while preparing artwork" }
                applyMapped(mapped)
                mapped=emptyMap()
                Log.d(TAG,"paint asset=${species.asset} copy_map_ms=${mappedAt-started} upload_ms=${SystemClock.elapsedRealtime()-mappedAt}")
            }
        } finally {
            input.recycle()
            mapped.values.forEach { if (!it.isRecycled) it.recycle() }
        }
    }

    private fun applyMapped(bitmaps: Map<String,Bitmap>) {
        val next=linkedMapOf<String,TextureResource>()
        try {
            check(bitmaps.keys==painted.keys) { "Artwork material bindings do not match the imported GLB" }
            bitmaps.forEach { (name,bitmap) -> next[name]=TextureResource.create(bitmap).apply { toGlobal() } }
            next.forEach { (name,texture) -> painted.getValue(name).apply {
                setBaseColor(Color4(1f,1f,1f,1f))
                setBaseColorTexture(texture)
            } }
        } catch (failure: Throwable) {
            next.values.forEach { it.close() }
            bitmaps.values.forEach { if (!it.isRecycled) it.recycle() }
            throw failure
        }
        val oldTextures=textures; val oldBitmaps=textureBitmaps
        textures=next; textureBitmaps=bitmaps
        oldTextures.values.forEach { it.close() }
        oldBitmaps.values.forEach { it.recycle() }
    }

    fun pose(x: Float,y: Float,z: Float,yaw: Float=0f,scale: Float=1f,pitch: Float=0f,roll: Float=0f) {
        root.components.get<TransformComponent>()?.apply {
            setPosition(Vector3(x,y,z)); setEulerAngles(EulerAngles(pitch,yaw,roll)); setScaleVector(Vector3(scale))
        }
    }

    fun animate(time: Float,flying: Boolean=false,open: Boolean=false,reaction: Float=0f) {
        if (closed || !active) return
        val controller=previewAnimation ?: return
        val delta=if (previousPreviewTime.isFinite() && time.isFinite()) (time-previousPreviewTime).coerceIn(0f,.1f) else 0f
        previousPreviewTime=time
        animate(controller.update(delta,flying=flying,open=open,reaction=reaction))
    }

    fun animate(frame: InsectAnimationFrame) {
        if (species==null || closed) return
        require(frame.species==species)
        val desired=AnimationClipPolicy.select(frame)
        if (desired!=plan) {
            val clip=clips.getValue(desired.name)
            scrubStart=if (plan?.name==desired.name && plan?.scrub==true && desired.scrub) scrubPhase else if (desired.reverse) 1f else 0f
            val previous=player
            val transition=if (active) desired.transitionSeconds else 0f
            if (transition==0f) previous?.stop()
            val resource=if (desired.loop) repeating.getOrPut(desired.name) {
                clip.resource.repeat(SpatialAnimation.INFINITE).apply { toGlobal() }
            } else clip.resource
            player=clip.owner.playAnimation(resource,AnimationPlayConfig(
                transitionDuration=transition,
                transitionMode=if (transition>0f) AnimationTransitionMode.CROSSFADE else AnimationTransitionMode.STOP_AND_CROSSFADE,
                blendLayer=0,blendWeight=1f))
            if (previous!=null) {
                if (transition==0f) previous.close() else retiredPlayers+=previous
            }
            plan=desired
            if (!active || desired.scrub || desired.freeze) player?.pause()
        }
        if (!active) return
        val current=player ?: return
        if (desired.scrub || desired.freeze) {
            scrubPhase=desired.phase(frame.progress,scrubStart)
            val duration=current.getDuration()
            if (duration.isFinite() && duration>0f) current.setTime(duration*scrubPhase)
        } else {
            val speed = if (frame.motion>.01f) frame.motion.coerceIn(.25f,2f) else 1f
            current.setSpeed(if (species == Species.DRAGONFLY && desired.name == "flight") speed * 2.5f else speed)
        }
        retiredPlayers.removeAll { old ->
            if (old.isStopped() || old.isComplete()) { old.close(); true } else false
        }
    }

    fun opacity(value: Float) {
        val next=value.coerceIn(0f,1f)
        if(next==appliedOpacity) return
        // Keep the normal opaque hierarchy free of an inherited opacity override.
        // A fresh controller belongs only to the current arrival/departure fade.
        if(next==1f) {
            root.components.remove(OpacityControllerComponent::class.java)
            opacity=null
        } else {
            val controller=opacity
            if(controller==null) {
                opacity=OpacityControllerComponent(next).also { root.components.set(it) }
            } else controller.opacity=next
        }
        appliedOpacity=next
    }

    /** Native clips have their own clock, so visibility/lifecycle changes must pause them explicitly. */
    fun setActive(active: Boolean) {
        if (closed || this.active==active) return
        this.active=active
        previousPreviewTime=Float.NaN
        if (active && plan?.loop==true) player?.resume() else player?.pause()
        if (!active) {
            // A hidden scene needs no pending fade; leave just the current frozen pose to resume.
            retiredPlayers.forEach { it.stop(); it.close() }
            retiredPlayers.clear()
        }
    }

    override fun close() {
        if (closed) return
        closed=true
        player?.let { it.stop(); it.close() }; player=null
        retiredPlayers.forEach { it.stop(); it.close() }; retiredPlayers.clear()
        clips.values.map { it.owner }.distinctBy { it.id }.forEach { it.stopAllAnimations() }
        root.destroy()
        repeating.values.forEach { it.close() }; repeating.clear()
        painted.values.forEach { it.close() }; painted.clear()
        textures.values.forEach { it.close() }; textures=emptyMap()
        textureBitmaps.values.forEach { if (!it.isRecycled) it.recycle() }; textureBitmaps=emptyMap()
    }

    companion object { private const val TAG="BugWorldModels" }
}
