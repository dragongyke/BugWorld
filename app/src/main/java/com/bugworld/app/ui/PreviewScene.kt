package com.bugworld.app.ui

import android.os.SystemClock
import android.util.Log
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.*
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import com.bugworld.app.R
import com.bugworld.app.BugWorldState
import com.bugworld.app.data.Species
import com.bugworld.app.spatial.*
import com.pico.spatial.core.container.SpatialViewContent
import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.ecs.resource.*
import com.pico.spatial.core.math.*
import com.pico.spatial.ui.design.Text
import com.pico.spatial.ui.foundation.content.SpatialView
import com.pico.spatial.ui.foundation.gesture.*
import com.pico.spatial.ui.foundation.gesture.data.InteractionKind
import com.pico.spatial.ui.platform.LocalSpatialContainerStateManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.abs

private const val PREVIEW_TAG="BugWorldPreview"

/** Paper and insect share one native hit tree; tools use the window's native side augment. */
@Composable fun StudioScene(state: BugWorldState, visible: Boolean,
    closePreview: ()->Unit, board: @Composable ()->Unit) {
    val lifecycle=LocalLifecycleOwner.current.lifecycle
    var surfaceMayAttach by remember(lifecycle) {
        mutableStateOf(lifecycle.currentState==Lifecycle.State.RESUMED)
    }
    DisposableEffect(lifecycle) {
        val observer=LifecycleEventObserver { _,event ->
            // A cold launch can compose while CREATED. SDK 6.1.0 disables the
            // SpatialView root then; an attachment created in that interval can
            // remain invisible after the native window becomes visible.
            if(event==Lifecycle.Event.ON_RESUME) surfaceMayAttach=true
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    var attempt by remember { mutableIntStateOf(0) }
    if(surfaceMayAttach) key(attempt) { PreviewContent(state,visible,closePreview,board) { attempt++ } }
    else board()
}

@Composable private fun PreviewContent(state: BugWorldState, visible: Boolean,
    close: ()->Unit, board: @Composable ()->Unit, retry: ()->Unit) {
    var runtime by remember { mutableStateOf<PreviewRuntime?>(null) }
    var error by remember { mutableStateOf<Int?>(null) }
    var loading by remember { mutableStateOf(false) }
    var viewSize by remember { mutableStateOf(IntSize.Zero) }
    val paperDiagnostics=remember { intArrayOf(0) }
    val paperRef=remember { arrayOfNulls<Entity>(1) }
    val disposed=remember { AtomicBoolean(false) }
    val density=LocalDensity.current
    val paperSize=if(viewSize.width>0 && viewSize.height>0) viewSize else with(density) { IntSize(1050.dp.roundToPx(),840.dp.roundToPx()) }
    val context=LocalContext.current
    val lifecycle=LocalLifecycleOwner.current.lifecycle
    var active by remember(lifecycle) { mutableStateOf(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) }
    val onstage=LocalSpatialContainerStateManager.current.isOnstage.value
    DisposableEffect(state,visible,active,onstage) {
        state.previewActive=visible && active && onstage
        onDispose { state.previewActive=false }
    }
    val fail: (Throwable)->Unit = { failure ->
        Log.e(PREVIEW_TAG,"preview failed asset=${state.previewAsset} revision=${state.previewRevision}",failure)
        error=R.string.preview_error; loading=false
        if(visible) state.report(R.string.preview_failed)
    }
    Box(Modifier.fillMaxSize()) {
        SpatialView(modifier=Modifier.fillMaxSize().onSizeChanged { viewSize=it }
            .then(if(visible && active && onstage && error==null) Modifier.pointerInput(runtime,density) {
                val scene=runtime
                if(scene!=null && visible && active && onstage && error==null) {
                    try {
                        // Native entity input supports direct poke and pinch in Shared Space.
                        // Only the insect collision entity can consume a paper-window event.
                        detectSpatialPointerEvent(context=context,
                            targetedToEntity=TargetEntity.any { scene.ownsHit(it) }) { events ->
                            scene.pointer(events)
                        }
                    } finally { scene.cancelGesture() }
                }
            } else Modifier),
            attachments={
                // The SDK caches the explicit size by id. Wrap content allows native remeasurement on resize.
                AttachmentPanel(id="studio-paper") {
                    Box(Modifier.requiredSize(with(density) { paperSize.width.toDp() },with(density) { paperSize.height.toDp() })) { board() }
                }
            },
            update={ content,attachments ->
                fun position(id: String,x: Float,y: Float,enabled: Boolean=true) {
                    attachments.entity(id)?.apply {
                        this.enabled=enabled
                        val position=content.convertPosition(Vector3(x,y,with(density) { 1.dp.toPx() }),
                            ViewCoordinateSpace.Local,content.localSpatialCoordinateSpace)
                        components[TransformComponent::class.java]?.setPosition(position)
                        if(paperDiagnostics[0]++<16) Log.i(PREVIEW_TAG,
                            "paper update id=${this.id} parent=${getParent()?.id}/${getParent()?.enabled} valid=$valid enabled=$enabled size=$viewSize position=$position active=$active lifecycle=${lifecycle.currentState} onstage=$onstage")
                    }
                }
                position("studio-paper",paperSize.width*.5f,paperSize.height*.5f)
            },
            initial={ content,attachments ->
                // Native AttachmentPanel dispatches 2D input directly to its Android/Compose content.
                listOf("studio-paper").forEach { id ->
                    val paper=attachments.entity(id)
                    paperRef[0]=paper
                    Log.i(PREVIEW_TAG,"paper initial id=${paper?.id} size=$viewSize active=$active onstage=$onstage")
                    paper?.let { content.addEntity(it) }
                }
                var created: PreviewRuntime?=null
                try {
                    created=PreviewRuntime(state,content)
                    if(disposed.get()) { created.close(); return@SpatialView }
                    runtime=created
                    Log.i(PREVIEW_TAG,"attached studio paper; tools owned by right Subwindow augment")
                } catch(failure: Exception) {
                    created?.close()
                    if(failure is CancellationException) throw failure
                    fail(failure)
                }
            })
        if(visible && error==null) {
            Text(stringResource(if(loading) R.string.preview_waking else R.string.preview_gesture),
                color=Ink,fontSize=14.sp,modifier=Modifier.align(Alignment.BottomCenter).padding(bottom=92.dp)
                    .clip(RoundedCornerShape(12.dp)).background(Panel.copy(alpha=.92f)).padding(8.dp))
        }
        if(visible && error!=null) {
            Row(Modifier.align(Alignment.TopCenter).padding(top=76.dp).clip(RoundedCornerShape(18.dp)).background(Panel).padding(12.dp),
                verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                Text(stringResource(error!!),color=Ink,fontSize=17.sp)
                Action(stringResource(R.string.retry),click=retry); IconButton(stringResource(R.string.close_preview),"close",click=close)
            }
        }
    }
    LaunchedEffect(Unit) {
        delay(8000)
        if(runtime==null && !disposed.get() && error==null) fail(IllegalStateException("SpatialView attachment timeout"))
    }
    var warmAsset by remember(state.species) { mutableStateOf("v3/${state.species.asset}") }
    val requestedAsset=if(visible) state.previewAsset else warmAsset
    // Visibility is deliberately NOT a key: opening the preview must join an
    // in-flight warm load instead of cancelling and parsing the same GLB again.
    LaunchedEffect(runtime,active,onstage,state.ready,requestedAsset) {
        val scene=runtime ?: return@LaunchedEffect
        if(error!=null || !state.ready || !active || !onstage) return@LaunchedEffect
        try {
            // Rapid paper browsing must not repeatedly start native GLB imports.
            if(!visible) delay(1000)
            scene.prepareArtwork(requestedAsset,null,-1)
        } catch(failure: Exception) {
            if(failure is CancellationException) throw failure
            scene.close(); runtime=null; fail(failure)
        }
    }
    LaunchedEffect(runtime,visible,active,onstage,state.ready,requestedAsset,state.previewRevision) {
        val scene=runtime ?: return@LaunchedEffect
        if(error!=null || !visible || !state.ready || !active || !onstage) return@LaunchedEffect
        try {
            loading=true
            val bitmap=state.previewBitmap
            if(bitmap==null) { close(); return@LaunchedEffect }
            warmAsset=requestedAsset
            scene.prepareArtwork(requestedAsset,bitmap,state.previewRevision)
            loading=false
        } catch(failure: Exception) {
            if(failure is CancellationException) throw failure
            scene.close(); runtime=null; fail(failure)
        }
    }
    LaunchedEffect(runtime,visible,active,onstage,error) {
        val scene=runtime ?: return@LaunchedEffect
        var previous=0L
        try {
            val running=visible && active && onstage && error==null
            scene.active(running)
            if(!running) return@LaunchedEffect
            while(true) withFrameNanos { now ->
                val dt=if(previous==0L) 0f else ((now-previous)/1_000_000_000f).coerceIn(0f,.05f)
                previous=now; scene.frame(dt,viewSize,density)
            }
        } catch(failure: Exception) {
            if(failure is CancellationException) throw failure
            scene.close(); runtime=null; fail(failure)
        }
    }
    DisposableEffect(lifecycle) {
        val observer=LifecycleEventObserver { _,event ->
            if(event==Lifecycle.Event.ON_RESUME || event==Lifecycle.Event.ON_PAUSE) {
                active=event==Lifecycle.Event.ON_RESUME
                if(!active) runtime?.active(false)
            }
            paperRef[0]?.let { paper ->
                Log.i(PREVIEW_TAG,"paper lifecycle event=$event state=${lifecycle.currentState} ancestors="+
                    generateSequence(paper) { it.getParent() }.take(6).joinToString { "${it.id}/${it.enabled}" })
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    DisposableEffect(Unit) {
        onDispose {
            disposed.set(true); runtime?.close(); runtime=null
            Log.i(PREVIEW_TAG,"disposed preview resources")
        }
    }
}

private class PreviewRuntime(private val state: BugWorldState,private val content: SpatialViewContent) : AutoCloseable {
    private val root=Entity()
    private val pivot=Entity()
    private var lighting: SceneLighting?=null
    private var library: ModelLibrary?=null
    private var model: InsectModel?=null
    private var hit: Entity?=null
    private val hitResources=mutableListOf<Resource>()
    private var asset: String?=null
    private var paintedRevision=-1
    private var span=.6f
    private var motion: PreviewMotion?=null
    private var active=false
    private var closed=false
    private var interaction=PreviewInteraction()
    private var showStarted=0L
    private var firstFrame=false
    private val preparation=Mutex()
    init {
        try {
            root.enabled=false
            check(root.addChild(pivot))
            content.addEntity(root)
        } catch(failure: Throwable) {
            root.destroy(); throw failure
        }
    }
    suspend fun prepareArtwork(requestedAsset: String,bitmap: android.graphics.Bitmap?,revision: Int) = preparation.withLock {
        prepare(requestedAsset)
        if(bitmap!=null) updateArtwork(bitmap,revision)
    }
    private suspend fun prepare(requestedAsset: String) {
        check(!closed)
        if(model!=null && asset==requestedAsset) return
        // One cached insect, never four large models plus the Stage at once.
        releaseModel()
        val nextLibrary=ModelLibrary(state.app,state.templates)
        var next: InsectModel?=null
        val started=SystemClock.elapsedRealtime()
        try {
            nextLibrary.preload(requestedAsset)
            currentCoroutineContext().ensureActive()
            check(!closed)
            val loadedAt=SystemClock.elapsedRealtime()
            next=InsectModel(nextLibrary,requestedAsset,null)
            next.setActive(false)
            val bounds=next.root.getVisualBounds(relativeTo=next.root,recursive=true,enabledOnly=false)
            val size=bounds.size
            span=maxOf(size.x,size.y,size.z)
            check(span.isFinite() && span>.001f) { "Invalid preview model extent: $size" }
            val shape=ShapeResource.createBox(Vector3(maxOf(size.x,.06f),maxOf(size.y,.06f),maxOf(size.z,.06f)))
                .also { it.toGlobal(); hitResources+=it }
            val material=PhysicsMaterialResource().also { it.toGlobal(); hitResources+=it }
            hit=Entity().also { target ->
                next.root.addChild(target)
                target.components.get<TransformComponent>()!!.setPosition(bounds.center)
                target.components.set(InteractableComponent())
                target.components.set(CollisionComponent(collisionShape=listOf(shape),physicsMaterial=material))
            }
            next.root.enabled=false
            // The model origin is at its feet. Center the child once so the fixed pivot is
            // also the visual center when the user rolls the insect through 180 degrees.
            next.root.components.get<TransformComponent>()!!.setPosition(-bounds.center)
            check(pivot.addChild(next.root))
            model=next; library=nextLibrary; asset=requestedAsset
            interaction=PreviewInteraction()
            motion=PreviewMotion(Species.entries.first { it.asset==ModelLibrary.key(requestedAsset) })
            Log.i(PREVIEW_TAG,"prepared asset=$asset load_ms=${loadedAt-started} instance_ms=${SystemClock.elapsedRealtime()-loadedAt}")
        } catch(failure: Throwable) {
            next?.close(); nextLibrary.close()
            hit=null; hitResources.forEach { it.close() }; hitResources.clear()
            throw failure
        }
    }
    private suspend fun updateArtwork(bitmap: android.graphics.Bitmap,revision: Int) {
        check(!closed)
        if(paintedRevision==revision) { Log.i(PREVIEW_TAG,"reuse asset=$asset revision=$revision"); return }
        val next=checkNotNull(model)
        val started=SystemClock.elapsedRealtime()
        next.updateTextureSuspend(bitmap)
        currentCoroutineContext().ensureActive()
        check(!closed)
        paintedRevision=revision
        Log.i(PREVIEW_TAG,"colors asset=$asset revision=$revision map_upload_ms=${SystemClock.elapsedRealtime()-started}")
    }
    fun ownsHit(entity: Entity)=active && !closed && root.enabled && hit?.id==entity.id
    fun pointer(events: List<SpatialPointerInfo>): Boolean {
        if(!active || closed || !root.enabled) return false
        interaction.releaseMissing(events.map { it.pointerId.value })
        for(event in events) {
            val id=event.pointerId.value
            val poke=event.kind==InteractionKind.Poke
            val pinch=event.kind==InteractionKind.DirectPinch || event.kind==InteractionKind.GazePinch ||
                event.kind==InteractionKind.RayBasedPinch
            if(event.isUpEvent()) { interaction.up(id,event.uptimeMillis); continue }
            val hand=if(pinch) {
                val pose=event.inputDevicePose
                if(pose==com.pico.spatial.ui.foundation.gesture.data.InputDevicePose.identity()) null
                else content.convertRotation(pose.rawRotation.toQuaternion(),ViewCoordinateSpace.Global,
                    content.localSpatialCoordinateSpace)
            } else null
            when {
                event.isDownEvent() && (poke || pinch) -> interaction.down(id,hand,event.uptimeMillis,poke)
                event.pressed -> interaction.sample(id,hand,event.uptimeMillis)
            }
        }
        return events.isNotEmpty()
    }
    fun cancelGesture()=interaction.cancel()
    fun frame(dt: Float,size: IntSize,density: Density) {
        if(closed || !active || paintedRevision<0 || size.width==0 || size.height==0) return
        val current=model ?: return
        // A hidden preview must not retain native light/shadow resources during Full Stage.
        if(lighting==null) lighting=SceneLighting(root)
        val origin=content.convertPosition(Vector3(size.width*.5f,size.height*.43f,with(density) { 240.dp.toPx() }),
            ViewCoordinateSpace.Local,content.localSpatialCoordinateSpace)
        val wanted=content.convertSize(Vector3(with(density) { 300.dp.toPx() },0f,0f),ViewCoordinateSpace.Local,content.localSpatialCoordinateSpace)
        pivot.components.get<TransformComponent>()!!.apply {
            setPosition(origin); setScaleVector(Vector3(abs(wanted.x)/span))
            setQuaternion(interaction.orientation)
        }
        current.setActive(true)
        current.animate(checkNotNull(motion).update(dt,interaction.takeReaction()>0f))
        current.root.enabled=true; root.enabled=true
        if(!firstFrame) {
            firstFrame=true
            Log.i(PREVIEW_TAG,"first_frame_submitted asset=$asset show_to_submit_ms=${SystemClock.elapsedRealtime()-showStarted}")
        }
    }
    fun active(value: Boolean) {
        if(closed) return
        if(value && !active) { showStarted=SystemClock.elapsedRealtime(); firstFrame=false }
        active=value
        if(!value) {
            root.enabled=false; interaction.cancel()
            lighting?.close(); lighting=null
        }
        model?.setActive(value && paintedRevision>=0)
    }
    private fun releaseModel() {
        root.enabled=false
        lighting?.close(); lighting=null
        interaction.cancel()
        model?.close(); model=null; hit=null; motion=null
        hitResources.forEach { it.close() }; hitResources.clear()
        library?.close(); library=null; asset=null; paintedRevision=-1
    }
    override fun close() {
        if(closed) return
        closed=true
        releaseModel()
        content.removeEntity(root); root.destroy()
    }
}
