#include <cassert>
#include <cstdint>
int64_t fake_us=0;
unsigned log_lines=0;
#include "goats_nav_sample_queue.h"
int main(){
 goats_clock::latest={2026,11,6,23,59,59};
 goats_nav_queue::push(true,45,9,40,100,1000,0.8,12);
 goats_clock::latest={2026,11,7,0,0,0};
 goats_nav_queue::push(true,45,9,40,140,1040,0.8,12);
 goats_nav_queue::Sample sample{};
 assert(goats_nav_queue::pop(sample));assert(sample.date.day==6 && sample.date.second==59);
 assert(goats_nav_queue::pop(sample));assert(sample.date.day==7 && sample.date.second==0);
}
