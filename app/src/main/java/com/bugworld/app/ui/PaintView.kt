package com.bugworld.app.ui

import android.content.Context
import android.graphics.*
import android.view.MotionEvent
import android.view.View
import com.bugworld.app.BugWorldState
import com.bugworld.app.PaintTool
import com.bugworld.app.data.Species
import com.bugworld.app.drawing.PaintGesture
import com.bugworld.app.drawing.PaintDocument

class PaintView(context: Context, var state: BugWorldState) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val destination = RectF()
    private var image: Bitmap? = null
    private var uploadedDocument: PaintDocument? = null
    private var uploadedRevision = -1
    private var gesture: PaintGesture? = null
    private var pointerId = MotionEvent.INVALID_POINTER_ID
    init { contentDescription = context.getString(com.bugworld.app.R.string.paint_canvas); isFocusable = true }
    fun refresh() {
        val document = state.document
        if(uploadedDocument===document && uploadedRevision==state.revision && image!=null) return
        if (image?.width != document.width || image?.height != document.height) {
            image?.recycle(); image = Bitmap.createBitmap(document.width, document.height, Bitmap.Config.ARGB_8888)
        }
        image!!.setPixels(document.pixels,0,document.width,0,0,document.width,document.height)
        uploadedDocument=document; uploadedRevision=state.revision
        invalidate()
    }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.rgb(245,239,228))
        val document = state.document
        val scale = minOf(width.toFloat()/document.width,height.toFloat()/document.height)
        val paperWidth = document.width*scale; val paperHeight = document.height*scale
        destination.set((width-paperWidth)/2,(height-paperHeight)/2,(width+paperWidth)/2,(height+paperHeight)/2)
        image?.let { canvas.drawBitmap(it,null,destination,paint) }
        canvas.drawBitmap(state.template.outline,null,destination,paint)
    }
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (gesture != null && (state.busy || gesture?.document !== state.document)) finishGesture()
        if (state.busy || !state.ready || destination.width() <= 0) return false
        val doc = state.document
        val x = (event.x-destination.left)/destination.width()*doc.width
        val y = (event.y-destination.top)/destination.height()*doc.height
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                if (!destination.contains(event.x,event.y)) return false
                parent?.requestDisallowInterceptTouchEvent(true)
                if (state.tool == PaintTool.FILL) {
                    doc.fill(x.toInt(),y.toInt(),state.color,state.mirror && state.species == Species.BUTTERFLY)
                    state.strokeFinished(); refresh(); performClick()
                    parent?.requestDisallowInterceptTouchEvent(false)
                    return true
                }
                pointerId = event.getPointerId(0)
                gesture = PaintGesture(doc,x,y,state.radius,state.color,
                    state.mirror && state.species == Species.BUTTERFLY,state.tool == PaintTool.ERASER,state.brushStrength)
                state.changed(); refresh()
            }
            MotionEvent.ACTION_MOVE -> appendEvent(event)
            MotionEvent.ACTION_POINTER_UP -> if (event.getPointerId(event.actionIndex) == pointerId) {
                appendEvent(event); finishGesture()
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                if (event.actionMasked == MotionEvent.ACTION_UP) appendEvent(event)
                finishGesture()
                if (event.actionMasked==MotionEvent.ACTION_UP) performClick()
            }
        }
        return true
    }
    private fun appendEvent(event: MotionEvent) {
        val active = gesture ?: return
        val pointer = event.findPointerIndex(pointerId)
        if (pointer < 0) { finishGesture(); return }
        fun paperX(x: Float) = (x-destination.left)/destination.width()*active.document.width
        fun paperY(y: Float) = (y-destination.top)/destination.height()*active.document.height
        active.appendBatch(event.historySize,
            { paperX(event.getHistoricalX(pointer,it)) }, { paperY(event.getHistoricalY(pointer,it)) },
            paperX(event.getX(pointer)),paperY(event.getY(pointer)))
        // Process every historical position, but upload the bitmap and notify preview once per event.
        state.changed(); refresh()
    }
    private fun finishGesture() {
        val active = gesture
        gesture = null; pointerId = MotionEvent.INVALID_POINTER_ID
        if (active?.document === state.document) state.strokeFinished()
        parent?.requestDisallowInterceptTouchEvent(false)
    }
    override fun performClick(): Boolean { super.performClick(); return true }
    override fun onDetachedFromWindow() { finishGesture(); super.onDetachedFromWindow(); image?.recycle(); image=null }
}
