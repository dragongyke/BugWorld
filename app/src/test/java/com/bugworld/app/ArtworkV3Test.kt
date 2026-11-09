package com.bugworld.app

import com.bugworld.app.data.*
import java.io.File
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class ArtworkV3Test {
    @get:Rule val temporary=TemporaryFolder()

    @Test fun failedAndLegacyDraftBytesAreArchivedBeforeReplacement() {
        val root=temporary.newFolder(); val store=ArtworkStore(root)
        for(version in listOf(1,2,3)) {
            val original=byteArrayOf(version.toByte(),99,1)
            store.saveDraft(Species.BUTTERFLY,original,version)
            store.preserveLatestDraft(Species.BUTTERFLY)
            store.preserveLatestDraft(Species.BUTTERFLY)
            store.saveDraft(Species.BUTTERFLY,byteArrayOf(8,7),3)
            val copies=File(root,".drafts/original-v$version").listFiles()!!
            assertEquals(1,copies.size)
            assertArrayEquals(original,copies.single().readBytes())
            assertArrayEquals(byteArrayOf(8,7),store.latestDraft(Species.BUTTERFLY)!!.second)
        }
    }

    @Test fun approvedTemplateAndDraftSurviveRestart() {
        val root=temporary.newFolder(); val store=ArtworkStore(root)
        val work=store.save(Species.BUTTERFLY,byteArrayOf(3,1,4),templateVersion=3)
        store.saveDraft(Species.BUTTERFLY,byteArrayOf(9,2),3)
        val reopened=ArtworkStore(root)
        assertEquals(3,reopened.list().single().templateVersion)
        assertArrayEquals(byteArrayOf(3,1,4),reopened.image(work))
        assertEquals(3,reopened.latestDraft(Species.BUTTERFLY)!!.first)
    }

    @Test fun migrationPreservesIdentityDatesQueueAndOriginalBytes() {
        val root=temporary.newFolder(); val store=ArtworkStore(root)
        val old=store.save(Species.BEETLE,byteArrayOf(1,2,3),templateVersion=1)
        store.saveGarden(listOf(old.id))
        val migrated=store.migrateToCurrent(old,byteArrayOf(8,9))
        assertEquals(old.id,migrated.id)
        assertEquals(old.createdAt,migrated.createdAt)
        assertEquals(old.updatedAt,migrated.updatedAt)
        assertEquals(3,migrated.templateVersion)
        assertEquals(old.revision+1,migrated.revision)
        assertArrayEquals(byteArrayOf(8,9),store.image(migrated))
        assertArrayEquals(byteArrayOf(1,2,3),File(root,"${old.id}/.original-v1/image.png").readBytes())
        assertEquals(listOf(old.id),ArtworkStore(root).loadGarden())
        assertEquals(migrated,store.migrateToCurrent(migrated,byteArrayOf(77)))
        assertArrayEquals(byteArrayOf(8,9),store.image(migrated))
        store.delete(migrated.id)
        assertFalse(File(root,old.id).exists())
    }

    @Test fun staleMigrationCannotOverwriteNewerUserEdit() {
        val root=temporary.newFolder(); val store=ArtworkStore(root)
        val old=store.save(Species.LADYBUG,byteArrayOf(1),templateVersion=2)
        val edited=store.save(Species.LADYBUG,byteArrayOf(2),old.id,2)
        assertThrows(IllegalArgumentException::class.java) { store.migrateToCurrent(old,byteArrayOf(8)) }
        assertArrayEquals(byteArrayOf(2),store.image(edited))
    }
}
