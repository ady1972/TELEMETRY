#include "scan_engine.h"
#include <cassert>
#include <deque>
#include <set>
#include <tuple>
#include <vector>
#include <iostream>
using namespace goats_scan;
using Bytes=std::vector<uint8_t>;
static void put(Bytes &p,size_t i,uint32_t x,unsigned n=4){for(unsigned j=0;j<n;j++)p.at(i+j)=uint8_t(x>>(8*j));}
static Bytes packet(uint8_t cls,uint8_t id,const Bytes&p){
 Bytes f{0xB5,0x62,cls,id,uint8_t(p.size()),uint8_t(p.size()>>8)};f.insert(f.end(),p.begin(),p.end());
 uint8_t a=0,b=0;for(size_t i=2;i<f.size();i++){a+=f[i];b+=a;}f.push_back(a);f.push_back(b);return f;
}
static Bytes nmea(std::string p){uint8_t ck=0;for(char c:p)ck^=c;char tail[8];std::snprintf(tail,sizeof(tail),"*%02X\r\n",ck);p="$"+p+tail;return {p.begin(),p.end()};}
static bool same(const Candidate&a,const Candidate&b){return a.port==b.port&&a.baud==b.baud&&a.format==b.format&&a.inverted==b.inverted;}
struct Fake : Transport {
 Candidate selected{},receiver{38400,0,0,false};std::vector<Candidate>opened;std::vector<Bytes>tx;
 size_t fragment_limit=8192,remaining=8192;std::deque<uint8_t>rx;bool fail_all=false,powered=true,answers=true,nav=true,fix=false,echo=false,use_nmea=false,corrupt=false;uint32_t now=0;
 bool open(const Candidate&c)override{selected=c;opened.push_back(c);rx.clear();return !fail_all;}
 size_t read(uint8_t*out,size_t n)override{n=std::min(n,remaining);size_t k=0;while(k<n&&!rx.empty()){out[k++]=rx.front();rx.pop_front();}remaining-=k;return k;}
 uint32_t actual_baud()const override{return selected.baud;}
 void push(const Bytes&f){rx.insert(rx.end(),f.begin(),f.end());}
 void write(const uint8_t *p,size_t n)override{
  Bytes f(p,p+n);tx.push_back(f);assert(n==8&&f[0]==0xB5&&f[1]==0x62&&f[4]==0&&f[5]==0);
  uint8_t a=0,b=0;for(size_t i=2;i<6;i++){a+=f[i];b+=a;}assert(f[6]==a&&f[7]==b);
  assert((f[2]==0x0A&&f[3]==4)||(f[2]==6&&(f[3]==0||f[3]==8))); // No settings or reset writes.
  if(echo){push(f);return;}
  if(!powered||!answers||!same(selected,receiver))return;
  if(f[2]==0x0A){Bytes p(40);std::memcpy(p.data(),"UBLOX TEST SOFTWARE",19);std::memcpy(p.data()+30,"M9N",3);push(packet(0x0A,4,p));}
  else if(f[3]==0){Bytes p(20);p[0]=1;put(p,4,0x8D0);put(p,8,receiver.baud);put(p,12,3,2);put(p,14,3,2);push(packet(6,0,p));}
  else {Bytes p(6);put(p,0,40,2);put(p,2,1,2);push(packet(6,8,p));}
 }
 void emit(uint32_t time){
  now=time;remaining=fragment_limit;if(!powered||!nav||opened.empty()||!same(selected,receiver))return;
  Bytes f;
  if(use_nmea){if(now%1000)return;f=nmea("BDGGA,123519,4807.038,N,01131.000,E,1,11,0.8,0,M,0,M,,");}
  else {if(now%40)return;Bytes p(92);put(p,0,now);p[20]=fix?3:0;p[21]=fix?1:0;p[23]=fix?12:0;f=packet(1,7,p);}
  if(corrupt)f.back()^=1;
  push(f);
 }
};
static void step(Engine&e,Fake&f,uint32_t now){f.emit(now);e.tick(now);}
static uint32_t lock(Engine&e,Fake&f,uint32_t start,uint32_t limit=100000){
 e.start(start);for(uint32_t t=0;t<limit;t+=20){step(e,f,start+t);if(e.view().phase==Phase::STABLE)return start+t;}
 assert(false&&"Expected lock");return 0;
}
int main(){
 // Full schedule: each port/rate/format/RX polarity exactly once in a cycle.
 {std::set<std::tuple<unsigned,unsigned,unsigned,bool>>all;
  for(unsigned i=0;i<TRIALS;i++){const auto c=candidate(i);all.emplace(c.port,c.baud,c.format,c.inverted);}
  assert(all.size()==396&&same(candidate(0),Candidate{230400,1,0,false}));}
 // Recover the correct UART/baud, verify query replies, don't confuse no fix with no link.
 {Fake f;Engine e(f);const auto t=lock(e,f,0);
  assert(same(e.view().selected,f.receiver));assert(e.view().tx_replies>=2);
  assert(e.view().current_ubx>5&&e.view().pvt_hz>20&&e.view().pvt_hz<30);
  assert(e.view().receiver_baud==38400&&e.view().meas_ms==40&&e.view().nav_rate==1);
  assert(std::strcmp(e.view().receiver_format,"8N1")==0);
  assert(!e.view().fix_ok&&std::strstr(e.status(),"RX/TX"));
  const auto n=f.opened.size();for(uint32_t dt=20;dt<6000;dt+=20)step(e,f,t+dt);
  assert(f.opened.size()==n&&e.view().phase==Phase::STABLE);}
 // A quiet UBX receiver can be discovered with read-only queries; no NAV required.
 {Fake f;f.nav=false;f.receiver={230400,1,0,false};Engine e(f);lock(e,f,0);
  assert(e.view().pvt_count==0&&e.view().tx_replies>=2&&!e.view().fix_ok);}
 // Echo and bad checksums are never accepted as a GPS lock.
 {Fake f;f.echo=true;f.nav=false;Engine e(f);e.start(0);
  for(unsigned t=0;t<30000;t+=20)step(e,f,t);
  assert(e.view().echo>0&&e.view().ubx==0&&e.view().phase!=Phase::STABLE&&f.opened.size()>5);}
 {Fake f;f.answers=false;f.corrupt=true;f.receiver={230400,1,0,false};Engine e(f);e.start(0);
  for(unsigned t=0;t<15000;t+=20)step(e,f,t);
  assert(e.view().bad>0&&e.view().current_ubx==0&&e.view().phase!=Phase::STABLE);}
 // NMEA at extended framing + RX inversion, with no UBX response, remains RX-only.
 {Fake f;f.use_nmea=true;f.answers=false;f.receiver={9600,1,2,true};Engine e(f);
  lock(e,f,0,900000);
  assert(same(e.view().selected,f.receiver)&&e.view().current_nmea>=5&&e.view().fix_ok);
  assert(e.view().sats==11&&std::abs(e.view().hdop-.8f)<.001f);
  assert(e.view().tx_replies==0&&std::strstr(e.status(),"NON CONFERMATO"));}
 // Known NMEA checksum vector, bad checksum and overlong recovery.
 {Fake f;f.nav=f.answers=false;Engine e(f);e.start(0);
  const std::string gold="$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n";
  for(unsigned t=0;t<=7000;t+=20){if(t>=2000&&t%1000==0)f.push(Bytes(gold.begin(),gold.end()));step(e,f,t);}
  assert(e.view().phase==Phase::STABLE&&e.view().current_nmea>=5&&e.view().sats==8);
  std::string bad=gold;bad[bad.size()-4]='0';f.push(Bytes(bad.begin(),bad.end()));step(e,f,7020);
  assert(e.view().phase==Phase::VERIFY&&e.view().current_bad>=1);
  std::string big="$GPGGA,"+std::string(400,'X')+"*00\r\n";f.push(Bytes(big.begin(),big.end()));step(e,f,7040);
  for(unsigned t=7060;t<=14000;t+=20){if(t%1000==0)f.push(Bytes(gold.begin(),gold.end()));step(e,f,t);}
  assert(e.view().phase==Phase::STABLE);}
 // Fragmented sentences across loop iterations preserve parser state.
 {Fake f;f.answers=false;f.use_nmea=true;f.fragment_limit=3;f.receiver={230400,1,0,false};Engine e(f);
  lock(e,f,0,30000);assert(e.view().current_nmea>=5&&e.view().fix_ok);}
 // Losing output reopens scanning; a receiver rebooted at another baud is found.
 {Fake f;f.receiver={230400,1,0,false};Engine e(f);const auto t=lock(e,f,0);f.powered=false;
  for(unsigned dt=20;dt<11000;dt+=20)step(e,f,t+dt);
  assert(e.view().phase!=Phase::STABLE&&e.view().lost>=1);
  f.receiver={38400,1,0,false};f.powered=true;bool found=false;
  for(unsigned dt=11000;dt<35000;dt+=20){step(e,f,t+dt);if(e.view().phase==Phase::STABLE){found=true;break;}}
  assert(found&&same(e.view().selected,f.receiver));}
 // Hardware errors require a fresh stable window, but don't change the GPS settings.
 {Fake f;f.receiver={230400,1,0,false};Engine e(f);const auto t=lock(e,f,0);
  e.note_io_errors(1,t);assert(e.view().phase==Phase::VERIFY);
  for(unsigned dt=20;dt<3000;dt+=20){step(e,f,t+dt);assert(e.view().phase!=Phase::STABLE);}
  for(unsigned dt=3000;dt<6000;dt+=20)step(e,f,t+dt);
  assert(e.view().phase==Phase::STABLE&&e.view().uart_errors==1);}
 // Wrap-safe millis comparisons using quiet-receiver query replies.
 {Fake f;f.nav=false;f.receiver={230400,1,0,false};Engine e(f);lock(e,f,UINT32_MAX-2500,30000);assert(e.view().current_ubx>=5);}
 // Failed UART opens advance without issuing queries or blocking.
 {Fake f;f.fail_all=true;f.nav=f.answers=false;Engine e(f);e.start(0);
  for(unsigned t=0;t<12000;t+=20)step(e,f,t);
  assert(e.view().open_errors>396&&f.tx.empty()&&e.view().phase==Phase::SEARCH);}
 // Silence completes the entire search and starts another pass, rather than hanging.
 {Fake f;f.nav=f.answers=false;Engine e(f);e.start(0);
  for(uint32_t t=0;t<900000;t+=20)step(e,f,t);
  assert(e.view().cycle>=2&&f.opened.size()>TRIALS&&e.view().phase==Phase::SEARCH&&e.view().bytes==0);}
 std::cout<<"PASS: 396 search candidates, real checksums, echo/noise rejection, UBX/NMEA, no-fix link,\n"
          <<"read-only discovery, stable window, UART errors, loss/reacquisition and millis wrap\n";
}
