package com.bugworld.app

import androidx.annotation.StringRes
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import com.bugworld.app.data.Species

@get:StringRes
val Species.labelRes: Int get() = when(this) {
    Species.BUTTERFLY -> R.string.species_butterfly
    Species.BEETLE -> R.string.species_beetle
    Species.LADYBUG -> R.string.species_ladybug
    Species.CATERPILLAR -> R.string.species_caterpillar
    Species.DRAGONFLY -> R.string.species_dragonfly
    Species.HONEYBEE -> R.string.species_honeybee
    Species.ANT -> R.string.species_ant
    Species.GRASSHOPPER -> R.string.species_grasshopper
}

// Keep status messages in resource form across configuration changes and window recreation.
sealed interface StudioStatus {
    data class Message(@StringRes val id: Int) : StudioStatus
    data class IncompleteMigration(val count: Int) : StudioStatus
}

@Composable fun StudioStatus.localized() = when(this) {
    is StudioStatus.Message -> stringResource(id)
    is StudioStatus.IncompleteMigration -> pluralStringResource(R.plurals.migration_incomplete,count,count)
}
