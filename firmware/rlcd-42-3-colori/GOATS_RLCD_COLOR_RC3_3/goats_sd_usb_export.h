#pragma once
// GOATS MG902 TEST25: FatFS read-only export. No change to GNSS/UART/recording.
#include <cstdio>
#include <cstring>
#include <string>
#include <algorithm>
#include "driver/usb_serial_jtag.h"
#include "goats_sd_storage.h"
#include "goats_session_control.h"
#include "goats_sd_r14_bridge.h"
namespace goats_sd_usb_export {
struct State {
  FIL file{}; bool file_open=false; uint32_t size=0, sent=0, crc=0xFFFFFFFFu, last_ms=0;
  FF_DIR listing{}; bool listing_open=false, root_phase=false;
  uint32_t num_items=0;
};
inline State& state(){static State v;return v;}
inline bool reply(const char* str){
  size_t n=strlen(str);int w=usb_serial_jtag_write_bytes(str,n,pdMS_TO_TICKS(60));
  if(w!=(int)n)return false;
  return usb_serial_jtag_write_bytes("\n",1,pdMS_TO_TICKS(60))==1;
}
inline void close_file(){auto&s=state();if(s.file_open){f_close(&s.file);s.file_open=false;}}
inline void stop_list(){auto&s=state();if(s.listing_open){f_closedir(&s.listing);s.listing_open=false;}}
inline bool available(){return goats_sd_storage::ready() && !goats_sd_storage::live_open() && !goats_session_ctl::has_started();}
inline std::string hex_encode(const std::string&v){static const char*d="0123456789ABCDEF";std::string r;for(unsigned char c:v){r+=d[c>>4];r+=d[c&15];}return r;}
inline int hval(char c){if(c>='0'&&c<='9')return c-'0';if(c>='A'&&c<='F')return c-'A'+10;if(c>='a'&&c<='f')return c-'a'+10;return -1;}
inline bool hex_decode(const std::string&s,std::string&out){if(s.empty()||s.size()>160||(s.size()&1))return false;out.clear();for(size_t i=0;i<s.size();i+=2){int a=hval(s[i]),b=hval(s[i+1]);if(a<0||b<0)return false;out+=char((a<<4)|b);}return true;}
inline void errfr(const char*prefix,FRESULT fr){char buf[80];snprintf(buf,sizeof(buf),"GSD_ERR %s_%u",prefix,(unsigned)fr);reply(buf);}
inline void start_root(){
  auto&s=state();s.root_phase=true;
  const FRESULT fr=f_opendir(&s.listing,"0:/");
  if(fr!=FR_OK){errfr("ROOT",fr);return;}
  s.listing_open=true;
}
inline void begin_list(){
  stop_list();close_file();auto&s=state();s.num_items=0;s.root_phase=false;
  if(!available()){reply("GSD_ERR BUSY_OR_NOT_READY");return;}
  const FRESULT fr=f_opendir(&s.listing,"0:/GOATS");
  if(fr!=FR_OK){errfr("GOATS_DIR",fr);return;}
  s.listing_open=true;reply("GSD_LIST_BEGIN");
}
inline void list_step(){
  auto&s=state();
  for(int step=0;step<2 && s.listing_open;++step){
    FILINFO info{};FRESULT fr=f_readdir(&s.listing,&info);
    if(fr!=FR_OK){stop_list();errfr("READDIR",fr);return;}
    if(info.fname[0]==0){
      stop_list();
      if(!s.root_phase){start_root();if(!s.listing_open)return;}
      else {char buf[50];snprintf(buf,sizeof(buf),"GSD_LIST_END %lu",(unsigned long)s.num_items);reply(buf);}
      continue;
    }
    if(info.fattrib & AM_DIR)continue;
    std::string name(info.fname);
    if(!goats_sd_storage::valid_user_file_name_(name.c_str()))continue;
    if(!s.root_phase && (name=="archive.tmp" || name=="session_checkpoint.tmp"))continue;
    if(s.root_phase){
      // Only session-like files in SD root; never system files / folders.
      auto dot=name.find_last_of('.');
      if(dot==std::string::npos)continue;
      std::string ext=name.substr(dot);for(char &c:ext)if(c>='a'&&c<='z')c-=32;
      if(ext!=".CSV"&&ext!=".GSA3"&&ext!=".TXT")continue;
    }
    std::string label=std::string(s.root_phase?"ROOT:":"")+name;
    std::string line="GSD_ITEM "+hex_encode(label)+" "+std::to_string((unsigned long)info.fsize);
    if(!reply(line.c_str())){stop_list();return;}
    ++s.num_items;
  }
}
inline bool handle_command(const std::string&c){
  if(c=="GSD_PING"){reply("GSD_PONG TEST25");return true;}
  if(c=="GSD_CAPS"){reply("GSD_CAPS BURST4=1 CHUNK=1024");return true;}
  if(c=="GSD_STATUS"){
    // L’utente ha richiesto esplicitamente la microSD: disponibile anche senza fix.
    if(!goats_sd_storage::ready() && !goats_session_ctl::has_started()) goats_sd_r14_bridge::begin();
    auto&s=state();char msg[128];snprintf(msg,sizeof(msg),"GSD_STATUS READY=%u LIVE=%u SESSION=%u LIST=%u",(unsigned)goats_sd_storage::ready(),(unsigned)goats_sd_storage::live_open(),(unsigned)goats_session_ctl::has_started(),(unsigned)s.listing_open);reply(msg);return true;
  }
  if(c=="GSD_LIST"){
    if(!goats_sd_storage::ready() && !goats_session_ctl::has_started()) goats_sd_r14_bridge::begin();
    begin_list();return true;}
  if(c=="GSD_CANCEL"){close_file();stop_list();reply("GSD_CANCEL_OK");return true;}
  if(c.rfind("GSD_GET ",0)==0){
    close_file();stop_list();
    if(!goats_sd_storage::ready() && !goats_session_ctl::has_started()) goats_sd_r14_bridge::begin();
    if(!available()){reply("GSD_ERR BUSY_OR_NOT_READY");return true;}
    std::string name;if(!hex_decode(c.substr(8),name)){reply("GSD_ERR NAME");return true;}
    std::string path="0:/GOATS/";
    if(name.rfind("ROOT:",0)==0){path="0:/";name=name.substr(5);}
    if(!goats_sd_storage::valid_user_file_name_(name.c_str())){reply("GSD_ERR NAME");return true;}
    path+=name;
    FILINFO info{};FRESULT fr=f_stat(path.c_str(),&info);
    if(fr!=FR_OK){errfr("STAT",fr);return true;}
    if(info.fattrib&AM_DIR){reply("GSD_ERR IS_DIR");return true;}
    auto&s=state();fr=f_open(&s.file,path.c_str(),FA_READ|FA_OPEN_EXISTING);
    if(fr!=FR_OK){errfr("OPEN",fr);return true;}
    s.file_open=true;s.size=(uint32_t)f_size(&s.file);s.sent=0;s.crc=0xFFFFFFFFu;s.last_ms=millis();
    char buf[65];snprintf(buf,sizeof(buf),"GSD_BEGIN %lu",(unsigned long)s.size);reply(buf);return true;
  }
  if(c=="GSD_NEXT" || c=="GSD_NEXT4"){
    const unsigned burst=(c=="GSD_NEXT4")?4:1;
    for(unsigned bi=0;bi<burst;++bi){
    auto&s=state();if(!s.file_open){reply("GSD_ERR NO_TRANSFER");break;}
    if(!available()){close_file();reply("GSD_ERR BUSY_OR_NOT_READY");break;}
    if(s.sent==s.size){char line[64];snprintf(line,sizeof(line),"GSD_END %08lX",(unsigned long)(~s.crc));close_file();reply(line);break;}
    constexpr unsigned CHUNK=1024;uint8_t buf[CHUNK];UINT got=0;
    FRESULT fr=f_read(&s.file,buf,(UINT)std::min<uint32_t>(CHUNK,s.size-s.sent),&got);
    if(fr!=FR_OK){close_file();errfr("READ",fr);break;}
    if(!got){close_file();reply("GSD_ERR SHORT_READ");break;}
    static const char*d="0123456789ABCDEF";char line[4+CHUNK*2+1];memcpy(line,"GSD ",4);
    for(unsigned i=0;i<got;++i){line[4+2*i]=d[buf[i]>>4];line[5+2*i]=d[buf[i]&15];}
    line[4+2*got]=0;
    if(!reply(line)){close_file();break;}
    for(unsigned i=0;i<got;++i){s.crc^=buf[i];for(int k=0;k<8;++k)s.crc=(s.crc>>1)^(0xEDB88320u & (0u-(s.crc&1u)));}
    s.sent+=(uint32_t)got;s.last_ms=millis();
    }
    return true;
  }
  return false;
}
inline void tick(){auto&s=state();if(s.file_open&&millis()-s.last_ms>15000)close_file();if(s.listing_open)list_step();}
}
