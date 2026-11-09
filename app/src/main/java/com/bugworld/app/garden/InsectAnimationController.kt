package com.bugworld.app.garden

import com.bugworld.app.data.Species
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin

enum class InsectAction { IDLE, WALK, TURN, TOUCH, TAKEOFF, FLIGHT, LAND, PERCH, CRAWL, EXPLORE, RECOIL, GROOM, HOP }

/** Local animation only. World movement and contact anchors remain owned by GardenRuntime. */
data class InsectAnimationFrame(
    val species: Species,
    val action: InsectAction = InsectAction.IDLE,
    val progress: Float = 0f,
    val elapsedSeconds: Float = 0f,
    val gaitPhase: Float = 0f,
    val wingPhase: Float = 0f,
    val motion: Float = 0f,
    val turn: Float = 0f,
    val flightBlend: Float = 0f,
    val shellOpen: Float = 0f,
    val reaction: Float = 0f,
    val open: Boolean = false,
    val exploration: Float = 0f
)

class InsectAnimationController(private val species: Species, seed: Float = 0f) {
    private val variation = if(seed.isFinite()) seed.coerceIn(0f,1f) else 0f
    private var elapsed = variation * 6f
    private var action = InsectAction.IDLE
    private var age = 0f
    private var idleTime = 0f
    private var antGroomNext = true
    private var cooldown = 0f
    private var previousReaction = 0f
    private var gait = variation * TAU
    private var wing = variation * TAU
    private var flight = 0f
    private var shell = 0f
    private var startFlight = 0f
    private var startShell = 0f
    private var turn = 0f

    private fun enter(next: InsectAction) {
        if(action == next) return
        action = next; age = 0f
        startFlight = flight; startShell = shell
    }

    private fun duration(): Float = when(action) {
        InsectAction.TAKEOFF -> when(species) { Species.BUTTERFLY -> .7f; Species.LADYBUG -> .9f; else -> 1.15f }
        InsectAction.LAND -> when(species) { Species.BUTTERFLY -> .8f; Species.LADYBUG -> .95f; else -> 1.2f }
        InsectAction.TOUCH -> 1.8f
        InsectAction.RECOIL -> 1.8f
        InsectAction.EXPLORE, InsectAction.GROOM -> 1.8f
        else -> 1f
    }

    fun update(deltaSeconds: Float, moving: Boolean = false, turning: Float = 0f,
        flying: Boolean = false, onHand: Boolean = false, reaction: Float = 0f,
        open: Boolean = false, retiring: Boolean = false, speedFactor: Float = 1f): InsectAnimationFrame {
        // A resumed frame must not skip contact/wing transitions or poison the phase clock.
        val dt = if(deltaSeconds.isFinite()) deltaSeconds.coerceIn(0f,.1f) else 0f
        val speed = if(speedFactor.isFinite()) speedFactor.coerceIn(0f,2f) else 0f
        val requestedTurn = if(turning.isFinite()) turning.coerceIn(-1f,1f) else 0f
        val touch = if(reaction.isFinite()) reaction.coerceIn(0f,1f) else 0f
        elapsed += dt; age += dt; cooldown = (cooldown-dt).coerceAtLeast(0f)
        val newTouch = touch >= .6f && previousReaction < .6f && cooldown == 0f
        previousReaction = touch
        val canFly = species.canFly
        val wantsFlight = canFly && (retiring || flying && !onHand)
        val flightAction = action in FLIGHT_ACTIONS

        when {
            wantsFlight && (action == InsectAction.LAND || !flightAction) -> enter(InsectAction.TAKEOFF)
            !wantsFlight && (action == InsectAction.TAKEOFF || action == InsectAction.FLIGHT) -> enter(InsectAction.LAND)
            action == InsectAction.TAKEOFF && age >= duration() -> enter(InsectAction.FLIGHT)
            action == InsectAction.LAND && age >= duration() -> enter(if(onHand) InsectAction.PERCH else InsectAction.IDLE)
        }

        if(action !in FLIGHT_ACTIONS) {
            if(newTouch && !retiring) {
                enter(if(species == Species.CATERPILLAR && touch>=.9f) InsectAction.RECOIL else InsectAction.TOUCH)
                cooldown = 2f; idleTime = 0f
            }
            val responding = action == InsectAction.TOUCH || action == InsectAction.RECOIL
            if(!responding || age >= duration() || retiring) {
                val walking = moving && speed > .01f && !onHand
                idleTime = if(walking || onHand) 0f else idleTime + dt
                val next = when {
                    onHand -> InsectAction.PERCH
                    abs(requestedTurn) > .18f && walking -> InsectAction.TURN
                    walking -> if(species == Species.CATERPILLAR) InsectAction.CRAWL else InsectAction.WALK
                    species == Species.ANT && (action == InsectAction.GROOM || action == InsectAction.EXPLORE) && age < duration() -> action
                    species == Species.ANT && idleTime > 2.5f -> {
                        idleTime = 0f
                        val nextIdle = if (antGroomNext) InsectAction.GROOM else InsectAction.EXPLORE
                        antGroomNext = !antGroomNext
                        nextIdle
                    }
                    species == Species.CATERPILLAR && action == InsectAction.EXPLORE && age < duration() -> InsectAction.EXPLORE
                    species == Species.CATERPILLAR && idleTime > 3.4f + variation * 1.6f -> {
                        idleTime = 0f; InsectAction.EXPLORE
                    }
                    else -> InsectAction.IDLE
                }
                enter(next)
            }
        } else idleTime = 0f

        val progress = (age / duration()).coerceIn(0f,1f)
        when(action) {
            InsectAction.TAKEOFF -> {
                shell = startShell + (1f-startShell) * smooth(progress/.35f)
                flight = startFlight + (1f-startFlight) * smooth((progress-.3f)/.7f)
            }
            InsectAction.FLIGHT -> { shell = 1f; flight = 1f }
            InsectAction.LAND -> {
                flight = startFlight * (1f-smooth(progress/.6f))
                shell = startShell * (1f-smooth((progress-.65f)/.35f))
            }
            else -> { shell = 0f; flight = 0f }
        }
        val motion = if(action in GROUND_MOTION) speed else 0f
        val stridePeriod = when(species) {
            Species.BUTTERFLY -> .8f; Species.LADYBUG -> .62f
            Species.BEETLE -> 1.08f; Species.CATERPILLAR -> 1.7f
            Species.DRAGONFLY -> .86f; Species.HONEYBEE -> .64f
            Species.ANT -> .50f; Species.GRASSHOPPER -> .92f
        }
        gait = (gait + dt * motion * TAU / stridePeriod) % TAU
        wing = (wing + dt * TAU * if(species == Species.BUTTERFLY) 4.6f else 10.5f) % TAU
        turn += (requestedTurn-turn) * (dt*7f).coerceAtMost(1f)
        val response = if(action == InsectAction.TOUCH || action == InsectAction.RECOIL) {
            if(progress < .18f) smooth(progress/.18f) else 1f-smooth((progress-.18f)/.82f)
        } else 0f
        return InsectAnimationFrame(species,action,progress,elapsed,gait,wing,motion,turn,
            flight,shell,response,open,
            if(action == InsectAction.EXPLORE) sin(progress * PI.toFloat()) else 0f)
    }

    companion object {
        private const val TAU = 6.2831853f
        private val FLIGHT_ACTIONS = setOf(InsectAction.TAKEOFF,InsectAction.FLIGHT,InsectAction.LAND)
        private val GROUND_MOTION = setOf(InsectAction.WALK,InsectAction.TURN,InsectAction.CRAWL)
        private fun smooth(value: Float): Float = value.coerceIn(0f,1f).let { it*it*(3f-2f*it) }
    }
}
