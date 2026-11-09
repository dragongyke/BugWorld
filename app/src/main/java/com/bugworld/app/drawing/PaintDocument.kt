package com.bugworld.app.drawing

import kotlin.math.*

class PaintDocument private constructor(val width: Int, val height: Int, val regions: IntArray,
                    val mirrorAxisX: Float, grain: ByteArray?) {
    constructor(width: Int, height: Int, regions: IntArray, mirrorAxisX: Float = (width-1)/2f) :
        this(width,height,regions,mirrorAxisX,null)
    companion object {
        const val PAPER = -1119259
        const val HISTORY_LIMIT = 24
        // Paper roughness depends on the dimensions and mirror axis, not the insect outline.
        private data class GrainKey(val width: Int,val height: Int,val axis: Float)
        private val relief = LinkedHashMap<GrainKey,ByteArray>()
        private fun grain(width:Int,height:Int,axis:Float,build:()->ByteArray): ByteArray {
            if (width!=1024 || height!=1024) return build()
            synchronized(relief) {
                val key=GrainKey(width,height,axis)
                relief[key]?.let { return it }
                if (relief.size>=2) relief.remove(relief.keys.first())
                return build().also { relief[key]=it }
            }
        }
    }
    init { require(width > 0 && height > 0 && regions.size == width * height && mirrorAxisX.isFinite()) }
    var pixels = IntArray(width * height) { if (regions[it] == 0) 0 else PAPER }
        private set
    private val past = ArrayDeque<IntArray>()
    private val future = ArrayDeque<IntArray>()
    // At 1024, snapshots otherwise consume 96 MiB. Small legacy documents still get 24 steps.
    private val historyLimit = min(HISTORY_LIMIT, max(1, 32 * 1024 * 1024 / (width * height * 4)))
    private val paperScale = (min(width, height) / 1024f).coerceAtLeast(.5f)
    private val paperGrain = grain ?: Companion.grain(width,height,mirrorAxisX) { ByteArray(width * height) { index ->
        // Fixed paper coordinates, including when a stroke is mirrored or a saved PNG is restored.
        // Symmetric paper relief makes the two wings receive exactly the same material.
        val x = min(index % width, mirroredX(index % width)) / paperScale
        val y = index / width / paperScale
        val grain = .38f * noise(x / 2.2f, y / 2.4f) +
            .20f * noise((x + y * .48f) / 6f, (y - x * .18f) / 1.8f) +
            .16f * noise((x - y * .7f) / 1.7f, (y + x * .7f) / 5f) +
            .08f * random(floor(x).toInt(), floor(y).toInt()) +
            .18f * noise(x / 18f, y / 18f)
        (((grain-.5f)*1.35f+.5f).coerceIn(0f,1f) * 255).roundToInt().toByte()
    } }
    private var lastX = Double.NaN
    private var lastY = Double.NaN
    private var distanceToNext = 0.0
    private var previousRadius = 0f
    private var previousColor = 0
    private var previousMirror = false
    private var previousErase = false
    private var previousStrength = 0f
    val canUndo get() = past.isNotEmpty()
    val canRedo get() = future.isNotEmpty()
    internal val historyBytes get() = (past.size.toLong()+future.size)*width*height*Int.SIZE_BYTES
    internal fun discardDistantHistory() {
        if (past.isNotEmpty()) past.removeFirst() else future.removeFirst()
    }

    /** Paper relief is immutable; new sheets share it but never pixels or undo history. */
    fun blankCopy() = PaintDocument(width,height,regions,mirrorAxisX,paperGrain)

    fun beginStroke() {
        past.addLast(pixels.copyOf())
        if (past.size > historyLimit) past.removeFirst()
        future.clear()
        resetSampling()
    }

    fun stroke(x0: Float, y0: Float, x1: Float, y1: Float, radius: Float, color: Int, mirror: Boolean, erase: Boolean, strength: Float = .5f) {
        if (!x0.isFinite() || !y0.isFinite() || !x1.isFinite() || !y1.isFinite() ||
            !radius.isFinite() || !strength.isFinite() || radius <= 0f) return
        val pressure = strength.coerceIn(0f, 1f)
        val dx = x1.toDouble() - x0
        val dy = y1.toDouble() - y0
        val length = hypot(dx, dy)
        val directionX = if (length > 0.0) (dx / length).toFloat() else 1f
        val directionY = if (length > 0.0) (dy / length).toFloat() else 0f
        val spacing = max(.5, radius * .16)
        val continuous = abs(lastX - x0) < .001 && abs(lastY - y0) < .001 &&
            previousRadius == radius && previousColor == color && previousMirror == mirror &&
            previousErase == erase && previousStrength == pressure
        if (!continuous) {
            stamp(x0,y0,radius,color,mirror,erase,pressure,directionX,directionY,spacing.toFloat())
            distanceToNext = spacing
        }
        // Carry the unused distance across calls. Event boundaries never add extra end stamps.
        var distance = distanceToNext
        while (length > 0.0 && distance <= length + 1e-7) {
            val t = (distance / length).coerceAtMost(1.0)
            val x = ((x0 + dx * t) * 4096).roundToInt() / 4096f
            val y = ((y0 + dy * t) * 4096).roundToInt() / 4096f
            stamp(x,y,radius,color,mirror,erase,pressure,directionX,directionY,spacing.toFloat())
            distance += spacing
        }
        distanceToNext = distance - length
        lastX = x1.toDouble(); lastY = y1.toDouble()
        previousRadius = radius; previousColor = color; previousMirror = mirror
        previousErase = erase; previousStrength = pressure
    }

    private fun stamp(x: Float, y: Float, radius: Float, color: Int, mirror: Boolean, erase: Boolean,
                      strength: Float, directionX: Float, directionY: Float, spacing: Float) {
        val left = max(0, floor(x-radius).toInt())
        val right = min(width-1, ceil(x+radius).toInt())
        val pointPressure = (1f-radius/3f).coerceAtLeast(0f) * .28f
        val stepRatio = spacing/radius
        for (iy in max(0, floor(y-radius).toInt())..min(height-1, ceil(y+radius).toInt())) {
            for (ix in left..right) {
                val otherX = mirroredX(ix)
                val hasOther = mirror && otherX in 0 until width
                if (hasOther && ix > otherX && otherX in left..right) continue
                val index = iy * width + ix
                val otherIndex = if (hasOther) iy * width + otherX else -1
                if (regions[index] == 0 && (!hasOther || regions[otherIndex] == 0)) continue
                var contact = tipContact(ix-x,iy-y,radius,erase,directionX,directionY,ix,iy)
                // Union the two impressions before depositing. Crossing the centre never doubles wax.
                if (hasOther && otherX in left..right) contact = max(contact,
                    tipContact(otherX-x,iy-y,radius,erase,directionX,directionY,otherX,iy))
                if (contact <= 0f) continue
                if (regions[index] != 0) deposit(index,color,erase,strength,contact,stepRatio,pointPressure)
                if (hasOther && otherIndex != index && regions[otherIndex] != 0)
                    deposit(otherIndex,color,erase,strength,contact,stepRatio,pointPressure)
            }
        }
    }

    private fun tipContact(dx: Float, dy: Float, radius: Float, erase: Boolean,
                           directionX: Float, directionY: Float, x: Int, y: Int): Float {
        val squared = (dx*dx + dy*dy) / (radius*radius)
        if (squared > 1f) return 0f
        if (erase) return 1f
        val across = abs(-dx * directionY + dy * directionX) / paperScale
        val along = (x * directionX + y * directionY) / paperScale
        // Long, broken striations follow the drag direction; they are not fresh random dots per stamp.
        val groove = ((noise(along / 20f, across / 1.8f)-.18f)/.7f).coerceIn(0f,1f)
        val edge = ((1f - squared) * 4f - .25f * groove).coerceIn(0f,1f)
        return edge * (.10f + .90f * groove * groove)
    }

    private fun deposit(index: Int, color: Int, erase: Boolean, strength: Float, contact: Float, stepRatio: Float, pointPressure: Float) {
        if (erase) { pixels[index] = PAPER; return }
        val old = pixels[index]
        val relief = (paperGrain[index].toInt() and 255) / 255f
        // Derive wax loading from the saved pixels, so undo/reload needs no hidden pigment buffer.
        val wax = max(abs((old ushr 16 and 255) - (PAPER ushr 16 and 255)),
            max(abs((old ushr 8 and 255) - (PAPER ushr 8 and 255)), abs((old and 255) - (PAPER and 255)))) / 255f
        // A sharpened tip concentrates force and can reach valleys that a broad wax side skips.
        val tooth = max(pointPressure,
            ((relief - (.47f - strength * .17f) + wax * .10f + pointPressure) * 5f).coerceIn(0f,1f))
        val alpha = (stepRatio * (2f + strength * 3.5f) * contact * tooth).coerceIn(0f,.65f)
        if (alpha <= 0f) return
        // Even burnished wax retains the relief of the paper instead of converging to a flat fill.
        val pigment = .86f + relief * .14f
        var value = -16777216
        for (shift in 16 downTo 0 step 8) {
            val before = old ushr shift and 255
            val paper = PAPER ushr shift and 255
            val target = paper + ((color ushr shift and 255) - paper) * pigment
            value = value or ((before + (target - before) * alpha).roundToInt().coerceIn(0,255) shl shift)
        }
        pixels[index] = value
    }

    private fun resetSampling() { lastX = Double.NaN; lastY = Double.NaN; distanceToNext = 0.0 }
    private fun mirroredX(x: Int) = (2*mirrorAxisX-x).roundToInt()

    private fun random(x: Int, y: Int): Float {
        var n = x * 374761393 + y * 668265263 + 1442695041
        n = (n xor (n ushr 13)) * 1274126177
        return ((n xor (n ushr 16)) ushr 8) / 16777215f
    }

    private fun noise(x: Float, y: Float): Float {
        val ix = floor(x).toInt(); val iy = floor(y).toInt()
        val fx = x-ix; val fy = y-iy
        val u = fx*fx*(3f-2f*fx); val v = fy*fy*(3f-2f*fy)
        val a = random(ix,iy); val b = random(ix+1,iy)
        val c = random(ix,iy+1); val d = random(ix+1,iy+1)
        return (a+(b-a)*u)*(1f-v)+(c+(d-c)*u)*v
    }

    fun fill(x: Int, y: Int, color: Int, mirror: Boolean = false) {
        if (x !in 0 until width || y !in 0 until height) return
        val region = regions[y * width + x]
        if (region == 0) return
        val reflectedX = mirroredX(x)
        val other = if(mirror && reflectedX in 0 until width) regions[y * width + reflectedX] else region
        beginStroke()
        for(index in pixels.indices) if(regions[index] == region || other != 0 && regions[index] == other) pixels[index] = color
    }
    fun undo() { if (canUndo) { future.addLast(pixels); pixels = past.removeLast(); resetSampling() } }
    fun redo() { if (canRedo) { past.addLast(pixels); pixels = future.removeLast(); resetSampling() } }
    fun restore(input: IntArray) {
        require(input.size == pixels.size)
        pixels = input.copyOf()
        past.clear(); future.clear(); resetSampling()
    }
}
