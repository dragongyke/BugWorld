package com.bugworld.app.garden

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.bugworld.app.R
import com.bugworld.app.BugWorldState
import com.bugworld.app.data.*
import com.bugworld.app.spatial.*
import com.bugworld.app.interaction.*
import com.bugworld.app.audio.GardenAudio
import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.ecs.resource.*
import com.pico.spatial.core.math.*
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlin.math.*

/** Loading is awaited outside the frame loop. Only prepared v3 GLB instances enter the scene. */
class GardenRuntime(private val state: BugWorldState) : AutoCloseable {
    private val createdAtNanos=java.lang.System.nanoTime()
    val root=Entity()
    private val library=ModelLibrary(state.app,state.templates)
    private var environment: ForestEnvironment?=null
    private val population=Population(10)
    private val models=mutableMapOf<String,Resident>()
    private val invitation=HandInvitation()
    private val arrival=ArrivalEffect(root)
    private val preparation=Mutex()
    private val readiness=SceneReadiness()
    private val sparkMesh=MeshResource.createSphere(.006f)
    private val sparkMaterial=UnlitMaterial.create(BlendingMode.OPAQUE).apply {
        setBaseColor(Color4(1f,.84f,.44f,1f)); setApplyToneMapping(false)
    }
    private val sparks=List(24) { Entity().apply {
        components.set(ModelComponent(sparkMesh,sparkMaterial)); enabled=false; root.addChild(this)
    } }
    private var audio: GardenAudio?=null
    private var initialized=false
    private var time=0f
    private val selection=GardenSelection()
    var interactionCue by mutableStateOf<GardenInteractionCue?>(null); private set
    private var cueRemaining=0f
    private var cueEntity: Entity?=null
    private var landedResident: String?=null
    private var placement=GardenPlacement()
    private var placed=false
    private var closed=false
    private var running=true
    private var exitFade=1f
    private val arrivals=linkedSetOf<String>()
    private var lastArrival=-100f
    private val lanes=Species.entries.associateWith { species ->
        List(ApprovedGardenRoutes.count(species)) { slot -> GardenRouteTraffic(species, slot) }
    }
    private fun lane(r: Resident)=lanes.getValue(r.work.species)[r.index]
    private var notifiedReady=false
    private var previousTips=emptyMap<HandSide,HandPoint>()
    private data class Resident(val model: InsectModel,var work: Artwork,var position: HandPoint,
        var index: Int,var yaw: Float,val animator: InsectAnimationController,val hit: GardenHitTarget,
        var onRoute: Boolean=false,var reaction: Float=0f,var lastTouch: Float=-100f,var bornAt: Float=-100f,var sounded: Boolean=true,
        val visit: VisitMotion=VisitMotion(),var palmBlend: Float=0f,var surfaceRotation: Quat?=null)

    init { state.stageReady(false) }

    suspend fun prepare() = preparation.withLock {
        check(!closed)
        if(environment==null) {
            val scene=StageDiagnostics.awaitPhase("garden_native_load") { ForestEnvironment.load() }
            try {
                currentCoroutineContext().ensureActive(); check(!closed)
                StageDiagnostics.measure("garden_attach_materials") {
                    check(root.addChild(scene.root)); environment=scene
                }
            } catch(error: Throwable) { scene.close(); throw error }
            runCatching { StageDiagnostics.measure("audio_setup") { GardenAudio(state.app) } }.onSuccess { audio=it; it.active(running) }
                .onFailure { state.report(R.string.audio_unavailable); Log.e(TAG,"Audio preparation failed",it) }
        }
        val requested=(state.gardenWorks+listOfNotNull(state.pendingRelease?.let { pending ->
            state.works.find { it.id==pending.artworkId }
        })).distinctBy { it.id }
        val occupied=models.filterValues { it.onRoute }.mapValues { it.value.index }
        for((work,index) in GardenResidentSlots.plan(requested,state.pendingRelease?.artworkId,occupied)) {
            val existing=models[work.id]
            if(existing!=null && !existing.onRoute) existing.index=index
            if(existing?.work?.revision==work.revision) continue
            StageDiagnostics.awaitPhase("resident_${work.species.asset}_load") { library.preload("v3/${work.species.asset}") }
            val bitmap=StageDiagnostics.awaitPhase("artwork_decode") { texture(work) }
            try {
                check(!closed)
                if(existing!=null) {
                    StageDiagnostics.awaitPhase("artwork_map_upload") { existing.model.updateTextureSuspend(bitmap) }; existing.work=work
                } else {
                    val model=InsectModel(library,"v3/${work.species.asset}")
                    try {
                        StageDiagnostics.awaitPhase("artwork_map_upload") { model.updateTextureSuspend(bitmap) }
                        currentCoroutineContext().ensureActive(); check(!closed)
                        val p=ApprovedGardenRoutes.arrivalPose(work.species,index)
                        model.opacity(0f); model.setActive(false); model.root.enabled=false; root.addChild(model.root)
                        models[work.id]=Resident(model,work,p.point,index,p.yaw,
                            InsectAnimationController(work.species,index/10f),GardenHitTarget(model.root))
                    } catch(error: Throwable) { model.close(); throw error }
                }
            } finally { bitmap.recycle() }
        }
        check(!closed)
        initialized=true
    }

    private fun resourcesPrepared(): Boolean {
        if(!initialized || audio?.ready==false) return false
        val required=(state.gardenWorks+listOfNotNull(state.pendingRelease?.let { request ->
            state.works.find { it.id==request.artworkId }
        })).distinctBy { it.id }
        return required.all { models[it.id]?.work?.revision==it.revision }
    }

    fun tick(delta: Float,hands: List<TrackedHand>,eyeWorld: Vector3?,visible: Boolean,onReady: ()->Unit) {
        if(closed || !running) return
        val ready=readiness.frame(visible,resourcesPrepared())
        if(!visible || !initialized) return
        time+=delta
        // Joint and HMD positions arrive in the Stage container space. All route,
        // surface, and wearer-facing calculations below are in the resident parent's axes.
        fun local(point: HandPoint): HandPoint {
            val v=root.convertPositionFrom(Vector3(point.x,point.y,point.z),null)
            return HandPoint(v.x,v.y,v.z)
        }
        val eye=eyeWorld?.let { local(HandPoint(it.x,it.y,it.z)) }?.takeIf { it.finite }
        val palms=if(eye==null) emptyList() else hands.mapNotNull { it.open?.inSpace(::local) }
        val tips=hands.filter { it.open==null && it.pinchGap>.045f }.associate { it.side to local(it.indexTip) }
        if(ready) {
            if(!notifiedReady) {
                notifiedReady=true; state.stageReady(true); onReady()
                Log.i(TAG,"Stage GLBs, painted residents and arrival audio prepared; visible for 3 frames")
                Log.i("BugWorldStagePerf","phase=first_visible_ready wall_ms=${(java.lang.System.nanoTime()-createdAtNanos)/1e6} residents=${models.size}")
            }
            state.claimRelease(true,true)?.let { request ->
                state.commitRelease(request) {
                    if(!closed) {
                        val id=request.artworkId
                        models[id]?.let { r ->
                            lane(r).depart(id); r.onRoute=false; r.model.root.enabled=false; r.model.setActive(false)
                            r.visit.target(null,r.position,r.position,false)
                            r.reaction=0f; r.lastTouch=-100f; r.palmBlend=0f; r.surfaceRotation=null
                        }
                        arrivals.add(id)
                    }
                }
            }
        }
        val previousInvitation=invitation.targetId
        invitation.update(palms,selection.preferredHand,delta)
        population.tick(state.gardenIds,delta)
        models.keys.filter { it !in population.entries && it !in state.gardenIds &&
            it!=state.pendingRelease?.artworkId }.forEach { id ->
            models.remove(id)?.let { r -> lane(r).depart(id); r.hit.close(); r.model.close() }
            arrivals.remove(id)
        }
        val available=population.entries.filter { (id,entry) -> !entry.leaving && models[id]?.onRoute==true }.keys
        val previousSelection=selection.selected
        selection.tick(delta,available)
        if(invitation.targetId!=null && invitation.targetId !in available) invitation.cancel()
        if(previousInvitation!=null && invitation.targetId==null) {
            showCue(previousInvitation,if(landedResident==previousInvitation) R.string.cue_visit_ended else R.string.cue_cancelled,
                R.string.cue_reinvite,3f)
            landedResident=null
        } else if(previousSelection!=null && selection.selected==null) {
            showCue(previousSelection,R.string.cue_selection_ended,R.string.cue_reinvite,2.5f)
        }
        val returning=models.values.any { it.visit.returning }
        val candidate=selection.selected?.takeIf { id -> models[id]?.let { resident ->
            GardenInteractionPolicy.canInvite(resident.work.species,invitation.surface?.center?.distance(resident.position),invitation.canInvite,
                inBirth=time-resident.bornAt<2.7f,retiring=population.entries[id]?.leaving!=false,
                visiting=returning || resident.visit.approaching,
                responding=resident.reaction>.03f || time-resident.lastTouch<1.8f)
        }==true }
        if(candidate!=null) {
            invitation.begin(candidate); selection.consume()
            showCue(candidate,R.string.cue_approaching,R.string.cue_hold,12f)
        }
        // Pause only the lane whose resident has left traffic or is holding at its birth/contact.
        for(group in lanes.values) for(track in group) track.held=false
        for((id,r) in models) if(r.onRoute && (id==invitation.targetId || r.visit.approaching || r.visit.returning ||
            r.reaction>.03f || time-r.lastTouch<1.8f || time-r.bornAt<2.7f)) lane(r).held=true
        for(group in lanes.values) for(track in group) track.advance(delta)

        fun admit(id: String) {
            val r=models[id] ?: return
            if(r.onRoute || population.entries[id]?.leaving!=false || id==state.pendingRelease?.artworkId) return
            val isArrival=id in arrivals
            if(isArrival && time-lastArrival<3f) return
            if(!lane(r).admit(id)) return
            val pose=ApprovedGardenRoutes.arrivalPose(r.work.species,r.index)
            r.position=pose.point; r.yaw=pose.yaw; r.onRoute=true
            r.model.root.enabled=true; r.model.setActive(true)
            if(isArrival) {
                r.bornAt=time; r.sounded=false
                lastArrival=time; arrival.start(pose.point)
                Log.i(TAG,"Arrival started id=$id revision=${r.work.revision} route=${r.index} position=${pose.point}")
            }
        }
        // Older residents start first, even when Stage was reconstructed for a new release.
        for(id in state.gardenIds) admit(id)
        arrivals.removeAll { it !in state.gardenIds || models[it]?.onRoute==true }

        models.forEach { (id,resident) ->
            val entry=population.entries[id] ?: return@forEach
            if(!resident.onRoute) return@forEach
            if(id==state.pendingRelease?.artworkId) { resident.model.opacity(0f); return@forEach }
            val species=resident.work.species
            val age=time-resident.bornAt
            if(!resident.sounded && age>.55f) { resident.sounded=true; audio?.arrival(resident.position.x,resident.position.z) }
            val inBirth=age<2.7f
            val previous=resident.position
            val nearby=tips.entries.firstOrNull { it.value.distance(previous)<.09f }
            if(nearby!=null && time-resident.lastTouch>2.5f && !inBirth && !entry.leaving &&
                selection.selected!=id && id!=invitation.targetId && !resident.visit.approaching && !resident.visit.returning) {
                val speed=previousTips[nearby.key]?.distance(nearby.value)?.div(delta.coerceAtLeast(.001f)) ?: 0f
                resident.reaction=if(species==Species.CATERPILLAR && speed<.35f) .7f else 1f
                resident.lastTouch=time; audio?.touch()
            }
            val reacting=resident.reaction>.03f || time-resident.lastTouch<1.8f
            val perchAge=invitation.landedFor ?: 0f
            val stepPhase=((perchAge-1.35f)/.85f).coerceIn(0f,1f)
            val perch=if(!entry.leaving && !inBirth && id==invitation.targetId && eye!=null)
                invitation.surface?.perch(species,eye,if(species==Species.BUTTERFLY) 0f else stepPhase*.004f) else null
            val approaching=perch!=null
            val track=lane(resident)
            val natural=ApprovedGardenRoutes.pose(species,resident.index,track.routeTime(id))
            var target=resident.visit.target(perch?.point,previous,natural.point,reacting)
            if(entry.leaving && species.canFly) target=HandPoint(target.x,target.y+.22f*entry.retiring,target.z-.12f*entry.retiring)
            val onHand=perch!=null && (landedResident==id || previous.distance(target)<.018f)
            if(onHand) {
                invitation.landed(id)
                if(landedResident!=id) {
                    landedResident=id
                    showCue(id,R.string.cue_landed,R.string.cue_returning,3.2f)
                }
            }
            val desiredYaw=if((approaching || resident.visit.returning) && previous.distance(target)>.05f)
                atan2(-(target.x-previous.x),-(target.z-previous.z))*180f/PI.toFloat() +
                    (if(species==Species.BUTTERFLY) 0f else 90f) else natural.yaw
            val angle=((desiredYaw-resident.yaw+540f)%360f)-180f
            val flying=species.canFly && (approaching && !onHand || resident.visit.returning ||
                !approaching && natural.airborne && natural.hopPhase==null)
            val groundTurning=!approaching && !resident.visit.returning && !natural.airborne && abs(angle)>.15f
            val frame=resident.animator.update(delta,moving=(previous.distance(target)>.0001f || natural.moving && !track.held || groundTurning) && !inBirth && !reacting,
                turning=(angle/60f).coerceIn(-1f,1f),flying=flying && !inBirth,onHand=onHand,
                reaction=resident.reaction,retiring=entry.leaving)
            // Shells open before flight travel. Ground paths are sampled on the reviewed meshes.
            val travel=if(flying || entry.leaving && species.canFly) frame.flightBlend else 1f
            resident.position=when {
                onHand -> target // Follow the current sample exactly, even when the hand starts moving.
                inBirth || reacting -> previous
                approaching || resident.visit.returning || entry.leaving -> lerp(previous,target,(delta*1.8f*travel).coerceIn(0f,1f))
                else -> target
            }
            if(!approaching && !resident.visit.returning && !natural.airborne) resident.yaw=natural.yaw
            else if(!reacting) resident.yaw+=angle*(delta*2f).coerceAtMost(1f)
            val p=resident.position
            val scale=ApprovedGardenRoutes.stageScale(species)
            val responseYaw=if(flying && reacting && !approaching && !resident.visit.returning)
                GardenInteractionPolicy.airborneResponseYaw(species,time-resident.lastTouch) else 0f
            // Flight eases down to a size supported by the palm. Restore stage scale on departure.
            val blendTarget=if(perch!=null) 1f else 0f
            resident.palmBlend+=(blendTarget-resident.palmBlend)*(delta*4f).coerceAtMost(1f)
            val palmScale=when(species) { Species.BUTTERFLY->.31f; Species.BEETLE->.21f; else->.15f }
            val renderScale=scale+(palmScale-scale)*resident.palmBlend
            resident.model.pose(p.x,p.y,p.z,resident.yaw+responseYaw,renderScale,
                if(approaching || resident.visit.returning) 0f else natural.pitch,
                if(approaching || resident.visit.returning) 0f else natural.roll)
            val nearPalm=perch!=null && (onHand || p.distance(perch.point)<.16f)
            if(nearPalm || resident.surfaceRotation!=null) {
                val transform=resident.model.root.components.get<TransformComponent>()!!
                val routeRotation=transform.quaternion
                val wanted=if(nearPalm) perch!!.orientation else routeRotation
                val rotation=Quat.slerp(resident.surfaceRotation ?: routeRotation,wanted,
                    (delta*(if(onHand) 20f else 8f)).coerceIn(0f,1f))
                transform.setQuaternion(rotation)
                resident.surfaceRotation=if(!nearPalm && abs(Quat.dot(rotation,routeRotation))>.9999f) null else rotation
            }
            // The authored beetle and ladybug walk clips articulate all six feet and antennae.
            // The butterfly's perch clip already grooms its antennae and moves its front legs.
            val settling=onHand && (species==Species.BEETLE || species==Species.LADYBUG) && frame.action==InsectAction.PERCH && stepPhase>0f && stepPhase<1f
            val hop = natural.hopPhase
            val visibleFrame = when {
                settling -> frame.copy(action=InsectAction.WALK,motion=.48f)
                hop != null && !approaching && !resident.visit.returning && !entry.leaving && !reacting ->
                    frame.copy(action=InsectAction.HOP,progress=hop)
                else -> frame
            }
            resident.model.animate(visibleFrame)
            resident.model.opacity(if(entry.leaving) (1-entry.retiring/1.2f).coerceAtLeast(0f) else ((age-.6f)/.6f).coerceIn(0f,1f))
            resident.reaction=(resident.reaction-delta*.75f).coerceAtLeast(0f)
        }
        previousTips=tips
        sparks.forEachIndexed { i,entity ->
            entity.enabled=true
            val a=i*2.399f
            entity.components[TransformComponent::class.java]?.apply {
                setPosition(Vector3(cos(a)*(1.2f+i%3)+sin(time*.2f+i)*.10f,.7f+(i%9)*.26f+sin(time*.5f+i)*.08f,sin(a)*(1.5f+i%3*.4f)))
                setScaleVector(Vector3(.55f+.45f*sin(time*.7f+i).pow(2)))
            }
        }
        arrival.tick(delta)
        updateCue(delta)
        audio?.volume(state.musicVolume,state.natureVolume,(time/1.2f).coerceAtMost(1f)*exitFade)
    }
    /** Entry orientation comes from HMD tracking, never from an assumed eye origin at floor level. */
    fun placeAt(eye: Vector3,forward: Vector3) {
        // Providers may publish an identity pose before tracking has acquired the wearer.
        if(placed || notifiedReady || !eye.x.isFinite() || eye.y !in .5f..2.5f || !eye.z.isFinite()) return
        if(forward.x*forward.x+forward.z*forward.z<.01f) return
        placement=GardenPlacement(eye.x,(eye.y-1.6f).coerceIn(-.45f,.25f),eye.z,
            atan2(-forward.x,-forward.z)*180f/PI.toFloat())
        root.components.get<TransformComponent>()!!.apply {
            setPosition(Vector3(placement.x,placement.y,placement.z));setEulerAngles(EulerAngles(0f,placement.yaw,0f))
        }
        placed=true
        Log.i(TAG,"Entry placement=$placement eye=$eye")
    }
    fun ownsHit(entity: Entity)=running && !closed && models.values.any { it.onRoute && it.hit.owns(entity) }
    fun interact(entity: Entity,poke: Boolean,side: HandSide?) {
        if(!running || closed || !notifiedReady) return
        val (id,resident)=models.entries.firstOrNull { it.value.onRoute && it.value.hit.owns(entity) } ?: return
        val response=GardenInteractionPolicy.gesture(resident.work.species,poke,
            inBirth=time-resident.bornAt<2.7f,retiring=population.entries[id]?.leaving!=false,
            visiting=invitation.targetId!=null || models.values.any { it.visit.approaching || it.visit.returning },
            secondsSinceTouch=time-resident.lastTouch)
        if(response==GardenGestureResponse.IGNORE) return
        resident.reaction=GardenInteractionPolicy.REACTION; resident.lastTouch=time; audio?.touch()
        // A new explicit target supersedes the old selection, including a poke or a ground-species pinch.
        selection.clear()
        if(response==GardenGestureResponse.RESPOND_AND_SELECT) {
            invitation.reset(); selection.select(id,side)
            showCue(id,R.string.cue_selected,
                R.string.cue_gesture,12.1f,resident.work.species)
            Log.i(TAG,"Selected insect=$id species=${resident.work.species}")
        } else showCue(id,R.string.cue_greet,
            if(!resident.work.species.canFly)
                R.string.cue_ground else R.string.cue_select_again,2.8f,resident.work.species)
    }
    /** Attachment shares garden-local coordinates and is released with the scene root. */
    fun attachInteractionCue(entity: Entity) {
        if(closed) return
        cueEntity=entity; entity.enabled=false; root.addChild(entity)
        val lookAt=LookAtComponent().apply {
            alignLocalUpToWorldUp=false; lookAtForwardDirection=LookAtForwardDirection.POSITIVE_Z
        }
        entity.components.set(lookAt); lookAt.setViewerAsTarget()
    }
    private fun showCue(id: String,title: Int,instruction: Int,duration: Float,species: Species?=null) {
        interactionCue=GardenInteractionCue(id,title,instruction,species); cueRemaining=duration
    }
    private fun updateCue(delta: Float) {
        cueRemaining=(cueRemaining-delta).coerceAtLeast(0f)
        val resident=interactionCue?.residentId?.let(models::get)
        if(cueRemaining==0f || resident==null) interactionCue=null
        cueEntity?.let { entity ->
            entity.enabled=interactionCue!=null
            if(interactionCue!=null && resident!=null) {
                val p=resident.position
                entity.components.get<TransformComponent>()?.setPosition(Vector3(p.x,p.y+.22f,p.z))
            }
        }
    }
    fun active(value: Boolean) {
        running=value; audio?.active(value); models.values.forEach { it.model.setActive(value && it.onRoute) }
        if(!value) {
            invitation.reset(); selection.clear(); readiness.reset(); previousTips=emptyMap()
            interactionCue=null; cueRemaining=0f; landedResident=null; cueEntity?.enabled=false
        }
    }
    suspend fun fadeOut() { repeat(12) {
        exitFade=1-(it+1)/12f; audio?.volume(state.musicVolume,state.natureVolume,exitFade); delay(35)
    } }
    fun cancelExitFade() { if(!closed) { exitFade=1f; state.stageReady(notifiedReady) } }
    private suspend fun texture(work: Artwork): Bitmap {
        val bytes=withContext(Dispatchers.IO) { state.store.image(work) }
        var produced: Bitmap?=null
        try { return withContext(Dispatchers.Default) {
            val original=checkNotNull(BitmapFactory.decodeByteArray(bytes,0,bytes.size)) { "Artwork bitmap could not be decoded" }
            try { val template=state.templateFor(work); template.bitmap(template.documentFrom(original,work.templateVersion)).also { produced=it } }
            finally { original.recycle() }
        } } catch(error: Throwable) { produced?.recycle(); throw error }
    }
    private fun lerp(a: HandPoint,b: HandPoint,t: Float)=HandPoint(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,a.z+(b.z-a.z)*t)
    override fun close() {
        if(closed) return
        closed=true; state.stageReady(false); invitation.reset(); audio?.close(); audio=null
        interactionCue=null; cueEntity?.enabled=false; cueEntity=null
        arrival.close(); models.values.forEach { it.hit.close(); it.model.close() }; models.clear(); environment?.close(); environment=null
        root.destroy(); sparkMaterial.close(); sparkMesh.close(); library.close()
    }
    companion object { private const val TAG="BugWorldGarden" }
}
