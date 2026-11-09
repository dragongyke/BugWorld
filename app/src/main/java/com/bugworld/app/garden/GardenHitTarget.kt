package com.bugworld.app.garden

import com.pico.spatial.core.ecs.*
import com.pico.spatial.core.ecs.resource.*
import com.pico.spatial.core.math.*

/** One stable interaction volume per resident; never cook hundreds of bind-pose wing/leg hulls. */
class GardenHitTarget(private val model: Entity): AutoCloseable {
    private val resources=mutableListOf<Resource>()
    private val targets=mutableListOf<Entity>()
    init {
        try {
            val physics=PhysicsMaterialResource().also { it.toGlobal(); resources+=it }
            val bounds=model.getVisualBounds(relativeTo=model,recursive=true,enabledOnly=false)
            val size=bounds.size
            val height=maxOf(size.y,.28f)
            val base=ShapeResource.createBox(Vector3(maxOf(size.x,.10f),height,maxOf(size.z,.10f)))
                .also { it.toGlobal();resources+=it }
            val shape=base.offsetByTranslation(Vector3(bounds.center.x,bounds.min.y+height*.5f,bounds.center.z))
                .also { it.toGlobal();resources+=it }
            targets+=model
            model.components.set(CollisionComponent(collisionShape=listOf(shape),physicsMaterial=physics))
            model.components.set(InteractableComponent())
            model.components.set(HoverEffectComponent())
        } catch(error: Throwable) { close(); throw error }
    }
    fun owns(entity: Entity)=targets.any { it.id==entity.id }
    override fun close() {
        targets.filter { it.valid }.forEach {
            it.components.remove(HoverEffectComponent::class.java)
            it.components.remove(InteractableComponent::class.java)
            it.components.remove(CollisionComponent::class.java)
        }
        targets.clear(); resources.asReversed().forEach { it.close() }; resources.clear()
    }
}
