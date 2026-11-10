package com.bugworld.app.ui

import androidx.compose.foundation.background
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.input.pointer.pointerInput
import com.pico.spatial.ui.foundation.gesture.*
import com.pico.spatial.ui.foundation.gesture.data.InteractionKind
import com.pico.spatial.core.ecs.resource.*
import androidx.compose.ui.unit.*
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import com.bugworld.app.R
import com.bugworld.app.labelRes
import com.bugworld.app.BugWorldState
import com.bugworld.app.garden.GardenRuntime
import com.bugworld.app.garden.StageDiagnostics
import com.bugworld.app.garden.StageFrameStats
import com.bugworld.app.interaction.HandTrackingSession
import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.math.*
import com.pico.spatial.ui.design.Text
import com.pico.spatial.ui.foundation.content.SpatialView
import com.pico.spatial.ui.platform.LocalSpatialContainerStateManager
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay
import kotlinx.coroutines.CancellationException
import java.util.concurrent.atomic.AtomicBoolean

@Composable fun GardenScene(state: BugWorldState,onReady: ()->Unit = {},exit: (onFailed: ()->Unit)->Unit) {
    var runtime by remember { mutableStateOf<GardenRuntime?>(null) }
    val interactionCue=runtime?.interactionCue
    val disposed=remember { AtomicBoolean(false) }
    val coroutine=rememberCoroutineScope()
    var hands by remember { mutableStateOf<HandTrackingSession?>(null) }
    val lifecycle=LocalLifecycleOwner.current.lifecycle
    var active by remember(lifecycle) { mutableStateOf(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) }
    var exiting by remember { mutableStateOf(false) }
    var loadError by remember { mutableStateOf<Int?>(null) }
    val containerState=LocalSpatialContainerStateManager.current
    val visible by rememberUpdatedState(containerState.isOnstage.value)
    val readyCallback by rememberUpdatedState(onReady)
    val context=LocalContext.current
    val preferences=remember(context) { context.getSharedPreferences("garden-guide",0) }
    var showGuide by remember { mutableStateOf(false) }
    val guideAlpha by animateFloatAsState(if(showGuide) 1f else 0f,tween(400),label="garden guide")
    LaunchedEffect(state.sceneReady) {
        if(state.sceneReady && !preferences.getBoolean("gesture-response-guide",false)) {
            showGuide=true
            preferences.edit().putBoolean("gesture-response-guide",true).apply()
            delay(8500)
            showGuide=false
        }
    }
    val panelSize=with(LocalDensity.current) { IntSize(200.dp.roundToPx(),144.dp.roundToPx()) }
    val cueSize=with(LocalDensity.current) { IntSize(288.dp.roundToPx(),88.dp.roundToPx()) }
    val leave: ()->Unit = {
        if(!exiting) { exiting=true; state.cancelPendingRelease(); coroutine.launch {
            runtime?.fadeOut(); exit { exiting=false; runtime?.cancelExitFade() }
        } }
    }
    val leaveCurrent by rememberUpdatedState(leave)
    val orbResources=remember { mutableListOf<Resource>() }

    SpatialView(modifier=Modifier.fillMaxSize().pointerInput(runtime,active,visible,exiting) {
        val garden=runtime
        if(garden!=null && active && visible && !exiting) detectSpatialPointerEvent(context=context,
            targetedToEntity=TargetEntity.any { garden.ownsHit(it) }) { events ->
            events.forEach { event ->
                val poke=event.kind==InteractionKind.Poke
                val pinch=event.kind==InteractionKind.DirectPinch || event.kind==InteractionKind.GazePinch ||
                    event.kind==InteractionKind.RayBasedPinch
                if(event.isDownEvent() && (poke || pinch)) event.targetedEntity?.let {
                    garden.interact(it,poke,hands?.pinchingSide)
                }
            }
            events.isNotEmpty()
        }
    },
        attachments={
            AttachmentPanel(id="garden-return",size=panelSize) { GardenReturnOrb(!exiting) { leaveCurrent() } }
            AttachmentPanel(id="garden-interaction",size=cueSize) {
                interactionCue?.let { cue ->
                    Column(Modifier.fillMaxSize().background(androidx.compose.ui.graphics.Color(0xE630273F),RoundedCornerShape(16.dp)).padding(10.dp),
                        horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center) {
                        val title=cue.species?.let { stringResource(cue.title,stringResource(it.labelRes)) } ?: stringResource(cue.title)
                        Text(title,color=androidx.compose.ui.graphics.Color.White,fontSize=16.sp,textAlign=TextAlign.Center)
                        Text(stringResource(cue.instruction),color=Lavender,fontSize=14.sp,textAlign=TextAlign.Center)
                    }
                }
            }
            AttachmentPanel(id="garden-status") {
                if(loadError!=null || !state.sceneReady) Column(Modifier.background(Night.copy(alpha=.88f)).padding(18.dp)) {
                    Text(stringResource(loadError ?: R.string.garden_preparing),color=Muted,fontSize=17.sp)
                    Action(stringResource(R.string.return_canvas),enabled=!exiting) { leaveCurrent() }
                } else if(guideAlpha>0f) Column(Modifier.alpha(guideAlpha).background(androidx.compose.ui.graphics.Color(0xD930273F),RoundedCornerShape(16.dp)).padding(14.dp)) {
                    Text(stringResource(R.string.guide_greet),color=androidx.compose.ui.graphics.Color.White,fontSize=15.sp)
                    Text(stringResource(R.string.guide_invite),color=androidx.compose.ui.graphics.Color.White,fontSize=15.sp)
                    Text(stringResource(R.string.guide_return),color=Muted,fontSize=14.sp)
                }
            }
        },
        update={ _,attachments -> attachments.entity("garden-status")?.enabled=loadError!=null || !state.sceneReady || guideAlpha>0f },
        initial={ content,attachments ->
            try {
                val garden=GardenRuntime(state)
                if(disposed.get()) { garden.close(); return@SpatialView }
                runtime=garden; content.addEntity(garden.root)
            } catch(error: Exception) {
                loadError=R.string.garden_open_error
                state.cancelPendingRelease(); state.report(loadError!!)
                android.util.Log.e("BugWorldGarden","Scene preparation failed",error)
            }
            runCatching { HandTrackingSession(coroutine) }.onSuccess { hands=it }
                .onFailure { state.report(R.string.tracking_unavailable) }
            attachments.entity("garden-return")?.let { entity ->
                entity.components.get<TransformComponent>()?.setPosition(Vector3(-.52f,1.03f,-.67f))
                val lookAt=LookAtComponent().apply { alignLocalUpToWorldUp=false;lookAtForwardDirection=LookAtForwardDirection.POSITIVE_Z }
                entity.components.set(lookAt)
                runtime?.root?.addChild(entity) ?: content.addEntity(entity)
                lookAt.setViewerAsTarget()
            }
            // Real PBR sphere remains fixed in the garden; transparent attachment supplies accessible input and gaze label.
            runtime?.root?.let { root ->
                val mesh=MeshResource.createSphere(.05f).also { it.toGlobal();orbResources+=it }
                val material=PhysicallyBasedMaterial.create().also { it.toGlobal();orbResources+=it }.apply {
                    setBaseColor(Color4(.42f,.66f,.47f,1f));setRoughness(.52f);setMetallic(0f)
                }
                root.addChild(Entity().apply {
                    setName("ReturnToCanvasOrb");components.set(ModelComponent(mesh,material))
                    components.get<TransformComponent>()?.setPosition(Vector3(-.52f,1.00f,-.72f))
                })
            }
            attachments.entity("garden-status")?.let {
                it.components.get<TransformComponent>()?.setPosition(Vector3(0f,1.2f,-1.25f));content.addEntity(it)
            }
            attachments.entity("garden-interaction")?.let { entity ->
                entity.enabled=false
                runtime?.attachInteractionCue(entity)
            }
        })
    LaunchedEffect(runtime,state.gardenWorks,state.pendingRelease) {
        val garden=runtime ?: return@LaunchedEffect
        if(loadError!=null) return@LaunchedEffect
        try { StageDiagnostics.awaitPhase("prepare_total") { garden.prepare() } }
        catch(error: Exception) {
            if(error is CancellationException) throw error
            loadError=R.string.garden_load_error
            state.cancelPendingRelease(); state.report(loadError!!)
            android.util.Log.e("BugWorldGarden","GLB preparation failed",error)
        }
    }
    LaunchedEffect(runtime,hands,active,visible,exiting) {
        runtime?.active(active && visible)
        runCatching { hands?.active(active && visible && !exiting) }.onFailure {
            android.util.Log.e("BugWorldGarden","Hand tracking start/stop failed",it)
            state.report(R.string.tracking_unavailable)
        }
    }
    LaunchedEffect(runtime,loadError) {
        val garden=runtime ?: return@LaunchedEffect
        if(loadError!=null) return@LaunchedEffect
        var previous=0L
        val frameStats=StageFrameStats()
        try { while(true) withFrameNanos { now ->
            val measureFrame=active && visible && !exiting
            val interval=if(previous==0L || !measureFrame) 0L else now-previous
            val delta=(interval/1_000_000_000f).coerceIn(0f,.05f)
            previous=if(measureFrame) now else 0L
            if(!measureFrame) frameStats.reset()
            val start=java.lang.System.nanoTime()
            val cpu=android.os.Debug.threadCpuTimeNanos()
            android.os.Trace.beginSection("BugWorldStage:tick")
            try { if(active) {
                val head=hands?.headPose
                head?.let { garden.placeAt(it.position,it.rotation.rotateVector(Vector3(0f,0f,-1f))) }
                garden.tick(delta,hands?.hands.orEmpty(),head?.position,visible && !exiting,readyCallback)
            } }
            finally {
                android.os.Trace.endSection()
                if(interval>0L) frameStats.record(interval,java.lang.System.nanoTime()-start,
                    android.os.Debug.threadCpuTimeNanos()-cpu)?.let(StageDiagnostics::frames)
            }
        } } catch(error: Exception) {
            if(error is CancellationException) throw error
            loadError=R.string.garden_display_error
            state.cancelPendingRelease(); state.report(loadError!!)
            android.util.Log.e("BugWorldGarden","Frame failed",error)
        }
    }
    DisposableEffect(lifecycle) {
        val observer=LifecycleEventObserver { _,event ->
            if(event==Lifecycle.Event.ON_RESUME || event==Lifecycle.Event.ON_PAUSE) {
                active=event==Lifecycle.Event.ON_RESUME
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    DisposableEffect(Unit) { onDispose { disposed.set(true); hands?.close(); runtime?.close(); orbResources.asReversed().forEach { it.close() }; orbResources.clear(); hands=null; runtime=null } }
}
