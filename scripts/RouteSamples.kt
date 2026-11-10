import com.bugworld.app.data.Species
import com.bugworld.app.garden.ApprovedGardenRoutes
import java.io.File

fun main(args: Array<String>) {
    File(args[0]).printWriter().use { out ->
        out.println("species,index,time,x,y,z,yaw,pitch,roll,moving,airborne,hopPhase")
        for (species in Species.entries) for (index in 0 until ApprovedGardenRoutes.count(species)) {
            val stepSeconds = if (species == Species.GRASSHOPPER) .02f else .1f
            val steps = if (species == Species.GRASSHOPPER)
                kotlin.math.ceil(ApprovedGardenRoutes.period(species, index) / stepSeconds).toInt()
            else 1200
            for (step in 0..steps) {
                val time=step*stepSeconds
                val pose=ApprovedGardenRoutes.pose(species,index,time)
                out.println("$species,$index,$time,${pose.point.x},${pose.point.y},${pose.point.z},${pose.yaw},${pose.pitch},${pose.roll},${pose.moving},${pose.airborne},${pose.hopPhase ?: ""}")
            }
        }
    }
}
