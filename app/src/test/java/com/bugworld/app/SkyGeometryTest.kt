package com.bugworld.app

import com.bugworld.app.spatial.SkyGeometry
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class SkyGeometryTest {
    @Test fun everyNonDegenerateTriangleFacesTheViewerInsideTheSky() {
        val mesh=SkyGeometry.create(32f,32,16)
        var checked=0
        mesh.indices.toList().chunked(3).forEach { (a,b,c) ->
            fun p(i: Int,k: Int)=mesh.positions[i*3+k]
            val ab=FloatArray(3) { p(b,it)-p(a,it) }
            val ac=FloatArray(3) { p(c,it)-p(a,it) }
            val n=floatArrayOf(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
            if(n.sumOf { (it*it).toDouble() }>1e-8) {
                assertTrue("Sky triangle faces outward",(0..2).sumOf { (n[it]*p(a,it)).toDouble() }<0)
                checked++
            }
        }
        assertTrue(checked>800)
    }

    @Test fun panoramaPolesAndSeamHaveExplicitUvs() {
        val mesh=SkyGeometry.create(32f,32,16)
        assertEquals(0f,mesh.uv[1],0f)
        assertEquals(32f,mesh.positions[1],.001f)
        assertEquals(1f,mesh.uv.last(),0f)
        assertEquals(-32f,mesh.positions[mesh.positions.size-2],.001f)
        for(row in 0..16) {
            val first=row*33; val last=first+32
            for(k in 0..2) assertEquals(mesh.positions[first*3+k],mesh.positions[last*3+k],.0001f)
            assertEquals(0f,mesh.uv[first*2],0f)
            assertEquals(1f,mesh.uv[last*2],0f)
        }
    }
}
