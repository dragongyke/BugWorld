package com.bugworld.app.drawing

/** One physical gesture keeps its original document and tools, even if another window changes them. */
class PaintGesture(
    val document: PaintDocument,
    x: Float,
    y: Float,
    private val radius: Float,
    private val color: Int,
    private val mirror: Boolean,
    private val erase: Boolean,
    private val strength: Float,
) {
    private var oldX = x
    private var oldY = y
    init { document.beginStroke(); append(x,y) }

    fun append(x: Float, y: Float) {
        if (!x.isFinite() || !y.isFinite()) return
        document.stroke(oldX,oldY,x,y,radius,color,mirror,erase,strength)
        oldX = x; oldY = y
    }

    fun appendBatch(historySize: Int, historicalX: (Int) -> Float, historicalY: (Int) -> Float, x: Float, y: Float) {
        for (i in 0 until historySize) append(historicalX(i),historicalY(i))
        append(x,y)
    }
}
