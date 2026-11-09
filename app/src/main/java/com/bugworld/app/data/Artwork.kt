package com.bugworld.app.data

enum class Species(val asset: String, val canFly: Boolean) {
    BUTTERFLY("butterfly", true), BEETLE("beetle", true),
    LADYBUG("ladybug", true), CATERPILLAR("caterpillar", false),
    DRAGONFLY("dragonfly", true), HONEYBEE("honeybee", true),
    ANT("ant", false), GRASSHOPPER("grasshopper", true);

    /** New models use UVs in the full drawing sheet's coordinate space. */
    val sheetMaterial: String? get() = when (this) {
        DRAGONFLY, HONEYBEE, ANT, GRASSHOPPER -> "Paper_$asset"
        else -> null
    }
}

data class Artwork(val id: String, val species: Species, val createdAt: Long, val updatedAt: Long, val revision: Int, val templateVersion: Int = 1)
