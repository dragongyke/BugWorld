package com.bugworld.app

import com.bugworld.app.data.*
import java.io.File
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class ArtworkStoreTest {
    @get:Rule val temporary = TemporaryFolder()
    @Test fun latestDraftCanSwitchBackToAnEditedLegacyWork() {
        val root=temporary.newFolder(); val store=ArtworkStore(root)
        store.saveDraft(Species.BUTTERFLY,byteArrayOf(2),2)
        store.saveDraft(Species.BUTTERFLY,byteArrayOf(1),1)
        val latest=ArtworkStore(root).latestDraft(Species.BUTTERFLY)!!
        assertEquals(1,latest.first); assertArrayEquals(byteArrayOf(1),latest.second)
        assertArrayEquals(byteArrayOf(2),store.draft(Species.BUTTERFLY,2))
    }
    @Test fun newTemplateMetadataDoesNotHideArtworkOrChangeLegacyVersion() {
        val root=temporary.newFolder()
        val store=ArtworkStore(root)
        val legacy=store.save(Species.BUTTERFLY,byteArrayOf(1))
        val newer=store.save(Species.LADYBUG,byteArrayOf(2))
        val metadata=File(root,"${newer.id}/current.properties")
        val properties=java.util.Properties().apply { metadata.inputStream().use(::load); setProperty("templateVersion","2") }
        metadata.outputStream().use { properties.store(it,null) }
        val loaded=ArtworkStore(root).list()
        assertEquals(2,loaded.size)
        assertEquals(1,loaded.single { it.id==legacy.id }.templateVersion)
        assertEquals(2,loaded.single { it.id==newer.id }.templateVersion)
    }
    @Test fun saveUpdateReloadAndDelete() {
        val root = temporary.newFolder()
        val store = ArtworkStore(root)
        val first = store.save(Species.BUTTERFLY, byteArrayOf(1, 2, 3))
        val updated = store.save(Species.BUTTERFLY, byteArrayOf(4, 5), first.id)
        assertEquals(first.id, updated.id)
        assertEquals(first.createdAt, updated.createdAt)
        assertEquals(first.revision + 1, updated.revision)
        val reopened = ArtworkStore(root)
        assertEquals(listOf(updated), reopened.list())
        assertArrayEquals(byteArrayOf(4, 5), reopened.image(updated))
        reopened.delete(updated.id)
        assertTrue(reopened.list().isEmpty())
    }
    @Test fun damagedAndInterruptedFilesDoNotEraseOtherWorks() {
        val root = temporary.newFolder()
        val store = ArtworkStore(root)
        val good = store.save(Species.LADYBUG, byteArrayOf(1))
        // Simulate interruption after a new revision image, before metadata publication.
        File(root,"${good.id}/2-orphan.png").writeBytes(byteArrayOf(9))
        File(root,"${good.id}/.current.properties.interrupted.tmp").writeText("revision=2")
        File(root, "broken").mkdirs()
        File(root, "broken/current.properties").writeText("species=UNKNOWN")
        File(root, "partial.tmp").writeText("unfinished")
        assertEquals(listOf(good), ArtworkStore(root).list())
        assertArrayEquals(byteArrayOf(1),ArtworkStore(root).image(good))
    }
    @Test fun queueAndDraftSurviveRestart() {
        val root = temporary.newFolder()
        val store = ArtworkStore(root)
        store.saveGarden(listOf("one", "two"))
        store.saveDraft(Species.CATERPILLAR, byteArrayOf(3, 4))
        val reopened = ArtworkStore(root)
        assertEquals(listOf("one", "two"), reopened.loadGarden())
        assertArrayEquals(byteArrayOf(3, 4), reopened.draft(Species.CATERPILLAR))
    }
}
