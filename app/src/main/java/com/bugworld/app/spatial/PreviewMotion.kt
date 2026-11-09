package com.bugworld.app.spatial

import com.bugworld.app.data.Species
import com.bugworld.app.garden.InsectAnimationController
import com.bugworld.app.garden.InsectAnimationFrame

/** Input owns touch cooldown; hidden frame clocks must not reject an accepted touch. */
class PreviewMotion(private val species: Species) {
    private var animation=InsectAnimationController(species)
    fun update(dt: Float,touch: Boolean): InsectAnimationFrame {
        // An accepted contact is an explicit new response. The preview never
        // flies or walks a route, so resetting this local controller is safe.
        // All four approved touch clips are scrubbed from frame.progress.
        if(touch) animation=InsectAnimationController(species)
        return animation.update(dt,reaction=if(touch) .7f else 0f)
    }
}
