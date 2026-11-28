#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#pragma once
#include <cmath>
#include <algorithm>
// RAM-only per-lap maximum. Does not change the timing engine or GNSS epochs.
namespace goats_lap_speed {
inline float &current(){static float value=0;return value;}
inline float &last(){static float value=NAN;return value;}
inline void reset(){current()=0;last()=NAN;}
inline void observe(float speed){if(std::isfinite(speed)&&speed>=0)current()=std::max(current(),speed);}
inline void complete(){last()=current();current()=0;}
}

#endif // GOATS_RC33_STEP1_IMPL
