package com.bugworld.app.drawing

import kotlin.math.roundToInt

/** Shape-aware transfer. The caller retains the original PNG as a lossless migration backup. */
object ArtworkMigration {
    fun migrate(sourceWidth: Int, sourceHeight: Int, source: IntArray,
                width: Int, height: Int, regions: IntArray,
                horizontalBody: Boolean, rotateClockwise: Boolean = false): IntArray {
        require(sourceWidth>0 && sourceHeight>0 && source.size==sourceWidth*sourceHeight)
        require(width>0 && height>0 && regions.size==width*height)
        val output = IntArray(width*height) { if (regions[it]==0) 0 else PaintDocument.PAPER }
        if (source.none { it ushr 24 != 0 } || regions.none { it!=0 }) return output
        val sw = if (rotateClockwise) sourceHeight else sourceWidth
        val sh = if (rotateClockwise) sourceWidth else sourceHeight
        val input = if (!rotateClockwise) source else IntArray(sw*sh) { i ->
            val oldX=i/sw; val oldY=sourceHeight-1-i%sw
            source[oldY*sourceWidth+oldX]
        }
        val sourceMask = IntArray(input.size) { if (input[it] ushr 24 == 0) 0 else 1 }
        val from = RegionShape(sw,sh,sourceMask,1)
        val to = RegionShape(width,height,regions,0)
        // Nearest opaque pixel for transparent holes and gaps, without retaining old template assets.
        val nearest = IntArray(input.size) { -1 }; val queue = IntArray(input.size)
        var read=0; var write=0
        for (i in input.indices) if (sourceMask[i]!=0) { nearest[i]=i; queue[write++]=i }
        while (read<write) {
            val i=queue[read++]
            fun visit(next: Int) { if (nearest[next]<0) { nearest[next]=nearest[i]; queue[write++]=next } }
            if (i%sw>0) visit(i-1)
            if (i%sw<sw-1) visit(i+1)
            if (i>=sw) visit(i-sw)
            if (i<input.size-sw) visit(i+sw)
        }
        fun fraction(value: Float, low: Float, high: Float) = if (high==low) .5f else (value-low)/(high-low)
        for (i in regions.indices) if (regions[i]!=0) {
            val x=(i%width).toFloat(); val y=(i/width).toFloat()
            val sx: Float; val sy: Float
            if (horizontalBody) {
                sx=from.left+fraction(x,to.left.toFloat(),to.right.toFloat())*(from.right-from.left)
                val (targetTop,targetBottom)=to.column(x); val (sourceTop,sourceBottom)=from.column(sx)
                sy=sourceTop+fraction(y,targetTop,targetBottom)*(sourceBottom-sourceTop)
            } else {
                sy=from.top+fraction(y,to.top.toFloat(),to.bottom.toFloat())*(from.bottom-from.top)
                val (targetLeft,targetRight)=to.row(y); val (sourceLeft,sourceRight)=from.row(sy)
                sx=sourceLeft+fraction(x,targetLeft,targetRight)*(sourceRight-sourceLeft)
            }
            val sourceIndex=sy.roundToInt().coerceIn(0,sh-1)*sw+sx.roundToInt().coerceIn(0,sw-1)
            output[i]=input[nearest[sourceIndex]]
        }
        return output
    }
}
