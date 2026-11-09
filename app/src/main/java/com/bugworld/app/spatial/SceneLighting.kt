package com.bugworld.app.spatial

import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.ecs.light.ShadowFaceCullingMode
import com.pico.spatial.core.ecs.light.ShadowProjectionType
import com.pico.spatial.core.math.*

/** Shared Space preview lighting; the forest bundle owns Stage sunlight. */
class SceneLighting(parent: Entity) : AutoCloseable {
    private val root=Entity()
    private var closed=false
    init {
        try {
            root.addChild(Entity().apply {
                components.set(DirectionalLightComponent(Color4(1f,.95f,.88f,1f),1600f,true).apply {
                    shadowDepthBias=.005f
                    shadowFaceCullingMode=ShadowFaceCullingMode.BACK
                    shadowProjectionType=ShadowProjectionType.Auto()
                })
                components.get<TransformComponent>()?.setEulerAngles(EulerAngles(-48f,-35f,0f))
            })
            root.addChild(Entity().apply {
                components.set(PointLightComponent(Color4(.74f,.82f,1f,1f),900f,16f))
                components.get<TransformComponent>()?.setPosition(Vector3(0f,4f,1f))
            })
            check(parent.addChild(root)) { "Unable to attach preview lighting" }
        } catch(error: Throwable) { close();throw error }
    }
    override fun close() {
        if(closed) return
        closed=true
        if(root.valid) root.destroy()
    }
}
