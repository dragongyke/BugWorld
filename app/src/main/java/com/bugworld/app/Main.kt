package com.bugworld.app

import android.util.Log
import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.pico.spatial.ui.design.PicoTheme
import com.pico.spatial.ui.design.windows.Subwindow
import com.pico.spatial.ui.design.windows.SubwindowPlacement
import com.pico.spatial.ui.foundation.geometry.NormalizedPoint3D
import com.pico.spatial.ui.foundation.geometry.Rotation3D
import com.pico.spatial.ui.foundation.geometry.RotationAxis3D
import com.pico.spatial.ui.foundation.dsl.*
import com.pico.spatial.ui.platform.containers.*
import com.pico.spatial.ui.platform.LocalSpatialContainerStateManager
import com.bugworld.app.platform.SpatialApplication
import com.bugworld.app.ui.*
import kotlinx.coroutines.*

const val STUDIO_ID = "BugWorldStudio"
const val ALBUM_ID = "BugWorldAlbum"
const val GARDEN_ID = "BugWorldGarden"
private const val WINDOW_INSTANCE = "workspace"
private const val WINDOW_TAG = "BugWorldWindows"

fun mainApp(scope: SpatialAppScope) = with(scope) {
    val state=(context.applicationContext as SpatialApplication).state
    val session=WorkspaceSession(state)
    DefaultWindowContainer {
        PicoTheme {
            val navigator=LocalSpatialNavigator.current
            BindWindow(session,STUDIO_ID)
            if(!session.inGarden) SpeciesBar(state,session.isOpen(ALBUM_ID),
                openCanvas={ session.open(STUDIO_ID,navigator) },
                album={ if(session.isOpen(ALBUM_ID)) session.close(ALBUM_ID,navigator) else session.open(ALBUM_ID,navigator) })
            if(!session.inGarden && session.toolsVisible) Subwindow(
                placement=SubwindowPlacement.Right,
                rotation3D=Rotation3D(degree=25f,axis=-RotationAxis3D.Y,pivot=NormalizedPoint3D.Left)
            ) {
                // Subwindow has a fixed native width; fill it to avoid exposed material at its edge.
                ToolScreen(state) { session.toolsVisible=false }
            }
            if(!session.inGarden) StudioScene(state,session.previewVisible,
                closePreview={session.previewVisible=false},
                board={ CanvasScreen(state,
                    previewVisible=session.previewVisible,
                    hidePreview={ session.previewVisible=false },
                    preview={ session.showPreview(navigator) },
                    enterGarden={ session.enterGarden(navigator) },
                    tools={ session.toolsVisible=!session.toolsVisible },
                    close={ session.close(STUDIO_ID,navigator) })
                })
        }
    }
    WindowContainer(id=ALBUM_ID,form=Form.Planar,defaultSize=WindowContainerSize(400.dp,740.dp),enableMaterialBackground=false,
        placement={ containers.firstOrNull { it.id==STUDIO_ID }?.let { Placement.left(it,36.dp) } ?: Placement.none() }) {
        PicoTheme {
            val navigator=LocalSpatialNavigator.current
            BindWindow(session,ALBUM_ID)
            if (!session.inGarden) AlbumScreen(state,session.selectedArtworkId,{session.selectedArtworkId=it},
                preview={ session.showPreview(navigator) },enterGarden={session.enterGarden(navigator)},
                editDone={session.resumeEditing(navigator)},newPaper={session.open(STUDIO_ID,navigator)},close={session.close(ALBUM_ID,navigator)})
        }
    }
    Stage(id=GARDEN_ID,immersion=Immersion(default=100,min=100,max=100)) {
        PicoTheme {
            val navigator=LocalSpatialNavigator.current
            val onstage = LocalSpatialContainerStateManager.current.isOnstage.value
            LaunchedEffect(onstage) {
                if (onstage) session.stageVisible(navigator)
                else session.stageHidden(navigator)
            }
            DisposableEffect(Unit) {
                Log.i(WINDOW_TAG,"Stage composition attached; waiting for rendered scene")
                onDispose { session.stageDetached(navigator) }
            }
            GardenScene(state,exit={failed -> session.leaveGarden(navigator,failed)})
        }
    }
}

@Composable private fun BindWindow(session: WorkspaceSession,id: String) {
    val navigator=LocalSpatialNavigator.current
    val activity=LocalContext.current.hostActivity()
    DisposableEffect(session,id) {
        session.attached(id,navigator)
        onDispose { session.detached(id,userClosed=activity?.isFinishing==true && !activity.isChangingConfigurations) }
    }
}

private fun Context.hostActivity(): Activity? = when(this) {
    is Activity -> this
    is ContextWrapper -> baseContext.takeIf { it!==this }?.hostActivity()
    else -> null
}

/** App-session scope survives the Activity which is minimized by an actual ready Stage. */
private class WorkspaceSession(private val state: BugWorldState) {
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.Main.immediate)
    private val windows=WorkspaceWindows(setOf(STUDIO_ID))
    private val attached=mutableSetOf<String>()
    private val explicitlyClosed=mutableSetOf<String>()
    private val opening=mutableMapOf<String,CompletableDeferred<Unit>>()
    private var freshOnNextOpen=false
    private var closingStage=false
    private var detachedDuringClose=false
    private var stageDetachedSignal: CompletableDeferred<Unit>?=null
    private var restoreOnLateStageDetach=false
    private var studioNavigator: SpatialNavigator? = null
    private var generation by mutableIntStateOf(0)
    var previewVisible by mutableStateOf(false)
    var toolsVisible by mutableStateOf(true)
    var selectedArtworkId by mutableStateOf<String?>(null)
    var inGarden by mutableStateOf(false); private set
    fun isOpen(id: String): Boolean { generation; return id in windows.openIds }
    private fun instance(id: String)=if(id==STUDIO_ID) null else WINDOW_INSTANCE
    fun attached(id: String,navigator: SpatialNavigator) {
        if(id==STUDIO_ID) {
            studioNavigator = navigator
            explicitlyClosed-=id
            if(freshOnNextOpen && windows.phase==WorkspaceWindows.Phase.SHARED) {
                freshOnNextOpen=false; previewVisible=false
                state.freshStudioSession()
            }
        }
        // An asynchronous open may finish after the user has already closed it.
        if(id in explicitlyClosed) {
            runCatching { navigator.closeWindowContainer(id,instance(id)) }.onFailure { failure(R.string.window_close_failed,it) }
            return
        }
        attached+=id; windows.opened(id); opening[id]?.complete(Unit); generation++
        if(windows.phase==WorkspaceWindows.Phase.STAGE) {
            runCatching { navigator.minimizeWindowContainer(id,instance(id)) }.onFailure { failure(R.string.window_minimize_failed,it) }
        }
        Log.i(WINDOW_TAG,"attached $id phase=${windows.phase}")
    }
    fun detached(id: String,userClosed: Boolean) {
        if(id==STUDIO_ID && userClosed && windows.phase==WorkspaceWindows.Phase.SHARED) freshOnNextOpen=true
        if (id == STUDIO_ID) studioNavigator = null
        attached-=id; windows.detached(id,userClosed); generation++
        Log.i(WINDOW_TAG,"detached $id phase=${windows.phase}")
    }
    fun open(id: String,navigator: SpatialNavigator,returningToWorkspace: Boolean = false) {
        if(windows.phase!=WorkspaceWindows.Phase.SHARED) return
        if(id in opening) return
        explicitlyClosed-=id
        if(id in attached) {
            runCatching {
                // Composition may still be attached after the system dropped its window.
                val restored = navigator.restoreWindowContainer(id,instance(id))
                if (!restored && returningToWorkspace) navigator.openWindowContainer(id,instance(id),null)
            }
                .onFailure { failure(R.string.window_restore_failed,it) }
            return
        }
        val ready=CompletableDeferred<Unit>()
        opening[id]=ready; windows.opened(id); generation++
        scope.launch {
            try {
                val restored=navigator.restoreWindowContainer(id,instance(id))
                if(!restored) navigator.openWindowContainer(id,instance(id),null)
                if(withTimeoutOrNull(6000) { ready.await(); true }!=true && windows.phase==WorkspaceWindows.Phase.SHARED) {
                    windows.closed(id); generation++
                    state.report(if(id==ALBUM_ID) R.string.window_album_timeout else R.string.window_canvas_timeout)
                    Log.w(WINDOW_TAG,"attach timeout $id restored=$restored")
                }
            } catch(error: Exception) {
                if(error is CancellationException) throw error
                windows.closed(id); generation++; failure(if(id==ALBUM_ID) R.string.window_album_open_failed else R.string.window_canvas_open_failed,error)
            } finally { if(opening[id]===ready) opening.remove(id) }
        }
    }
    fun close(id: String,navigator: SpatialNavigator) {
        runCatching { navigator.closeWindowContainer(id,instance(id)) }
            .onSuccess {
                if(id==STUDIO_ID) freshOnNextOpen=true
                explicitlyClosed+=id; windows.closed(id); attached-=id
                opening.remove(id)?.complete(Unit)
                generation++; Log.i(WINDOW_TAG,"close requested $id")
            }
            .onFailure { failure(if(id==ALBUM_ID) R.string.window_album_close_failed else R.string.window_canvas_close_failed,it) }
    }
    fun resumeEditing(navigator: SpatialNavigator) { freshOnNextOpen=false; open(STUDIO_ID,navigator) }
    fun showPreview(navigator: SpatialNavigator) {
        if(freshOnNextOpen) { freshOnNextOpen=false; state.freshStudioSession() }
        previewVisible=true; open(STUDIO_ID,navigator)
    }
    fun enterGarden(navigator: SpatialNavigator) {
        if(!windows.beginStage()) return
        generation++
        scope.launch {
            try {
                Log.i(WINDOW_TAG,"request Stage; preserve=${windows.openIds}")
                val result=navigator.openStage(GARDEN_ID,StageStyle.Full)
                if(result !is OpenStageResult.Allowed) {
                    if(windows.stageRejected()) { state.cancelPendingRelease(); state.report(R.string.stage_refused) }
                    return@launch
                }
                // Allowed acknowledges navigation, not native attachment or scene readiness.
                val ready=withTimeoutOrNull(60000) {
                    while(windows.phase==WorkspaceWindows.Phase.OPENING ||
                        (windows.phase==WorkspaceWindows.Phase.STAGE && !state.sceneReady)) delay(100)
                    state.sceneReady
                }
                if(ready==null && windows.phase in setOf(WorkspaceWindows.Phase.OPENING,WorkspaceWindows.Phase.STAGE)) {
                    state.report(R.string.stage_timeout)
                    leaveGarden(navigator)
                }
            } catch(error: Exception) {
                if(error is CancellationException) throw error
                if(windows.stageRejected()) state.cancelPendingRelease()
                failure(R.string.stage_enter_failed,error)
            } finally { generation++ }
        }
    }
    fun stageVisible(navigator: SpatialNavigator) {
        if(windows.phase!=WorkspaceWindows.Phase.OPENING) return
        val ids=windows.stageReady()
        inGarden=true; generation++
        Log.i(WINDOW_TAG,"Native Stage visible; minimize=$ids")
        ids.forEach { id -> runCatching {
            val minimized = if (id == STUDIO_ID) {
                studioNavigator?.minimizeWindowContainer() ?: navigator.minimizeWindowContainer(id, instance(id))
            } else navigator.minimizeWindowContainer(id, instance(id))
            Log.i(WINDOW_TAG,"minimize $id accepted=$minimized")
        }
            .onFailure { failure(R.string.window_minimize_failed,it) } }
    }
    fun leaveGarden(navigator: SpatialNavigator,onFailed: ()->Unit = {}) {
        state.cancelPendingRelease()
        if(!windows.beginReturn()) return
        closingStage=true
        detachedDuringClose=false
        val detached=CompletableDeferred<Unit>()
        stageDetachedSignal=detached
        scope.launch {
            var succeeded=false
            try {
                navigator.closeStage(); succeeded=true
                // closeStage acknowledges the request before the native Stage disappears.
                // Restoring earlier races its final system-wide minimization of Shared Space.
                withTimeoutOrNull(5000) { detached.await() }
                yield()
            }
            catch(error: Exception) {
                if(error is CancellationException) throw error
                failure(R.string.stage_exit_failed,error)
            } finally {
                closingStage=false
                stageDetachedSignal=null
                if(succeeded || detachedDuringClose) {
                    restoreOnLateStageDetach=!detachedDuringClose
                    restore(navigator)
                }
                else { windows.returnFailed(); generation++; onFailed() }
            }
        }
    }
    fun stageHidden(navigator: SpatialNavigator) {
        if (windows.phase == WorkspaceWindows.Phase.STAGE || closingStage) stageDetached(navigator)
    }

    fun stageDetached(navigator: SpatialNavigator) {
        state.cancelPendingRelease()
        Log.i(WINDOW_TAG,"Stage detached phase=${windows.phase}")
        if(closingStage) { detachedDuringClose=true; stageDetachedSignal?.complete(Unit); return }
        if(restoreOnLateStageDetach) {
            restoreOnLateStageDetach=false
            if(windows.phase==WorkspaceWindows.Phase.SHARED) windows.openIds.forEach { open(it,navigator,true) }
            return
        }
        if(windows.beginReturn()) scope.launch { yield(); restore(navigator) }
    }
    private fun restore(navigator: SpatialNavigator) {
        val ids=windows.finishReturn(STUDIO_ID)
        freshOnNextOpen=false
        inGarden=false; state.cancelPendingRelease(); generation++
        Log.i(WINDOW_TAG,"restore workspace=$ids")
        scope.launch {
            // Native Shared Space can become available after the Stage visibility callback.
            var restored = false
            for (waitMillis in listOf(120L, 300L, 650L)) {
                delay(waitMillis)
                if (windows.phase != WorkspaceWindows.Phase.SHARED) return@launch
                restored = runCatching {
                    studioNavigator?.restoreWindowContainer() == true ||
                        navigator.restoreWindowContainer(STUDIO_ID, instance(STUDIO_ID))
                }.getOrElse {
                    Log.w(WINDOW_TAG, "Native studio restore failed", it)
                    false
                }
                Log.i(WINDOW_TAG, "Native studio restore accepted=$restored")
                if (restored) break
            }
            if (windows.phase == WorkspaceWindows.Phase.SHARED) {
                ids.filter { it in windows.openIds }.forEach { id ->
                    if (id != STUDIO_ID || !restored || id !in attached) open(id, navigator, true)
                }
            }
        }
    }
    private fun failure(@androidx.annotation.StringRes message: Int,error: Throwable) {
        Log.e(WINDOW_TAG,state.app.getString(message),error); state.report(message)
    }
}
