package com.bugworld.app.spatial

import android.util.Log
import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.ecs.resource.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** The reviewed native materials, sun and sky are loaded as one versioned scene. */
class ForestEnvironment private constructor(
    val root: Entity,
    private val bundle: AssetBundle,
    private val environment: TextureResource,
) : AutoCloseable {
    private var closed=false
    override fun close() {
        if(closed) return
        closed=true
        root.destroy()
        environment.close()
        bundle.close()
    }

    companion object {
        suspend fun load(): ForestEnvironment {
            var ownedBundle: AssetBundle?=null
            var scene: Entity?=null
            var texture: TextureResource?=null
            try {
                // Retain ownership inside IO: prompt cancellation may discard its return value.
                withContext(Dispatchers.IO) {
                    ownedBundle=AssetBundle.load("v3/environment/forest.bundle",LoadType.FROM_ASSETS)
                }
                val bundle=checkNotNull(ownedBundle)
                scene=Entity.loadSuspend("Forest",bundle)
                val names=ModelLibrary.entities(scene).map { it.getName() }
                check("garden" in names && "ForestBackdrop" in names && "NativeSunLit" in names) {
                    "Incomplete forest scene: $names"
                }
                check("review_insects" !in names) { "Review-only insects in runtime scene" }
                texture=TextureResource.load("v3/environment/forest.ktx",LoadType.FROM_ASSETS,
                    TextureCreateOption().apply {
                        textureEncoding=TextureEncoding.LINEAR
                        colorSpace=TextureColorSpace.SRGB
                        mipmapMode=TextureMipmapMode.NONE
                    }).also { it.toGlobal() }
                scene.addChild(Entity().apply {
                    setName("ForestEnvironmentIBL")
                    components.set(StageEnvironmentLightingComponent(ImageBasedLightSource.Single(texture),8f))
                })
                Log.i("BugWorldLighting","Emerald forest ready: native scene, animated shallow water, sun=2400lux, captured HDR IBL=8EV; nodes=${names.size}")
                return ForestEnvironment(scene,bundle,texture)
            } catch(error: Throwable) {
                scene?.destroy();texture?.close();ownedBundle?.close()
                throw error
            }
        }
    }
}
