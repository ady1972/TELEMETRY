#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#include "goats_step3_store.h"
namespace goats_step3 {bool stop();bool free_start();bool arm();void catalog_changed();const char *status();}
namespace goats_step3_usb {
struct State {
 uint8_t output[8192]{};unsigned rd=0,wr=0,size=0;
 bool ready=false,raw_tx=false,listing=false,file=false;
 size_t raw_at=0;unsigned list_at=0,list_count=0,burst=0;
 uint32_t activity=0,sent=0,total=0,crc=~0u;
 goats_step3_store::Reader reader;
};
inline State &state(){static State s;return s;}
inline bool write(const void *p,size_t n){auto&s=state();if(n>sizeof(s.output)-s.size)return false;auto*b=static_cast<const uint8_t*>(p);for(size_t i=0;i<n;i++){s.output[s.wr]=b[i];s.wr=(s.wr+1)%sizeof(s.output);}s.size+=n;return true;}
inline bool reply(const std::string&line){if(line.size()+1>sizeof(state().output)-state().size)return false;return write(line.data(),line.size())&&write("\n",1);}
inline bool catalog_busy(){const auto&m=goats_step3_store::state();return m.active||m.queued||m.stopping||m.erasing||goats_session_ctl::has_started();}
inline bool busy(){return !goats_step3_store::idle()||goats_session_ctl::has_started();}
inline std::string hex(const std::string&v){const char*d="0123456789ABCDEF";std::string out;for(uint8_t c:v){out+=d[c>>4];out+=d[c&15];}return out;}
inline int unhex(char c){if(c>='0'&&c<='9')return c-'0';if(c>='A'&&c<='F')return c-'A'+10;if(c>='a'&&c<='f')return c-'a'+10;return -1;}
inline bool file_id(const std::string&encoded,uint32_t&id){
 if(encoded.size()>64||(encoded.size()&1))return false;std::string name;
 for(size_t i=0;i<encoded.size();i+=2){int a=unhex(encoded[i]),b=unhex(encoded[i+1]);if(a<0||b<0)return false;name+=char(a*16+b);}
 auto&s=goats_step3_store::state();for(unsigned i=0;i<s.count;i++)if(!s.sessions[i].deleted&&name==goats_step3_store::filename(s.sessions[i])){id=s.sessions[i].header.sid;return true;}return false;
}
inline bool validate(const std::vector<uint8_t>&raw,std::vector<goats_b::Track>&tracks){
 if(!goats_b::parse_catalog(raw,tracks))return false;
 for(const auto&t:tracks){
  if(!std::isfinite(t.a)||!std::isfinite(t.b)||!std::isfinite(t.c)||!std::isfinite(t.d)||!std::isfinite(t.radius)||t.radius<=0||t.radius>2000||t.direction>2)return false;
  for(const auto&s:t.sectors)if(!std::isfinite(s.a)||!std::isfinite(s.b)||!std::isfinite(s.c)||!std::isfinite(s.d)||fabs(s.a)>90||fabs(s.c)>90||fabs(s.b)>180||fabs(s.d)>180)return false;
 }return true;
}
inline void cancel(){auto&s=state();s.raw_tx=false;s.listing=false;s.file=false;s.burst=0;}
inline void command(const std::string&c){
 auto&s=state();auto&b=goats_b::state();auto&m=goats_step3_store::state();s.activity=::millis();
 if(c=="GSD_PING"){reply("GSD_PONG TEST3_INTERNAL");return;}
 if(c=="GSD_CAPS"){reply("GSD_CAPS BURST4=1 CHUNK=1024 INTERNAL=1");return;}
 if(c=="GSD_STATUS"){
  char line[220];snprintf(line,sizeof(line),"GSD_STATUS READY=%u LIVE=%u SESSION=%u LIST=%u INTERNAL=1 PTS=%lu DROP=%lu FREE=%lu USB=1",m.ready&&!m.erasing,m.active!=0||m.queued!=0,goats_session_ctl::has_started(),s.listing,(unsigned long)(m.count?m.sessions[m.count-1].points:0),(unsigned long)(m.active?m.dropped:m.last_dropped),(unsigned long)(m.partition?m.partition->size-m.next:0));reply(line);return;
 }
 if(c=="GREC_STATUS"){reply(goats_step3::status());return;}
 if(c=="GREC_STOP"){reply(goats_step3::stop()?"GREC_STOP_OK":"GREC_ERR MOVING_OR_IDLE");return;}
 if(c=="GREC_START"){reply(goats_step3::free_start()?"GREC_START_OK":"GREC_ERR BUSY_OR_STORAGE");return;}
 if(c=="GREC_ARM"){reply(goats_step3::arm()?"GREC_ARM_OK":"GREC_ERR BUSY");return;}
 if(c=="GREC_ERASE"){if(s.file||s.raw_tx||s.listing||busy())reply("GREC_ERR BUSY");else reply(goats_step3_store::erase_begin()?"GREC_ERASING":"GREC_ERR STORAGE");return;}
 if(c=="GSD_CANCEL"){cancel();reply("GSD_CANCEL_OK");return;}
 if(c=="GSD_LIST"){
  if(busy()){reply("GSD_ERR BUSY_OR_NOT_READY");return;}cancel();s.listing=true;s.list_at=s.list_count=0;reply("GSD_LIST_BEGIN");return;
 }
 if(c.rfind("GSD_GET ",0)==0){
  if(busy()){reply("GSD_ERR BUSY_OR_NOT_READY");return;}cancel();uint32_t id=0;
  if(!file_id(c.substr(8),id)||!s.reader.open(id)){reply("GSD_ERR NAME_OR_READ");return;}
  s.file=true;s.sent=0;s.crc=~0u;s.total=goats_step3_store::file_size(*goats_step3_store::find(id));reply("GSD_BEGIN "+std::to_string(s.total));return;
 }
 if(c=="GSD_NEXT"||c=="GSD_NEXT4"){
  if(!s.file||s.burst){reply("GSD_ERR NO_TRANSFER");return;}if(busy()){s.file=false;reply("GSD_ERR BUSY_OR_NOT_READY");return;}s.burst=c=="GSD_NEXT4"?4:1;return;
 }
 if(c.rfind("GSD_DELETE ",0)==0){uint32_t id=0;if(s.file||s.raw_tx||s.listing||busy()){reply("GSD_ERR BUSY_OR_NOT_READY");return;}reply(file_id(c.substr(11),id)&&goats_step3_store::delete_session(id)?"GSD_DELETE_OK":"GSD_ERR NAME_OR_STORAGE");return;}
 if(c=="GTRK_GET"){
  if(s.file||s.raw_tx||s.listing||catalog_busy()){reply("GTRK_ERR BUSY");return;}
  if(b.raw.empty())b.raw={'G','T','C','3',1,0,0,0};
  char line[70];snprintf(line,sizeof(line),"GTRK_DATA %u %08lX",(unsigned)b.raw.size(),(unsigned long)goats_b::crc32(b.raw.data(),b.raw.size()));reply(line);s.raw_tx=true;s.raw_at=0;return;
 }
 if(c=="GTRK_CLEAR"){
  if(catalog_busy()||s.file||s.raw_tx||s.listing){reply("GTRK_ERR BUSY");return;}
  std::vector<uint8_t>empty={'G','T','C','3',1,0,0,0};
  if(!goats_b::save(empty)){reply("GTRK_ERR STORAGE");return;}b.raw=empty;b.tracks.clear();goats_step3::catalog_changed();reply("GTRK_CLEAR_OK");return;
 }
 unsigned long n=0,crc=0;char trailing=0;
 if(sscanf(c.c_str(),"GTRK_BEGIN %lu %lx %c",&n,&crc,&trailing)==2&&n>=8&&n<=60000){
  if(catalog_busy()||s.file||s.raw_tx||s.listing){reply("GTRK_ERR BUSY");return;}
  b.need=n;b.expected_crc=crc;b.incoming.clear();b.incoming.reserve(n);b.receiving=true;reply("GTRK_READY");return;
 }
 // Explicitly report unsupported legacy/MSC protocols, never fake empty success.
 reply(c.rfind("GSD",0)==0?"GSD_ERR COMMAND":"GTRK_ERR COMMAND");
}
inline void input(uint8_t v){
 auto&b=goats_b::state();auto&s=state();s.activity=::millis();
 if(b.receiving){
  b.incoming.push_back(v);if(b.incoming.size()<b.need)return;b.receiving=false;
  std::vector<goats_b::Track>tracks;
  if(goats_b::crc32(b.incoming.data(),b.incoming.size())!=b.expected_crc)reply("GTRK_ERR CRC");
  else if(!validate(b.incoming,tracks))reply("GTRK_ERR FORMAT");
  else if(catalog_busy())reply("GTRK_ERR BUSY");
  else if(!goats_b::save(b.incoming))reply("GTRK_ERR STORAGE");
  else {b.raw=std::move(b.incoming);b.tracks=std::move(tracks);goats_step3::catalog_changed();reply("GTRK_OK "+std::to_string(b.tracks.size()));}
  b.incoming.clear();return;
 }
 if(v=='\n'){command(b.command);b.command.clear();}else if(v!='\r'){if(b.command.size()<127)b.command.push_back(char(v));else b.command="INVALID";}
}
inline void init(){
 auto&s=state();usb_serial_jtag_driver_config_t cfg{};cfg.rx_buffer_size=8192;cfg.tx_buffer_size=4096;
 const auto result=usb_serial_jtag_driver_install(&cfg);s.ready=result==ESP_OK||result==ESP_ERR_INVALID_STATE;goats_b::state().usb=s.ready;
}
inline void tick(){
 auto&s=state();auto&b=goats_b::state();if(!s.ready)return;
 // Keep all USB writes nonblocking, including disconnected/slow hosts.
 if(s.size){const unsigned n=std::min<unsigned>({512,s.size,unsigned(sizeof(s.output)-s.rd)});int written=usb_serial_jtag_write_bytes(s.output+s.rd,n,0);if(written>0){s.rd=(s.rd+written)%sizeof(s.output);s.size-=written;}}
 if(s.size<6144){uint8_t bytes[256];const int n=usb_serial_jtag_read_bytes(bytes,sizeof(bytes),0);for(int i=0;i<n;i++)input(bytes[i]);}
 if(b.receiving&&uint32_t(::millis()-s.activity)>10000){b.receiving=false;b.incoming.clear();reply("GTRK_ERR RX_TIMEOUT");}
 if((s.file||s.raw_tx)&&uint32_t(::millis()-s.activity)>15000)cancel();
 if(s.size>4096)return;
 if(s.raw_tx){
  if(s.raw_at<b.raw.size()){const size_t n=std::min<size_t>(512,b.raw.size()-s.raw_at);write(b.raw.data()+s.raw_at,n);s.raw_at+=n;s.activity=::millis();}
  else {s.raw_tx=false;reply("GTRK_END");}return;
 }
 if(s.listing){
  auto&m=goats_step3_store::state();
  while(s.list_at<m.count){auto&f=m.sessions[s.list_at++];if(f.deleted||!f.points)continue;reply("GSD_ITEM "+hex(goats_step3_store::filename(f))+" "+std::to_string(goats_step3_store::file_size(f)));++s.list_count;return;}
  s.listing=false;reply("GSD_LIST_END "+std::to_string(s.list_count));return;
 }
 if(s.burst){
  if(s.sent==s.total){char line[40];snprintf(line,sizeof(line),"GSD_END %08lX",(unsigned long)(~s.crc));reply(line);s.file=false;s.burst=0;return;}
  uint8_t buffer[1024];const size_t n=s.reader.read(buffer,std::min<uint32_t>(sizeof(buffer),s.total-s.sent));
  if(s.reader.error||!n){reply("GSD_ERR READ");s.file=false;s.burst=0;return;}
  static const char*d="0123456789ABCDEF";char line[2053];memcpy(line,"GSD ",4);for(size_t i=0;i<n;i++){line[4+i*2]=d[buffer[i]>>4];line[5+i*2]=d[buffer[i]&15];}line[4+n*2]=0;reply(line);
  s.crc=goats_step3_store::crc32(buffer,n,s.crc);s.sent+=n;--s.burst;if(s.sent==s.total)s.burst=0; // EOF is returned on the next NEXT request.
  s.activity=::millis();
 }
}
}
#endif
