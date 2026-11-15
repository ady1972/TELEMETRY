#include <cassert>
#include "goats_screen_mode.h"
int main(){
 using namespace goats_screen_mode;
 load();assert(!delta()); // No preference -> original display.
 assert(select(true));assert(delta());assert(commits==1);
 delta()=false;load();assert(delta()); // Boot restores DELTA.
 assert(select(false));delta()=true;load();assert(!delta());
 fail_open=true;assert(!select(true));assert(!delta());fail_open=false;
 fail_set=true;assert(!select(true));assert(!delta());fail_set=false;
 fail_commit=true;assert(!select(true));assert(!delta());fail_commit=false;
 delta()=true;load();assert(!delta()); // Failed change is not restored.
 durable=9;load();assert(!delta()); // Invalid preference -> safe default.
 assert(select(true));delta()=false;load();assert(delta());
}
