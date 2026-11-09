package com.bugworld.app

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.*
import com.bugworld.app.data.*
import com.bugworld.app.drawing.*
import com.bugworld.app.garden.GardenQueue
import com.bugworld.app.garden.SceneRelease
import java.io.ByteArrayOutputStream
import java.io.File
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

enum class PaintTool { CRAYON, FILL, ERASER }

class BugWorldState(val app: Application) {
    val templates = Species.entries.associateWith { Template(app, it) }
    val store = ArtworkStore(File(app.filesDir, "artworks"))
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val ioMutex = Mutex()
    private val operationMutex = Mutex()
    private var pendingOperations = 0
    private val queue = GardenQueue()
    private val release = SceneRelease()
    private val draftJobs=mutableMapOf<Species,Job>()
    private var canvases: CanvasSession? = null
    private var previewJob: Job? = null
    private val draftBackupsPending=Species.entries.toMutableSet()
    private val previewLink=PreviewLink()
    var previewActive=false
    var works by mutableStateOf<List<Artwork>>(emptyList()); private set
    var gardenIds by mutableStateOf<List<String>>(emptyList()); private set
    var species by mutableStateOf(Species.BUTTERFLY); private set
    val canvasTemplateVersion = Template.CURRENT_VERSION
    var document by mutableStateOf(templates.getValue(species).newDocument()); private set
    var editedId by mutableStateOf<String?>(null); private set
    var revision by mutableIntStateOf(0); private set
    var tool by mutableStateOf(PaintTool.CRAYON)
    var color by mutableIntStateOf(0xFF986BD3.toInt())
    var radius by mutableFloatStateOf(13f)
    var brushStrength by mutableFloatStateOf(.5f)
    var mirror by mutableStateOf(false)
    var busy by mutableStateOf(false); private set
    var ready by mutableStateOf(false); private set
    var message by mutableStateOf<StudioStatus>(StudioStatus.Message(R.string.album_opening)); private set
    var previewBitmap by mutableStateOf<Bitmap?>(null); private set
    var previewSpecies by mutableStateOf(Species.BUTTERFLY); private set
    var previewAsset by mutableStateOf("v3/butterfly"); private set
    var previewRevision by mutableIntStateOf(0); private set
    var musicVolume by mutableFloatStateOf(.35f)
    var natureVolume by mutableFloatStateOf(.6f)
    var invitation by mutableIntStateOf(0); private set
    var invitationTarget by mutableStateOf<String?>(null); private set
    var sceneReady by mutableStateOf(false); private set
    var pendingRelease by mutableStateOf<SceneRelease.Request?>(null); private set
    var arrival by mutableStateOf<SceneRelease.Request?>(null); private set
    val template get() = templates.getValue(species)
    fun templateFor(work: Artwork) = templates.getValue(work.species)
    val gardenWorks get() = gardenIds.mapNotNull { id -> works.find { it.id == id } }

    init {
        operation {
            // Build paper relief once, away from the UI. Switching never creates or decodes a sheet.
            val first=document
            canvases=withContext(Dispatchers.Default) { CanvasSession(Species.entries.associateWith {
                if(it==Species.BUTTERFLY) first else templates.getValue(it).newDocument()
            }) }
            works = io { store.list() }
            val oldWorkCount=works.count { it.templateVersion<Template.CURRENT_VERSION }
            var migrationFailures=0
            for(work in works.filter { it.templateVersion<Template.CURRENT_VERSION }) {
                try {
                    val bytes=io { store.image(work) }
                    val converted=withContext(Dispatchers.Default) {
                        val image=checkNotNull(BitmapFactory.decodeByteArray(bytes,0,bytes.size))
                        try { val current=templateFor(work); current.bitmap(current.documentFrom(image,work.templateVersion)).usePng() }
                        finally { image.recycle() }
                    }
                    io { store.migrateToCurrent(work,converted) }
                } catch(error: Exception) {
                    if(error is CancellationException) throw error
                    migrationFailures++
                    android.util.Log.e("BugWorldArtworks","Migration retained original ${work.id}",error)
                }
            }
            works=io { store.list() }
            queue.restore(io { store.loadGarden() }, works.map { it.id }.toSet())
            gardenIds = queue.ids
            ready = true
            message = when {
                migrationFailures>0 -> StudioStatus.IncompleteMigration(migrationFailures)
                oldWorkCount>0 -> StudioStatus.Message(R.string.migration_done)
                else -> StudioStatus.Message(R.string.choose_color)
            }
        }
    }
    private suspend fun <T> io(action: () -> T): T = ioMutex.withLock { withContext(Dispatchers.IO) { action() } }
    private fun operation(action: suspend () -> Unit) {
        pendingOperations++; busy=true
        scope.launch {
            try { operationMutex.withLock { action() } } catch (error: Exception) {
                if (error is CancellationException) throw error
                android.util.Log.e("BugWorldArtworks","Artwork operation failed",error)
                report(when ((error as? ArtworkException)?.issue) {
                    ArtworkIssue.SHEET_CHANGED -> R.string.work_version_conflict
                    ArtworkIssue.STALE -> R.string.work_stale
                    ArtworkIssue.CHECKSUM -> R.string.work_checksum
                    ArtworkIssue.DELETE_FAILED -> R.string.work_delete_failed
                    ArtworkIssue.INVALID_ID -> R.string.work_invalid_id
                    ArtworkIssue.UNSUPPORTED_VERSION -> R.string.work_unsupported
                    ArtworkIssue.UNREADABLE -> R.string.file_read_failed
                    null -> R.string.operation_failed
                })
            } finally { pendingOperations--; busy = pendingOperations > 0 }
        }
    }
    fun changed() {
        revision++
        if(!previewActive) return
        if(previewJob?.isActive==true) return
        previewJob=scope.launch {
            delay(100)
            if(previewActive && previewLink.changedDraft(species,revision)) updatePreview(template.bitmap(document),species)
        }
    }
    fun strokeFinished() {
        canvases?.trimHistory()
        changed()
        val kind=species; val sheet=document
        draftJobs.remove(kind)?.cancel()
        draftJobs[kind] = scope.launch {
            delay(700)
            DraftWrite.attempt({ saveDraftBytes(kind,encoded(sheet),canvasTemplateVersion) }) { error ->
                android.util.Log.e("BugWorldArtworks","Draft write failed",error)
                report(R.string.draft_save_failed)
            }
        }
    }
    private suspend fun encoded(sheet: PaintDocument = document): ByteArray {
        // Snapshot on Main; encoding never races with finger painting or blocks it.
        val pixels=sheet.pixels.copyOf(); val width=sheet.width; val height=sheet.height
        return withContext(Dispatchers.Default) {
            Bitmap.createBitmap(pixels,width,height,Bitmap.Config.ARGB_8888).usePng()
        }
    }
    private suspend fun saveDraftBytes(currentSpecies: Species,bytes: ByteArray,version: Int) {
        io {
            if(currentSpecies in draftBackupsPending) store.preserveLatestDraft(currentSpecies)
            store.saveDraft(currentSpecies, bytes, version)
        }
        draftBackupsPending-=currentSpecies
    }
    private fun showCurrentCanvas() {
        val session=checkNotNull(canvases)
        species=session.species; document=session.current.document; editedId=session.current.artworkId
        mirror=false; changed()
    }
    fun selectSpecies(next: Species) {
        if (busy || !ready || next == species) return
        val started=android.os.SystemClock.elapsedRealtimeNanos()
        checkNotNull(canvases).select(next); showCurrentCanvas()
        android.util.Log.i("BugWorldCanvas","select=${next.asset} state_us=${(android.os.SystemClock.elapsedRealtimeNanos()-started)/1000}")
    }
    fun undo() { document.undo(); strokeFinished() }
    fun redo() { document.redo(); strokeFinished() }
    fun newCanvas() {
        if (busy || !ready) return
        draftJobs.remove(species)?.cancel()
        checkNotNull(canvases).fresh(); showCurrentCanvas(); strokeFinished()
        report(R.string.fresh_paper)
    }
    /** User reopened the studio. Stage suspension/return must never call this. */
    fun freshStudioSession() {
        draftJobs.values.forEach { it.cancel() }; draftJobs.clear()
        operation {
            checkNotNull(canvases).restart(); showCurrentCanvas()
            report(R.string.fresh_paper)
        }
    }
    fun save(asNew: Boolean = false, onSaved: (Artwork) -> Unit = {}) {
        if (busy || !ready) return
        draftJobs.remove(species)?.cancel()
        val selected = species; val id = if (asNew) null else editedId
        val version = canvasTemplateVersion
        operation {
            val bytes=encoded()
            val work = io { store.save(selected, bytes, id, version) }
            checkNotNull(canvases).saved(work.id)
            editedId = work.id; works = io { store.list() }
            saveDraftBytes(selected,bytes,version)
            if(previewLink.changedSaved(work.id,work.revision)) updatePreview(template.bitmap(document),selected)
            report(R.string.art_saved); onSaved(work)
        }
    }
    fun edit(work: Artwork, done: () -> Unit) {
        if (busy) return
        draftJobs.remove(work.species)?.cancel()
        operation {
            val bytes = io { store.image(work) }
            val restored=decodeDocument(work.species,bytes,work.templateVersion)
            if(work.templateVersion<Template.CURRENT_VERSION) {
                val converted=encoded(restored)
                io { store.migrateToCurrent(work,converted) }
                works=io { store.list() }
            }
            checkNotNull(canvases).edit(work.species,restored,work.id); showCurrentCanvas(); done()
        }
    }
    fun delete(work: Artwork, done: () -> Unit) {
        if (busy) return
        operation {
            io { store.delete(work.id) }
            queue.remove(work.id); gardenIds = queue.ids
            io { store.saveGarden(gardenIds) }
            works = io { store.list() }
            canvases?.deleted(work.id)
            if (editedId == work.id) editedId = null
            if (invitationTarget == work.id) invitationTarget = null
            if (pendingRelease?.artworkId == work.id) cancelPendingRelease()
            if(previewLink.clear(work.id)) { previewBitmap=null; previewRevision++ }
            done(); report(R.string.art_deleted)
        }
    }
    fun place(work: Artwork, done: () -> Unit) {
        if(pendingRelease!=null) { report(R.string.release_busy); return }
        // save() can call this after its durable write; serialized IO preserves order.
        operation {
            if (pendingRelease!=null) { report(R.string.release_busy); return@operation }
            if (io { store.list().none { it.id == work.id } }) { report(R.string.work_removed); return@operation }
            pendingRelease = release.request(work.id)
            invitationTarget = work.id; report(R.string.release_started); done()
        }
    }
    fun stageReady(value: Boolean) { sceneReady = value }
    fun claimRelease(visible: Boolean, resourcesReady: Boolean) = release.claim(visible, resourcesReady)
    fun commitRelease(request: SceneRelease.Request, onCommitted: () -> Unit) {
        operation {
            if (!release.isCurrent(request)) return@operation
            val desired = GardenQueue().apply { restore(gardenIds, works.map { it.id }.toSet()); place(request.artworkId) }.ids
            try {
                io { store.saveGarden(desired) }
                // Cancellation during the durable write must not publish a stale arrival.
                if (!release.isCurrent(request)) { io { store.saveGarden(gardenIds) }; return@operation }
                check(release.complete(request))
                queue.restore(desired, works.map { it.id }.toSet()); gardenIds = queue.ids
                pendingRelease = null; arrival = request
                report(R.string.release_done); onCommitted()
            } catch (error: Exception) { release.retry(request); throw error }
        }
    }
    fun cancelPendingRelease() { release.cancel(); pendingRelease = null; sceneReady = false }
    fun preview(work: Artwork? = null, done: () -> Unit) {
        if (busy) return
        operation {
            val unchanged=if(work==null) previewLink.matchesDraft(species,revision)
                else previewLink.matchesSaved(work.id,work.revision)
            if(previewBitmap!=null && unchanged) { done(); return@operation }
            val bitmap = if (work == null) template.bitmap(document) else {
                val bytes = io { store.image(work) }
                withContext(Dispatchers.Default) {
                    val image=checkNotNull(BitmapFactory.decodeByteArray(bytes,0,bytes.size))
                    try { val current=templateFor(work); current.bitmap(current.documentFrom(image,work.templateVersion)) }
                    finally { image.recycle() }
                }
            }
            if(work==null) previewLink.draft(species,revision) else previewLink.saved(work.id,work.revision)
            updatePreview(bitmap,work?.species ?: species)
            done()
        }
    }
    private fun updatePreview(bitmap: Bitmap,kind: Species) {
        previewBitmap=bitmap; previewSpecies=kind; previewRevision++
        previewAsset = "v3/${kind.asset}"
    }
    fun invite() { invitation++; report(R.string.invite_hint) }
    fun report(@androidx.annotation.StringRes id: Int) { message = StudioStatus.Message(id) }
    private suspend fun decodeDocument(kind: Species,bytes: ByteArray,sourceVersion: Int): PaintDocument =
        withContext(Dispatchers.Default) {
            val bitmap=BitmapFactory.decodeByteArray(bytes,0,bytes.size) ?: throw ArtworkException(ArtworkIssue.UNREADABLE)
            try { templates.getValue(kind).documentFrom(bitmap,sourceVersion) } finally { bitmap.recycle() }
        }
}

private fun Bitmap.usePng(): ByteArray = try {
    ByteArrayOutputStream().also { check(compress(Bitmap.CompressFormat.PNG, 100, it)) }.toByteArray()
} finally { recycle() }
