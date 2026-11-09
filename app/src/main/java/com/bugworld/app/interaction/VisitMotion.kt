package com.bugworld.app.interaction

/** Invitation state independent of a temporary touch-animation hold. */
class VisitMotion {
    var approaching=false; private set
    var returning=false; private set
    fun target(hand: HandPoint?,current: HandPoint,home: HandPoint,reacting: Boolean): HandPoint {
        if(approaching && hand==null) returning=true
        approaching=hand!=null
        if(approaching) returning=false
        // Only reaching HOME completes the return, not reaching a temporary reaction target.
        if(returning && current.distance(home)<.007f) returning=false
        return hand ?: if(reacting) current else home
    }
}
