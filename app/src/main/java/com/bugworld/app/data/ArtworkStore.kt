package com.bugworld.app.data

import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.nio.file.AtomicMoveNotSupportedException
import java.security.MessageDigest
import java.util.Properties
import java.util.UUID

enum class ArtworkIssue { SHEET_CHANGED, STALE, CHECKSUM, DELETE_FAILED, INVALID_ID, UNSUPPORTED_VERSION, UNREADABLE }
class ArtworkException(val issue: ArtworkIssue) : IllegalArgumentException(issue.name)

class ArtworkStore(private val root: File) {
    init { check(root.exists() || root.mkdirs()) }

    @Synchronized fun save(species: Species, image: ByteArray, id: String? = null, templateVersion: Int? = null): Artwork {
        require(image.isNotEmpty() && image.size <= 8 * 1024 * 1024)
        val workId = id ?: UUID.randomUUID().toString()
        val directory = directory(workId)
        val old = if (id != null) read(directory).first else null
        require(old == null || old.species == species)
        check(directory.exists() || directory.mkdirs())
        val now = System.currentTimeMillis()
        val version = templateVersion ?: old?.templateVersion ?: 1
        require(version in 1..3)
        if (old != null && old.templateVersion != version) throw ArtworkException(ArtworkIssue.SHEET_CHANGED)
        val work = Artwork(workId, species, old?.createdAt ?: now, now, (old?.revision ?: 0) + 1, version)
        val imageName = "${work.revision}-${UUID.randomUUID()}.png"
        atomicWrite(File(directory, imageName), image)
        val properties = Properties().apply {
            setProperty("species", species.name)
            setProperty("templateVersion", version.toString())
            setProperty("createdAt", work.createdAt.toString())
            setProperty("updatedAt", work.updatedAt.toString())
            setProperty("revision", work.revision.toString())
            setProperty("image", imageName)
            setProperty("sha256", digest(image))
        }
        val bytes = java.io.ByteArrayOutputStream().apply { properties.store(this, "BugWorld artwork v1") }.toByteArray()
        // Publish the metadata only after the complete image is durable.
        atomicWrite(File(directory, "current.properties"), bytes)
        directory.listFiles()?.filter { it.extension == "png" && it.name != imageName }
            ?.forEach { runCatching { it.delete() } }
        return work
    }

    @Synchronized fun list(): List<Artwork> = root.listFiles().orEmpty()
        .filter { it.isDirectory && validId(it.name) }
        .mapNotNull { runCatching { read(it).first }.getOrNull() }
        .sortedByDescending { it.updatedAt }

    /** Preserve the original user pixels before atomically publishing a new template version. */
    @Synchronized fun migrateToCurrent(work: Artwork, image: ByteArray): Artwork {
        require(image.isNotEmpty() && image.size<=8*1024*1024)
        val directory=directory(work.id)
        val (current,properties)=read(directory)
        if (current.revision != work.revision || current.templateVersion != work.templateVersion) throw ArtworkException(ArtworkIssue.STALE)
        if(current.templateVersion==3) return current
        val original=this.image(current)
        val backup=File(directory,".original-v${current.templateVersion}")
        check(backup.exists() || backup.mkdirs())
        atomicWrite(File(backup,"image.png"),original)
        atomicWrite(File(backup,"current.properties"),File(directory,"current.properties").readBytes())
        val migrated=current.copy(revision=current.revision+1,templateVersion=3)
        val name="${migrated.revision}-${UUID.randomUUID()}.png"
        atomicWrite(File(directory,name),image)
        properties.setProperty("templateVersion","3")
        properties.setProperty("revision",migrated.revision.toString())
        properties.setProperty("image",name)
        properties.setProperty("sha256",digest(image))
        val metadata=java.io.ByteArrayOutputStream().apply { properties.store(this,"BugWorld artwork v3") }.toByteArray()
        atomicWrite(File(directory,"current.properties"),metadata)
        directory.listFiles()?.filter { it.isFile && it.extension=="png" && it.name!=name }
            ?.forEach { runCatching { it.delete() } }
        return migrated
    }

    @Synchronized fun image(work: Artwork): ByteArray {
        val (current, properties) = read(directory(work.id))
        if (current.revision != work.revision) throw ArtworkException(ArtworkIssue.STALE)
        val bytes = File(directory(work.id), properties.getProperty("image")).readBytes()
        if (digest(bytes) != properties.getProperty("sha256")) throw ArtworkException(ArtworkIssue.CHECKSUM)
        return bytes
    }

    @Synchronized fun delete(id: String) {
        val directory = directory(id)
        if (!directory.exists()) return
        if (!File(directory, "current.properties").delete()) throw ArtworkException(ArtworkIssue.DELETE_FAILED)
        directory.deleteRecursively()
    }

    @Synchronized fun saveGarden(ids: List<String>) {
        require(ids.all(::validId))
        atomicWrite(File(root, "garden.txt"), ids.joinToString("\n").toByteArray(Charsets.UTF_8))
    }
    @Synchronized fun loadGarden(): List<String> = File(root, "garden.txt")
        .takeIf { it.isFile }?.readLines()?.filter(::validId) ?: emptyList()

    @Synchronized fun saveDraft(species: Species, image: ByteArray, templateVersion: Int = 1) {
        require(templateVersion in 1..3)
        val draftDirectory = File(root, if (templateVersion == 1) ".drafts" else ".drafts/v$templateVersion").apply { mkdirs() }
        atomicWrite(File(draftDirectory, "${species.asset}.png"), image)
        atomicWrite(File(root,".drafts/${species.asset}-active.txt"),templateVersion.toString().toByteArray())
    }
    @Synchronized fun draft(species: Species, templateVersion: Int = 1): ByteArray? {
        require(templateVersion in 1..3)
        return File(root, if (templateVersion == 1) ".drafts/${species.asset}.png" else ".drafts/v$templateVersion/${species.asset}.png")
            .takeIf { it.isFile }?.readBytes()
    }
    @Synchronized fun latestDraft(species: Species): Pair<Int,ByteArray>? {
        val selected=File(root,".drafts/${species.asset}-active.txt").takeIf { it.isFile }?.readText()?.trim()?.toIntOrNull()
        if(selected in 1..3) draft(species,selected!!)?.let { return selected to it }
        return (3 downTo 1).firstNotNullOfOrNull { version -> draft(species,version)?.let { version to it } }
    }
    /** Preserve failed/legacy draft bytes before any replacement, including unreadable PNG payloads. */
    @Synchronized fun preserveLatestDraft(species: Species) {
        val (version,bytes)=latestDraft(species) ?: return
        val archive=File(root,".drafts/original-v$version").apply { mkdirs() }
        val destination=File(archive,"${species.asset}-${digest(bytes)}.png")
        if(!destination.exists()) atomicWrite(destination,bytes)
    }

    private fun directory(id: String): File {
        if (!validId(id)) throw ArtworkException(ArtworkIssue.INVALID_ID)
        return File(root, id)
    }
    private fun validId(id: String) = id.matches(Regex("[A-Za-z0-9-]{1,80}"))
    private fun read(directory: File): Pair<Artwork, Properties> {
        val properties = Properties().apply { File(directory, "current.properties").inputStream().use(::load) }
        val image = properties.getProperty("image")
        require(image.matches(Regex("[A-Za-z0-9-]+\\.png")))
        check(File(directory, image).isFile)
        val work = Artwork(directory.name, Species.valueOf(properties.getProperty("species")),
            properties.getProperty("createdAt").toLong(), properties.getProperty("updatedAt").toLong(),
            properties.getProperty("revision").toInt(), properties.getProperty("templateVersion", "1").toInt())
        require(work.revision > 0)
        if (work.templateVersion !in 1..3) throw ArtworkException(ArtworkIssue.UNSUPPORTED_VERSION)
        return work to properties
    }
    private fun digest(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }

    private fun atomicWrite(destination: File, bytes: ByteArray) {
        val temp = File(destination.parentFile, ".${destination.name}.${UUID.randomUUID()}.tmp")
        try {
            FileOutputStream(temp).use { it.write(bytes); it.fd.sync() }
            try {
                Files.move(temp.toPath(), destination.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
            } catch (_: AtomicMoveNotSupportedException) {
                Files.move(temp.toPath(), destination.toPath(), StandardCopyOption.REPLACE_EXISTING)
            }
        } finally { temp.delete() }
    }
}
