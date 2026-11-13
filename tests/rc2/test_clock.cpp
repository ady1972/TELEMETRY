#include "goats_recording_clock.h"
#include <cassert>
#include <string>
using namespace goats_clock;
static void local(DateTime utc,const char *date,const char*time){char d[16],t[16];format(rome(utc),d,sizeof(d),t,sizeof(t));assert(std::string(d)==date);assert(std::string(t)==time);}
int main(){
 local({2026,11,6,12,34,56},"2026-11-06","13:34:56");
 local({2026,7,6,12,34,56},"2026-07-06","14:34:56");
 local({2026,3,29,0,59,59},"2026-03-29","01:59:59");
 local({2026,3,29,1,0,0},"2026-03-29","03:00:00");
 local({2026,10,25,0,59,59},"2026-10-25","02:59:59");
 local({2026,10,25,1,0,0},"2026-10-25","02:00:00");
 local({2026,12,31,23,30,0},"2027-01-01","00:30:00");
 local({2028,2,28,23,30,0},"2028-02-29","00:30:00");
 assert(!valid(rome({2026,2,29,0,0,0})));assert(!valid(rome({2026,0,1,0,0,0})));
 uint8_t p[92]{};p[4]=2026&255;p[5]=2026>>8;p[6]=11;p[7]=6;p[8]=23;p[9]=30;
 assert(!valid(from_pvt(p)));p[11]=3;assert(from_pvt(p).day==7);
 char name[16];auto date=parse("2026-11-06","13:34:56");
 assert(filename(date,"Taranto",1,name,sizeof(name)));assert(std::string(name)=="TA06NO01.CSV");
 assert(filename(date,"Taranto",99,name,sizeof(name)));assert(std::string(name)=="TA06NO99.CSV");
 assert(!filename(date,"TA",100,name,sizeof(name)));assert(!filename({},"TA",1,name,sizeof(name)));
 assert(is_rc2_name("TA06NO01.CSV"));assert(!is_rc2_name("TA00NO01.CSV"));assert(!is_rc2_name("TA06XX01.CSV"));
 assert(filename(date,"7 Laghi",1,name,sizeof(name)));assert(std::string(name)=="LA06NO01.CSV");
 assert(is_legacy_name("TA6NO01.CSV"));
 assert(fat_date(date)==uint16_t((2026-1980)<<9|11<<5|6));assert(fat_time(date)==uint16_t(13<<11|34<<5|28));
 assert(epoch({2026,1,1,0,0,0})==1767225600);
}
