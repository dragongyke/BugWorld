package com.bugworld.app.garden

import com.bugworld.app.interaction.HandPoint
import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.ecs.resource.*
import com.pico.spatial.core.math.*
import kotlin.math.*

/** A localized gathering halo followed by rising sparks, allocated before the release. */
class ArrivalEffect(parent: Entity): AutoCloseable {
    private val root=Entity().also { parent.addChild(it) }
    private val mesh=MeshResource.createSphere(.009f)
    private val material=UnlitMaterial.create(BlendingMode.OPAQUE).apply {
        setBaseColor(Color4(1f,.76f,.87f,1f)); setApplyToneMapping(false)
    }
    private val opacity=OpacityControllerComponent(0f)
    private val glow=PointLightComponent(Color4(1f,.71f,.45f,1f),0f,.85f)
    private val glowEntity=Entity().also { it.components.set(glow); root.addChild(it) }
    private val particles=List(40) { Entity().apply { components.set(ModelComponent(mesh,material)); root.addChild(this) } }
    private var origin=HandPoint(0f,0f,0f)
    private var time=4f
    init { root.components.set(opacity); root.enabled=false }
    fun start(point: HandPoint) {
        origin=point; time=0f; root.enabled=true
        glowEntity.components[TransformComponent::class.java]?.setPosition(Vector3(point.x,point.y+.18f,point.z))
    }
    fun tick(delta: Float) {
        time+=delta
        if(time>=3f) { root.enabled=false; return }
        opacity.opacity=if(time<.4f) time/.4f else ((3f-time)/1.2f).coerceIn(0f,1f)
        glow.intensity=24f*opacity.opacity
        val gather=(1-time/.7f).coerceAtLeast(0f)
        particles.forEachIndexed { i,e ->
            val a=i*2.399963f+time*.9f
            val ring=i<16
            val radius=if(ring) .10f+(time-.7f).coerceAtLeast(0f)*.055f else .03f+gather*.25f+(i%5)*.014f
            val y=if(ring) -.025f else (i%9)*.012f+max(time-.7f,0f)*(.025f+(i%5)*.012f)
            e.components[TransformComponent::class.java]?.apply {
                setPosition(Vector3(origin.x+cos(a)*radius,origin.y+y,origin.z+sin(a)*radius))
                setScaleVector(Vector3(if(ring) .58f else .42f+(i%4)*.16f))
            }
        }
    }
    override fun close() { root.destroy(); mesh.close(); material.close() }
}
