#include "goats_diag3.h"
#include <cassert>
#include <cstring>
#include <iostream>
using esphome::goats_diag3::GoatsDiag3;
using esphome::uart::UARTComponent;
std::vector<uint8_t> nav(uint32_t tow,uint8_t type=3,bool ok=true){
 std::vector<uint8_t> p(92);for(int i=0;i<4;i++)p[i]=uint8_t(tow>>(8*i));
 p[4]=0xea;p[5]=7;p[6]=11;p[7]=26;p[11]=3;
 p[20]=type;p[21]=ok;p[23]=12;
 uint32_t speed=27778;for(int i=0;i<4;i++)p[60+i]=uint8_t(speed>>(8*i));
 return goats_m9n::frame(1,7,p);
}
void add(UARTComponent&u,const std::vector<uint8_t>&f){u.rx.insert(u.rx.end(),f.begin(),f.end());}
int main(){
 UARTComponent u;GoatsDiag3 c;c.set_uart_parent(&u);
 clock_ms=0;c.setup();clock_ms=899;c.loop();assert(u.writes.empty());
 assert(c.speed_text()=="--" && c.visible_text()=="--" && c.used_text()=="--" && c.hdop_text()=="--");
 clock_ms=900;c.loop();assert(clock_ms==3330 && u.baud==230400 && u.writes.size()==17);
 assert(u.bauds==std::vector<uint32_t>({38400,9600,115200,230400,230400}));
 auto f=nav(1000);add(u,{f.begin(),f.begin()+3});c.loop();assert(goats_gps_diag::counters.pvt==0);
 add(u,{f.begin()+3,f.end()});c.loop();assert(goats_gps_diag::counters.pvt==1);
 assert(c.status_text()=="DATI OK - FIX 3D" && c.position_valid());
 assert(c.used_text()=="12" && c.speed_text()=="100.0");
 assert(c.visible_text()=="--" && c.hdop_text()=="--");
 for(unsigned i=1;i<=80;i++){clock_ms+=40;add(u,nav(1000+40*i));c.loop();}
 assert(goats_m9n::state.pvt_hz==25 && goats_gps_diag::stability.step_ms==40);
 assert(goats_m9n::pending_samples.empty());
 assert(goats_gps_diag::stability.max_gap_ms==40);
 // NAV-SAT list count follows DIAG3, including channels without positive C/N0.
 std::vector<uint8_t> sat(8+12*21);sat[5]=21;add(u,goats_m9n::frame(1,0x35,sat));
 std::vector<uint8_t> dop(18);dop[12]=75;add(u,goats_m9n::frame(1,4,dop));c.loop();
 assert(c.visible_text()=="21" && c.hdop_text()=="0.75");
 const uint32_t aux_ms=clock_ms;
 auto broken=nav(5000);broken.back()^=1;add(u,broken);c.loop();
 assert(goats_gps_diag::counters.checksum_errors==1);
 add(u,{0xb5,0x62,1,7,0xff,0xff});c.loop();assert(goats_gps_diag::counters.oversize==1);
 add(u,goats_m9n::frame(5,1,{6,0x8a}));add(u,goats_m9n::frame(5,0,{6,1}));c.loop();
 assert(goats_gps_diag::counters.ack==1 && goats_gps_diag::counters.nak==1);
 clock_ms+=1600;c.loop();assert(!c.position_valid() && c.speed_text()=="--" && c.used_text()=="--");
 assert(goats_gps_diag::stability.stream_losses==1 && goats_gps_diag::stability.fix_losses==1);
 c.loop();assert(goats_gps_diag::stability.stream_losses==1);
 add(u,nav(7000,5,true));c.loop();assert(c.status_text()=="DATI OK - SOLO TEMPO" && c.speed_text()=="--");
 clock_ms=aux_ms+5001;c.loop();assert(c.visible_text()=="--" && c.hdop_text()=="--");
 assert(u.writes.size()==17); // No retries, extra polls, writes or GNSS resets in runtime.
 assert(u.reads==u.rx.size()); // Every byte consumed once, by the original reader.
 std::cout<<"PASS: DIAG3 boot, original single reader, fragmented UBX, freshness, fix, speed, SAT/DOP, ACK/NAK and no runtime writes\n";
}
