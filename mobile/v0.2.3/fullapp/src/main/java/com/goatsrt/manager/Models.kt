package com.goatsrt.manager

import org.json.JSONArray
import org.json.JSONObject

data class DashboardUi(val sessions:Int=0,val points:Long=0,val hours:Double=0.0,val best:String="--:--.---")
data class SessionUi(
    val id:Int, val date:String, val time:String, val track:String, val type:String,
    val laps:Int, val points:Int, val best:String, val duration:String,
    val vmax:Double, val vavg:Double, val notes:String, val format:String
)
data class LapUi(val lap:Int,val timeMs:Long,val time:String,val vmax:Double,val vavg:Double,val points:Int)
data class TrackPoint(val t:Long,val lat:Double,val lon:Double,val speed:Double,val lap:Int)
data class AnalysisUi(
    val ok:Boolean=false,
    val sessionId:Int=0,
    val track:String="",
    val date:String="",
    val time:String="",
    val best:String="--:--.---",
    val vmax:Double=0.0,
    val vavg:Double=0.0,
    val duration:String="00:00:00",
    val sampleHz:Double=0.0,
    val selectedLap:Int=0,
    val laps:List<LapUi> = emptyList(),
    val points:List<TrackPoint> = emptyList(),
)
data class TrackUi(
    val id:String,val name:String,val country:String,val direction:String,
    val triggerRadius:Double,val splitLines:Int,val realSectors:Int
)

fun JSONObject.toDashboardUi() = DashboardUi(
    sessions = optInt("sessions"), points = optLong("points"), hours = optDouble("hours"), best = optString("best", "--:--.---")
)

fun JSONArray.toSessions(): List<SessionUi> = buildList {
    for (i in 0 until length()) {
        val o = getJSONObject(i)
        add(SessionUi(
            o.getInt("id"), o.optString("date"), o.optString("time"), o.optString("track"), o.optString("type"),
            o.optInt("laps"), o.optInt("points"), o.optString("best"), o.optString("duration"),
            o.optDouble("vmax"), o.optDouble("vavg"), o.optString("notes"), o.optString("format")
        ))
    }
}

fun JSONObject.toAnalysisUi(): AnalysisUi {
    if (!optBoolean("ok")) return AnalysisUi(false)
    val s = getJSONObject("session")
    val lapsArray = getJSONArray("laps")
    val laps = buildList {
        for (i in 0 until lapsArray.length()) {
            val o = lapsArray.getJSONObject(i)
            add(LapUi(o.optInt("lap"),o.optLong("time_ms"),o.optString("time"),o.optDouble("vmax"),o.optDouble("vavg"),o.optInt("points")))
        }
    }
    val pointsArray = getJSONArray("points")
    val points = buildList {
        for (i in 0 until pointsArray.length()) {
            val o = pointsArray.getJSONObject(i)
            add(TrackPoint(o.optLong("t"),o.optDouble("lat"),o.optDouble("lon"),o.optDouble("v"),o.optInt("lap")))
        }
    }
    return AnalysisUi(
        ok=true, sessionId=s.optInt("id"), track=s.optString("track"), date=s.optString("date"), time=s.optString("time"),
        best=s.optString("best"), vmax=s.optDouble("vmax"), vavg=s.optDouble("vavg"), duration=s.optString("duration"),
        sampleHz=s.optDouble("sample_hz"), selectedLap=optInt("selected_lap"), laps=laps, points=points
    )
}


data class TrackLineUi(
    val name:String = "",
    val lat1:Double = 0.0, val lon1:Double = 0.0,
    val lat2:Double = 0.0, val lon2:Double = 0.0
)

data class TrackDetailUi(
    val ok:Boolean = false, val id:String = "", val name:String = "", val country:String = "IT",
    val direction:String = "unspecified", val triggerRadius:Double = 20.0,
    val startLine:TrackLineUi? = null, val sectors:List<TrackLineUi> = emptyList(),
    val error:String = ""
)

fun JSONObject.toTrackDetail(): TrackDetailUi {
    if (!optBoolean("ok")) return TrackDetailUi(error = optString("error"))
    val st = optJSONObject("start_line")
    val start = st?.let { TrackLineUi("Traguardo", it.optDouble("lat1"), it.optDouble("lon1"), it.optDouble("lat2"), it.optDouble("lon2")) }
    val sa = optJSONArray("sectors")
    val sectors = buildList {
        if (sa != null) for (i in 0 until sa.length()) {
            val o = sa.getJSONObject(i)
            add(TrackLineUi(o.optString("name", "Settore ${i+1}"), o.optDouble("lat1"), o.optDouble("lon1"), o.optDouble("lat2"), o.optDouble("lon2")))
        }
    }
    return TrackDetailUi(
        ok = true, id = optString("id"), name = optString("name"), country = optString("country", "IT"),
        direction = optString("direction", "unspecified"), triggerRadius = optDouble("trigger_radius_m", 20.0),
        startLine = start, sectors = sectors
    )
}

fun JSONArray.toTracks(): List<TrackUi> = buildList {
    for (i in 0 until length()) {
        val o = getJSONObject(i)
        add(TrackUi(
            o.optString("id"), o.optString("name"), o.optString("country"), o.optString("direction"),
            o.optDouble("trigger_radius_m"), o.optInt("split_lines"), o.optInt("real_sectors")
        ))
    }
}
