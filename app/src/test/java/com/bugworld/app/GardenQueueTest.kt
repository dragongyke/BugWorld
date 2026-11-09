package com.bugworld.app

import com.bugworld.app.garden.GardenQueue
import org.junit.Assert.*
import org.junit.Test

class GardenQueueTest {
    @Test fun eleventhWorkRetiresOldestWithoutLosingAlbum() {
        val queue = GardenQueue()
        (1..11).forEach { queue.place("art-$it") }
        assertEquals((2..11).map { "art-$it" }, queue.ids)
    }
    @Test fun replacingAnExistingWorkRefreshesOrderWithoutDuplicating() {
        val queue = GardenQueue()
        (1..10).forEach { queue.place("art-$it") }
        queue.place("art-1")
        assertEquals((2..10).map { "art-$it" } + "art-1", queue.ids)
    }
    @Test fun restoreFiltersDeletedAndDuplicateWorksAndKeepsLatestTen() {
        val queue = GardenQueue()
        queue.restore((1..12).map { "art-$it" } + "art-2", (2..12).map { "art-$it" }.toSet())
        assertEquals((4..12).map { "art-$it" } + "art-2", queue.ids)
        queue.remove("art-7")
        assertFalse(queue.ids.contains("art-7"))
    }
}
