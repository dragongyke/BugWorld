package com.bugworld.app.garden

import com.bugworld.app.interaction.HandPoint
import kotlin.math.*

/** One entry transform for render geometry AND interaction samples. Never follow the user's head. */
data class GardenPlacement(val x: Float=0f,val y: Float=0f,val z: Float=0f,val yaw: Float=0f) {
    fun local(point: HandPoint): HandPoint {
        val angle=yaw*PI.toFloat()/180f;val c=cos(angle);val s=sin(angle)
        val dx=point.x-x;val dz=point.z-z
        return HandPoint(c*dx-s*dz,point.y-y,s*dx+c*dz)
    }
    fun world(point: HandPoint): HandPoint {
        val angle=yaw*PI.toFloat()/180f;val c=cos(angle);val s=sin(angle)
        return HandPoint(x+c*point.x+s*point.z,y+point.y,z-s*point.x+c*point.z)
    }
}
