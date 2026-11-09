package com.bugworld.app.spatial

import kotlin.math.*

/** Explicit inward winding and equirectangular UVs; independent of SDK primitive defaults. */
data class SkyGeometry(val positions: FloatArray,val uv: FloatArray,val indices: IntArray) {
    companion object {
        fun create(radius: Float,columns: Int=64,rows: Int=32): SkyGeometry {
            require(radius>0f && columns>=4 && rows>=2)
            val positions=FloatArray((columns+1)*(rows+1)*3)
            val uv=FloatArray((columns+1)*(rows+1)*2)
            val indices=ArrayList<Int>()
            for(y in 0..rows) for(x in 0..columns) {
                val u=x.toFloat()/columns; val v=y.toFloat()/rows
                val theta=(u-.5f)*2*PI; val phi=v*PI
                val i=y*(columns+1)+x
                // Matches the KTX converter's panorama_sample orientation.
                positions[i*3]=(-sin(theta)*sin(phi)*radius).toFloat()
                positions[i*3+1]=(cos(phi)*radius).toFloat()
                positions[i*3+2]=(cos(theta)*sin(phi)*radius).toFloat()
                uv[i*2]=u; uv[i*2+1]=v
                if(y<rows && x<columns) {
                    val a=i; val b=i+1; val c=i+columns+1; val d=c+1
                    if(y>0) indices.addAll(listOf(a,c,b))
                    if(y<rows-1) indices.addAll(listOf(b,c,d))
                }
            }
            return SkyGeometry(positions,uv,indices.toIntArray())
        }
    }
}
