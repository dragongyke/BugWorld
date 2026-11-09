package com.bugworld.app.interaction

/** A native click selects exactly one insect. A hand pose alone never chooses another resident. */
class GardenSelection {
    var selected: String?=null; private set
    var preferredHand: HandSide?=null; private set
    private var remaining=0f
    fun select(id: String,hand: HandSide?=null) { selected=id; preferredHand=hand; remaining=12f }
    fun tick(delta: Float,available: Set<String>) {
        remaining-=delta
        if(remaining<=0f || selected !in available) clear()
    }
    fun consume(): String? = selected.also { clear() }
    fun clear() { selected=null; preferredHand=null; remaining=0f }
}
