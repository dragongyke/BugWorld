import com.bugworld.app.data.Species
import com.bugworld.app.garden.ApprovedGardenRoutes
import java.io.File

fun main(args: Array<String>) {
    File(args[0]).printWriter().use { out ->
        out.println("species,index,time,x,y,z,yaw,pitch,roll,moving,airborne,hopPhase")
        for(species in Species.entries) for(index in 0 until ApprovedGardenRoutes.count(species)) for(step in 0..1200) {
            val time=step*.1f
            val pose=ApprovedGardenRoutes.pose(species,index,time)
            out.println("$species,$index,$time,${pose.point.x},${pose.point.y},${pose.point.z},${pose.yaw},${pose.pitch},${pose.roll},${pose.moving},${pose.airborne},${pose.hopPhase ?: ""}")
        }
    }
}
