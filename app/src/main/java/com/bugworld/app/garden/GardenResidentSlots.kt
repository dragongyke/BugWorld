package com.bugworld.app.garden

import com.bugworld.app.data.Artwork
import com.bugworld.app.data.Species

object GardenResidentSlots {
    data class Placement(val work: Artwork,val slot: Int)

    /** Keep visible residents on their route. Assign each newcomer to the least used
     * route of its species, preferring the forward route when the counts are equal. */
    fun plan(requested: List<Artwork>,arrivingId: String?,occupied: Map<String,Int> = emptyMap()): List<Placement> {
        val unique=requested.distinctBy { it.id }
        val arriving=unique.find { it.id==arrivingId }
        val retiring=if(unique.size>10) unique.first { it.id!=arrivingId } else null
        val counts=Species.entries.associateWith { IntArray(ApprovedGardenRoutes.count(it)) }
        val slots=mutableMapOf<String,Int>()
        for(work in unique) occupied[work.id]?.let { index ->
            slots[work.id]=index
            counts.getValue(work.species)[index]++
        }
        // Reopening Stage reconstructs previous occupants first, in durable album order.
        // A newly appended work therefore takes the second/third route on subsequent visits.
        val order=if(retiring!=null && arriving!=null) unique.filter { it.id!=arriving.id }+arriving else unique
        for(work in order) {
            if(work==arriving && retiring!=null)
                counts.getValue(retiring.species)[slots.getValue(retiring.id)]--
            if(work.id !in slots) {
                val usage=counts.getValue(work.species)
                val index=usage.indices.minBy { usage[it] }
                slots[work.id]=index
                usage[index]++
            }
        }
        // Preload the release first, while leaving traffic admission in chronological order.
        val preload=if(arriving==null) unique else listOf(arriving)+unique.filter { it.id!=arriving.id }
        return preload.map { Placement(it,slots.getValue(it.id)) }
    }
}

/** A shared clock preserves separation during rests, hand visits, returns and repeated laps.
 * A resident starts at the physical spawn only as its free phase passes that point. */
class GardenRouteTraffic(species: Species) {
    private val period=ApprovedGardenRoutes.period(species)
    private val seats=arrayOfNulls<String>(ApprovedGardenRoutes.seats(species))
    private val interval=period/seats.size
    private var clock=0f
    private var step=0f
    var held=false

    fun advance(delta: Float) {
        step=if(held) 0f else delta.coerceIn(0f,.05f)
        clock=(clock+step)%period
    }
    fun depart(id: String) {
        val seat=seats.indexOf(id)
        if(seat>=0) seats[seat]=null
    }
    fun admit(id: String): Boolean {
        if(id in seats) return true
        if(seats.all { it==null }) {
            clock=0f
            seats[0]=id
            return true
        }
        if(held) return false
        for(i in seats.indices) {
            val phase=i*interval
            if(seats[i]==null && elapsed(phase)<=step+.0001f) {
                // Snap this frame to the crossing. Other residents move at most one frame less.
                clock=phase
                seats[i]=id
                return true
            }
        }
        return false
    }
    fun routeTime(id: String): Float {
        val seat=seats.indexOf(id)
        check(seat>=0)
        return elapsed(seat*interval)
    }
    private fun elapsed(phase: Float): Float {
        val difference=clock-phase
        return if(difference<0f) difference+period else difference
    }
}
