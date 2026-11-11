package com.bugworld.app.drawing

import com.bugworld.app.data.Species
import kotlin.math.*

/** Pure pixel transfer used by both Android and asset regression tests. */
class ArtworkRasterMapper(val species: Species, val width: Int, val height: Int,
                          private val regions: IntArray, private val ink: IntArray,
                          private val detail: ByteArray? = null) {
    data class Point(val x: Float, val y: Float)
    init { require(width > 0 && height > 0 && regions.size == width*height && ink.size == regions.size)
        require(detail == null || detail.size == regions.size) }
    private val shapes by lazy { (1..(regions.maxOrNull() ?: 0)).associateWith { RegionShape(width,height,regions,it) } }
    private val bindings = materialMeshes(species)
    private var projectionSize = 0
    private var projections = emptyMap<String,IntArray>()

    /** u/v are exported glTF coordinates. In a Bitmap, row zero corresponds to glTF v=0. */
    fun sourcePoint(material: String, u: Float, v: Float): Point {
        require(u.isFinite() && v.isFinite())
        require(material in bindings) { "Unknown paint material: $material" }
        val x = u.coerceIn(0f,1f); val y = v.coerceIn(0f,1f)
        return when (species) {
            Species.DRAGONFLY, Species.HONEYBEE, Species.ANT, Species.GRASSHOPPER ->
                Point(x*width-.5f,y*height-.5f)
            Species.BUTTERFLY -> {
                // Same approved source coordinates serve both atlas halves; never mirror one painting onto the other.
                val sourceX = 251f + (x-.5f)*600f
                val sourceY = 190f + (y-.495f)*600f
                Point((64f+sourceX*1.77075099f)*width/1024f-.5f,
                    (181.754941f+sourceY*1.77075099f)*height/1024f-.5f)
            }
            Species.BEETLE -> when (material) {
                "left_green_elytron", "right_green_elytron" -> {
                    val shape = shapes.getValue(1)
                    val px = shape.left + x*(shape.right-shape.left)
                    val (top,bottom) = shape.column(px)
                    val h = cos((1f-y)*PI/2).pow(.94).toFloat()
                    Point(px,bottom-(bottom-top)*h)
                }
                "lavender_pronotum" -> shapes.getValue(2).rectangle(x,y)
                else -> shapes.getValue(3).rectangle(x,y)
            }
            Species.LADYBUG -> when (material) {
                "left_pink_wax", "right_mint_wax" -> {
                    val left = material == "left_pink_wax"
                    val shape = shapes.getValue(if (left) 1 else 2)
                    val py = shape.bottom-x*(shape.bottom-shape.top)
                    val (lo,hi) = shape.row(py)
                    val across = sin((1f-y)*PI/2).toFloat()
                    Point(if (left) hi-(hi-lo)*across else lo+(hi-lo)*across,py)
                }
                "ivory_collar_with_brown_smudge" -> {
                    val shape = shapes.getValue(4)
                    val across = (sin(-PI/2+PI*(1-y))+1).toFloat()/2
                    val px = shape.left+across*(shape.right-shape.left)
                    val (top,bottom) = shape.column(px)
                    Point(px,bottom-x*(bottom-top))
                }
                else -> {
                    // Head is an ellipsoid: exported V runs rear-to-front and U wraps around its long axis.
                    val shape = shapes.getValue(3)
                    val py = shape.bottom-y*(shape.bottom-shape.top)
                    val (left,right) = shape.row(py)
                    Point(left+(right-left)*(cos(2*PI*x)+1).toFloat()/2,py)
                }
            }
            Species.CATERPILLAR -> {
                val limits = CATERPILLAR_INTERVALS
                val index = (0 until limits.lastIndex).firstOrNull { x < limits[it+1] } ?: limits.lastIndex-1
                val shape = shapes.getValue(index+1)
                val along = (x-limits[index])/(limits[index+1]-limits[index])
                val px = shape.left+along*(shape.right-shape.left)
                val (top,bottom) = shape.column(px)
                // j=24/96 is dorsal, j=72/96 ventral in the actual continuous cuticle mesh.
                val down = (1-sin(2*PI*y)).toFloat()/2
                shape.pigmentPoint(px,top+(bottom-top)*down)
            }
        }
    }

    fun sample(material: String, u: Float, v: Float, pigment: IntArray): Int {
        val point = sourcePoint(material,u,v)
        val x = point.x.roundToInt(); val y = point.y.roundToInt()
        if (x !in 0 until width || y !in 0 until height) return PaintDocument.PAPER
        return colorAt(y*width+x,pigment)
    }

    private fun colorAt(index: Int,pigment: IntArray): Int {
        if (index<0) return PaintDocument.PAPER
        val base = if (regions[index] == 0 || pigment[index] ushr 24 == 0) PaintDocument.PAPER else pigment[index]
        // The side-view silhouette folds onto the dorsal/ventral ridge in this wrap.
        // Transfer only player pigment; eyes and feet already have separate model materials.
        if (species == Species.CATERPILLAR) return base
        val relief=detail ?: return over(ink[index],base)
        val tone=relief[index].toInt() and 255
        fun channel(shift:Int) = (((base ushr shift and 255)*tone+64) / 128).coerceAtMost(255)
        val shaded=(255 shl 24) or (channel(16) shl 16) or (channel(8) shl 8) or channel(0)
        // Keep the paper's locked silhouette out of the grasshopper's cuticle texture.
        return if (species == Species.GRASSHOPPER) shaded else over(ink[index],shaded)
    }

    @Synchronized
    fun mapPixels(pigment: IntArray, size: Int = 1024): Map<String, IntArray> {
        require(pigment.size == width*height && size > 0)
        val sheet = species.sheetMaterial
        if (sheet != null && size == width && size == height) {
            return mapOf(sheet to IntArray(pigment.size) { colorAt(it,pigment) })
        }
        val rows = if (species == Species.CATERPILLAR) max(1,size/2) else size
        if (projectionSize != size) {
            projections = bindings.keys.associateWith { material ->
                IntArray(size*rows) { i ->
                    val point = sourcePoint(material,(i%size+.5f)/size,(i/size+.5f)/rows)
                    val x=point.x.roundToInt(); val y=point.y.roundToInt()
                    if (x in 0 until width && y in 0 until height) y*width+x else -1
                }
            }
            projectionSize=size
        }
        return projections.mapValues { (_,projection) -> IntArray(projection.size) { colorAt(projection[it],pigment) } }
    }

    companion object {
        private val CATERPILLAR_INTERVALS = floatArrayOf(0f,.06f,.165f,.27f,.375f,.48f,.585f,.69f,.795f,.9f,1f)
        /** Limit a replacement to these meshes, especially when the original GLB shares the material. */
        fun materialMeshes(species: Species): Map<String, Set<String>> = when (species) {
            Species.DRAGONFLY, Species.HONEYBEE, Species.ANT, Species.GRASSHOPPER ->
                mapOf(requireNotNull(species.sheetMaterial) to setOf("PaperSurface"))
            Species.BUTTERFLY -> mapOf("Continuous wax pigment • image PBR" to setOf(
                "L_forewing_closed_membrane","R_forewing_closed_membrane","L_hindwing_closed_membrane","R_hindwing_closed_membrane"))
            Species.CATERPILLAR -> mapOf("Continuous wax pigment • image PBR" to setOf("ONE continuous wrinkled soft cuticle"))
            Species.BEETLE -> mapOf("left_green_elytron" to setOf("elytron_L"), "right_green_elytron" to setOf("elytron_R"),
                "lavender_pronotum" to setOf("pronotum_and_short_horn"), "warm_ivory_wax" to setOf("head_and_recurved_horn"))
            Species.LADYBUG -> mapOf("left_pink_wax" to setOf("elytron_L"),"right_mint_wax" to setOf("elytron_R"),
                "warm_brown_cuticle" to setOf("head"),"ivory_collar_with_brown_smudge" to setOf("pronotum"))
        }
        private fun over(ink: Int, base: Int): Int {
            val alpha = ink ushr 24
            if (alpha == 0) return base or -16777216
            if (alpha == 255) return ink
            var result = -16777216
            for (shift in 16 downTo 0 step 8) {
                val channel = ((ink ushr shift and 255)*alpha+(base ushr shift and 255)*(255-alpha)+127)/255
                result = result or (channel shl shift)
            }
            return result
        }
    }
}

/** Scanline envelopes include locked holes, so a black spot cannot shrink a curved shell. */
internal class RegionShape(private val width: Int, private val height: Int,
                           private val regions: IntArray, private val id: Int) {
    var left = width; private set
    var right = -1; private set
    var top = height; private set
    var bottom = -1; private set
    private val rowMin = IntArray(height) { width }; private val rowMax = IntArray(height) { -1 }
    private val colMin = IntArray(width) { height }; private val colMax = IntArray(width) { -1 }
    init {
        for (i in regions.indices) if (regions[i] == id && id != 0 || id == 0 && regions[i] != 0) {
            val x = i%width; val y = i/width
            left=min(left,x); right=max(right,x); top=min(top,y); bottom=max(bottom,y)
            rowMin[y]=min(rowMin[y],x); rowMax[y]=max(rowMax[y],x)
            colMin[x]=min(colMin[x],y); colMax[x]=max(colMax[x],y)
        }
        require(right >= left && bottom >= top) { "Missing drawing region $id" }
    }
    fun rectangle(u: Float,v: Float) = ArtworkRasterMapper.Point(left+u*(right-left),top+v*(bottom-top))
    /** Extend pigment through locked eye/outline holes without copying the paper's ink to skin. */
    fun pigmentPoint(x: Float,y: Float): ArtworkRasterMapper.Point {
        val ix=x.roundToInt().coerceIn(left,right); val iy=y.roundToInt().coerceIn(top,bottom)
        if (regions[iy*width+ix]==id) return ArtworkRasterMapper.Point(x,y)
        for (distance in 1..bottom-top) {
            val above=iy-distance; val below=iy+distance
            if (above>=top && regions[above*width+ix]==id) return ArtworkRasterMapper.Point(ix.toFloat(),above.toFloat())
            if (below<=bottom && regions[below*width+ix]==id) return ArtworkRasterMapper.Point(ix.toFloat(),below.toFloat())
        }
        return ArtworkRasterMapper.Point(x,y)
    }
    fun row(y: Float): Pair<Float,Float> = span(y.roundToInt().coerceIn(top,bottom),rowMin,rowMax,top,bottom)
    fun column(x: Float): Pair<Float,Float> = span(x.roundToInt().coerceIn(left,right),colMin,colMax,left,right)
    private fun span(index: Int, lo: IntArray, hi: IntArray, min: Int, max: Int): Pair<Float,Float> {
        if (hi[index] >= 0) return lo[index].toFloat() to hi[index].toFloat()
        for (distance in 1..max-min) {
            val before = index-distance; val after = index+distance
            if (before>=min && hi[before]>=0) return lo[before].toFloat() to hi[before].toFloat()
            if (after<=max && hi[after]>=0) return lo[after].toFloat() to hi[after].toFloat()
        }
        error("Empty region")
    }
}
