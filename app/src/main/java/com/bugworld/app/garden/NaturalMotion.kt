package com.bugworld.app.garden

import com.bugworld.app.interaction.HandPoint

/** Y-up world position with native SDK Y-X-Z orientation, in degrees. */
data class NaturalPose(val point: HandPoint,val yaw: Float,val pitch: Float,val moving: Boolean,val roll: Float=0f,val airborne: Boolean=false,val hopPhase: Float?=null)
