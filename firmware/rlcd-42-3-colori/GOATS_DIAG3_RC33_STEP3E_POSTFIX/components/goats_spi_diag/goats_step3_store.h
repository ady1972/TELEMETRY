#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#include "esp_partition.h"
#include "nvs.h"
#include "rc33_goats_recording_clock.h"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
// Append-only journal in the existing, dedicated goatsfs partition. No mount,
// GPIO/SD access, automatic formatting, cyclic overwrite or flash I/O in PVT.
namespace goats_step3_store {
constexpr uint32_t BEGIN=0x33545301,NAME1=0x33545302,NAME2=0x33545303,
                   POINT=0x33545304,END=0x33545305,DELETED=0x33545306;
constexpr unsigned QUEUE=512,MAX_SESSIONS=64;
#pragma pack(push,1)
struct Point {uint32_t elapsed;int32_t lat,lon;float speed;uint16_t lap,hdop;uint8_t sats,fix;uint16_t seq;};
struct Header {uint32_t sid,itow;uint16_t year;uint8_t month,day,hour,minute,second,free;uint8_t reserved[8];};
struct Record {uint32_t kind;uint8_t payload[24];uint32_t crc;};
#pragma pack(pop)
static_assert(sizeof(Point)==24 && sizeof(Header)==24 && sizeof(Record)==32);
inline uint32_t crc32(const uint8_t*p,size_t n,uint32_t c=~0u){for(size_t i=0;i<n;i++){c^=p[i];for(int k=0;k<8;k++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return c;}
inline Record record(uint32_t kind,const void*p=nullptr,size_t n=0){Record r{};r.kind=kind;if(p)memcpy(r.payload,p,std::min<size_t>(n,24));r.crc=~crc32(reinterpret_cast<const uint8_t*>(&r),28);return r;}
inline bool valid(const Record&r){return r.kind>=BEGIN && r.kind<=DELETED && r.crc==~crc32(reinterpret_cast<const uint8_t*>(&r),28);}
inline bool blank(const void*p,size_t n){auto*b=static_cast<const uint8_t*>(p);for(size_t i=0;i<n;i++)if(b[i]!=255)return false;return true;}
struct Session {Header header{};char track[49]{};uint32_t start=0,end=0,points=0,body_bytes=0,dropped=0;bool deleted=false,closed=false;};
struct State {
 const esp_partition_t *partition=nullptr;
 Session sessions[MAX_SESSIONS]{};unsigned count=0;
 Record queue[QUEUE]{};unsigned rd=0,wr=0,queued=0;
 uint32_t next=0,scan=0,max_id=0,active=0,last_itow=0,elapsed=0,nav_seq=0;
 uint32_t dropped=0,last_dropped=0,erase_at=0;
 bool ready=false,scanning=false,readonly=false,recording=false,stopping=false,erasing=false;
 const char *stage="INIT";
};
inline State &state(){static State s;return s;}
inline Session *find(uint32_t id){auto&s=state();for(unsigned i=0;i<s.count;i++)if(s.sessions[i].header.sid==id)return &s.sessions[i];return nullptr;}
inline int point_line(const Point&p,char*out,size_t n){return snprintf(out,n,"%lu,%u,%.7f,%.7f,%.2f,%.2f,%u\n",(unsigned long)p.elapsed,p.lap,double(p.lat)*1e-7,double(p.lon)*1e-7,double(p.speed),p.hdop==65535?-1.0:double(p.hdop)/100,p.sats);}
inline std::string header_text(const Session&s){
 char date[16],time[16],text[384];
 goats_clock::DateTime dt{s.header.year,s.header.month,s.header.day,s.header.hour,s.header.minute,s.header.second};
 goats_clock::format(dt,date,sizeof(date),time,sizeof(time));
 snprintf(text,sizeof(text),"# GOATS RT RC3.3 STEP3 FULL TRACE 25Hz\n# mode=%s,date=%s,time=%s,track=%s,tz=Europe/Rome,firmware=DIAG3_RC33_STEP3\nelapsed_ms,lap,latitude,longitude,speed_kmh,hdop,satellites\n",s.header.free?"FREE":"CIRCUIT",date,time,s.track);
 return text;
}
inline uint32_t file_size(const Session&s){return header_text(s).size()+s.body_bytes;}
inline std::string filename(const Session&s){char name[24];snprintf(name,sizeof(name),"S%06lu.CSV",(unsigned long)s.header.sid);return name;}
inline bool read_record(uint32_t offset,Record&r){auto&s=state();return s.partition&&offset+32<=s.partition->size&&esp_partition_read(s.partition,offset,&r,32)==ESP_OK;}
inline void apply(const Record&r,uint32_t offset){
 auto&s=state();
 if(r.kind==BEGIN){
  if(s.count>=MAX_SESSIONS){s.readonly=true;s.stage="INDICE PIENO";return;}
  if(s.count)s.sessions[s.count-1].closed=true;
  auto &session=s.sessions[s.count++];session={};memcpy(&session.header,r.payload,24);
  session.start=offset;session.end=offset+32;s.max_id=std::max(s.max_id,session.header.sid);return;
 }
 if(r.kind==DELETED){uint32_t id;memcpy(&id,r.payload,4);if(auto *p=find(id))p->deleted=true;return;}
 if(!s.count){s.readonly=true;s.stage="LOG NON VALIDO";return;}
 auto &session=s.sessions[s.count-1];session.end=offset+32;
 if(r.kind==NAME1)memcpy(session.track,r.payload,24);
 if(r.kind==NAME2){memcpy(session.track+24,r.payload,24);session.track[48]=0;}
 if(r.kind==POINT){Point p;memcpy(&p,r.payload,24);char line[160];session.body_bytes+=point_line(p,line,sizeof(line));++session.points;}
 if(r.kind==END){memcpy(&session.dropped,r.payload,4);session.closed=true;}
}
inline void init(){auto&s=state();if(s.partition)return;s.partition=esp_partition_find_first(ESP_PARTITION_TYPE_DATA,ESP_PARTITION_SUBTYPE_ANY,"goatsfs");if(!s.partition){s.stage="PARTIZIONE ASSENTE";return;}s.scanning=true;s.stage="SCANSIONE";}
inline void scan_step(){
 auto&s=state();
 for(unsigned i=0;i<64&&s.scanning;i++){
  Record r;
  if(s.scan+32>s.partition->size){s.next=s.scan;s.readonly=true;s.stage="MEMORIA PIENA";s.scanning=false;break;}
  if(!read_record(s.scan,r)){s.readonly=true;s.stage="LETTURA FALLITA";s.scanning=false;break;}
  if(blank(&r,32)){s.next=s.scan;s.scanning=false;break;}
  if(!valid(r)){s.next=s.scan;s.readonly=true;s.stage=s.scan?"RECUPERO PARZIALE":"MEMORIA SCONOSCIUTA";s.scanning=false;break;}
  apply(r,s.scan);s.scan+=32;
 }
 if(!s.scanning){s.ready=true;if(s.count)s.sessions[s.count-1].closed=true;if(!s.readonly)s.stage="PRONTA";}
}
inline bool idle(){auto&s=state();return s.ready&&!s.erasing&&!s.active&&!s.queued&&!s.stopping;}
// Reserve IDs outside the PVT callback, so erasing telemetry never reuses a
// filename already imported/deleted in the Manager. Only one NVS commit/block.
inline uint32_t id_floor=0,id_limit=0,id_retry=0;
inline void reserve_ids(){
 auto&s=state();if(!s.ready||s.readonly||s.erasing||id_floor<id_limit||int32_t(::millis()-id_retry)<0)return;
 id_retry=::millis()+1000;nvs_handle_t h;
 if(nvs_open("goats_rec3",NVS_READWRITE,&h)!=ESP_OK){s.stage="ID NON PRONTO";return;}
 uint32_t previous=1;nvs_get_u32(h,"next",&previous);
 uint32_t base=std::max({previous,s.max_id+1,id_floor+1});
 if(base>=0xffffff00u || nvs_set_u32(h,"next",base+256)!=ESP_OK || nvs_commit(h)!=ESP_OK){s.stage="ID NON PRONTO";nvs_close(h);return;}
 nvs_close(h);id_floor=base-1;id_limit=base+255;s.stage="PRONTA";
}
inline bool can_begin(){auto&s=state();if(!idle()||s.readonly)return false;
 if(s.count>=MAX_SESSIONS){s.stage="INDICE PIENO";return false;}
 if(s.next+128>s.partition->size){s.stage="MEMORIA PIENA";s.readonly=true;return false;}
 return id_floor<id_limit;
}
inline bool enqueue(const Record&r){auto&s=state();if(s.queued>=QUEUE){++s.dropped;return false;}s.queue[s.wr]=r;s.wr=(s.wr+1)%QUEUE;++s.queued;return true;}
inline bool begin(const char *track,const goats_clock::DateTime&dt,uint32_t itow,bool free){
 auto&s=state();if(!can_begin())return false;
 Header h{};h.sid=++id_floor;s.max_id=std::max(s.max_id,h.sid);h.itow=itow;h.year=dt.year;h.month=dt.month;h.day=dt.day;h.hour=dt.hour;h.minute=dt.minute;h.second=dt.second;h.free=free;
 char name[48]{};snprintf(name,sizeof(name),"%s",track?track:"AUTO");for(char &c:name)if(c==','||c=='\r'||c=='\n')c=' ';
 enqueue(record(BEGIN,&h,24));enqueue(record(NAME1,name,24));enqueue(record(NAME2,name+24,24));
 s.active=h.sid;s.recording=true;s.stopping=false;s.dropped=0;s.elapsed=0;s.last_itow=itow;s.nav_seq=0;s.stage="REGISTRAZIONE";return true;
}
// Called only after a distinct validated NAV-PVT: copies one point into RAM.
inline void observe(uint32_t itow,uint32_t lap,int32_t lat,int32_t lon,float speed,float hdop,uint8_t sv,uint8_t fix){
 auto&s=state();if(!s.recording)return;
 constexpr uint32_t WEEK=604800000;
 uint32_t step=itow>=s.last_itow?itow-s.last_itow:WEEK-s.last_itow+itow;
 if(step>WEEK/2){++s.dropped;return;}
 s.elapsed+=step;s.last_itow=itow;
 Point p{s.elapsed,lat,lon,speed,uint16_t(std::min<uint32_t>(lap,65535)),uint16_t(std::isfinite(hdop)&&hdop>=0?std::min(65534.0f,roundf(hdop*100)):65535),sv,fix,uint16_t(s.nav_seq++)};
 enqueue(record(POINT,&p,24));
}
inline void stop(){auto&s=state();if(!s.active)return;s.recording=false;s.stopping=true;s.stage="CHIUSURA";}
inline void fail(const char *reason){auto&s=state();s.stage=reason;s.readonly=true;s.recording=false;s.stopping=false;s.last_dropped=s.dropped+s.queued;s.queued=0;s.rd=s.wr=0;s.active=0;if(s.count)s.sessions[s.count-1].closed=true;}
inline bool append(const Record *records,unsigned count){
 auto&s=state();const size_t bytes=count*32;
 if(s.next+bytes>s.partition->size){fail("MEMORIA PIENA");return false;}
 uint8_t previous[256];if(bytes>sizeof(previous)||esp_partition_read(s.partition,s.next,previous,bytes)!=ESP_OK){fail("LETTURA FALLITA");return false;}
 if(!blank(previous,bytes)){fail("AREA NON VUOTA");return false;}
 if(esp_partition_write(s.partition,s.next,records,bytes)!=ESP_OK){fail("SCRITTURA FALLITA");return false;}
 for(unsigned i=0;i<count;i++){apply(records[i],s.next);s.next+=32;}return true;
}
inline bool erase_begin(){auto&s=state();if(!idle()||!s.partition)return false;s.erasing=true;s.ready=false;s.erase_at=0;s.stage="CANCELLAZIONE";return true;}
inline bool erase_one(){auto&s=state();if(esp_partition_erase_range(s.partition,s.erase_at,4096)!=ESP_OK){s.erasing=false;s.ready=true;fail("ERASE FALLITO");return false;}s.erase_at+=4096;if(s.erase_at>=s.partition->size){s.count=0;s.rd=s.wr=s.queued=0;s.next=s.scan=s.max_id=s.active=0;
 s.last_itow=s.elapsed=s.nav_seq=s.dropped=s.last_dropped=s.erase_at=0;
 s.ready=false;s.scanning=true;s.readonly=s.recording=s.stopping=s.erasing=false;
 memset(s.sessions,0,sizeof(s.sessions));s.stage="SCANSIONE";}return true;}
inline bool delete_session(uint32_t id){auto*p=find(id);if(!idle()||!p||p->deleted)return false;const auto r=record(DELETED,&id,4);return append(&r,1);}
inline void tick(){
 auto&s=state();if(!s.partition)return;
 if(s.erasing){erase_one();return;}if(s.scanning){scan_step();return;}if(s.readonly)return;
 if(s.queued){const unsigned n=std::min<unsigned>({8,s.queued,QUEUE-s.rd});if(append(s.queue+s.rd,n)){s.rd=(s.rd+n)%QUEUE;s.queued-=n;}return;}
 if(s.stopping){const auto r=record(END,&s.dropped,4);if(append(&r,1)){s.last_dropped=s.dropped;s.active=0;s.stopping=false;s.stage="PRONTA";}}
}
struct Reader {
 uint32_t sid=0,offset=0,end=0;char line[384]{};size_t at=0,length=0;bool error=false;
 bool open(uint32_t id){auto*p=find(id);if(!idle()||!p||p->deleted||!p->points)return false;sid=id;offset=p->start;end=p->end;auto h=header_text(*p);memcpy(line,h.data(),h.size());at=0;length=h.size();error=false;return true;}
 size_t read(uint8_t*out,size_t n){size_t done=0;while(done<n){
  if(at<length){const size_t take=std::min(n-done,length-at);memcpy(out+done,line+at,take);at+=take;done+=take;continue;}
  bool found=false;while(offset<end){Record r;if(!read_record(offset,r)||!valid(r)){error=true;return done;}offset+=32;if(r.kind==POINT){Point p;memcpy(&p,r.payload,24);length=point_line(p,line,sizeof(line));at=0;found=true;break;}}
  if(!found)break;
 }return done;}
};
}
#endif
