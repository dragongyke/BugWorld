package com.bugworld.app.interaction

import kotlin.math.sqrt

data class HandPoint(val x: Float,val y: Float,val z: Float) {
    operator fun plus(b: HandPoint)=HandPoint(x+b.x,y+b.y,z+b.z)
    operator fun minus(b: HandPoint)=HandPoint(x-b.x,y-b.y,z-b.z)
    operator fun times(k: Float)=HandPoint(x*k,y*k,z*k)
    fun dot(b: HandPoint)=x*b.x+y*b.y+z*b.z
    fun cross(b: HandPoint)=HandPoint(y*b.z-z*b.y,z*b.x-x*b.z,x*b.y-y*b.x)
    fun unit(): HandPoint? {
        val length=sqrt(dot(this))
        return if(length.isFinite() && length>.00001f) this*(1f/length) else null
    }
    val finite get()=x.isFinite() && y.isFinite() && z.isFinite()
}
fun HandPoint.distance(other: HandPoint)=(this-other).let { sqrt(it.dot(it)) }
