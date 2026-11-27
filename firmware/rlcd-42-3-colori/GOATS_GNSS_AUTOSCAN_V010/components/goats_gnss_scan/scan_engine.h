#pragma once
#include "ubx_parser.h"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>

namespace goats_scan {
// Search only the existing GPS wires. Port is the ESP peripheral, not GPIO.
inline constexpr uint32_t BAUDS[]={230400,38400,9600,115200,57600,19200,4800,460800,921600,2400,1200};
inline constexpr uint8_t PORTS[]={1,0,2};
inline constexpr const char *FORMATS[]={"8N1","8N2","8E1","8O1","8E2","8O2"};
inline constexpr uint32_t TRIALS=11*3*6*2;
struct Candidate {
  uint32_t baud{230400}; uint8_t port{1}, format{0}; bool inverted{false};
};
inline Candidate candidate(uint32_t index) {
  index%=TRIALS;
  Candidate c;
  c.port=PORTS[index%3];index/=3;
  c.baud=BAUDS[index%11];index/=11;
  c.format=index%6;c.inverted=index>=6;
  return c;
}
class Transport {
 public:
  virtual ~Transport()=default;
  virtual bool open(const Candidate&)=0;
  virtual size_t read(uint8_t*,size_t)=0;
  virtual void write(const uint8_t*,size_t)=0;
  virtual uint32_t actual_baud() const=0;
};
enum class Phase { BOOT, SEARCH, VERIFY, STABLE, RECOVER };
struct View {
  Phase phase{Phase::BOOT}; Candidate selected{};
  uint32_t index{0}, cycle{1}, bytes{0}, current_bytes{0}, ubx{0}, nmea{0}, bad{0};
  uint32_t current_ubx{0},current_nmea{0},current_bad{0},echo{0},uart_errors{0},current_uart_errors{0};
  uint32_t good_run{0}, last_good{0}, since{0}, stable_since{0}, lost{0}, open_errors{0};
  uint32_t tx_polls{0}, tx_replies{0}, pvt_count{0}, last_nav{0}, max_gap{0};
  float pvt_hz{0};uint8_t sats{0},fix_type{0};bool fix_ok{false};float hdop{-1};
  uint32_t receiver_baud{0};uint32_t receiver_mode{0};uint16_t meas_ms{0},nav_rate{0};
  uint16_t input_mask{0},output_mask{0};uint8_t receiver_port{255};
  char model[42]{},sample[46]{},receiver_format[12]{"--"},raw_hex[37]{};
};
class Engine {
 public:
  explicit Engine(Transport &transport):transport_(transport){}
  const View &view() const{return v_;}
  void start(uint32_t now){v_=View{};boot_at_=now;started_=true;}
  const char *status() const {
    switch(v_.phase){
      case Phase::BOOT:return "ATTESA AVVIO GPS";
      case Phase::SEARCH:return "SCANSIONE AUTOMATICA";
      case Phase::VERIFY:return "VERIFICA COMUNICAZIONE";
      case Phase::STABLE:return v_.tx_replies>=2?"LINK RX/TX STABILE":"RX STABILE - TX NON CONFERMATO";
      case Phase::RECOVER:return "FLUSSO PERSO - RECUPERO";
    }return "";
  }
  void note_io_errors(uint32_t total,uint32_t now){
    const uint32_t diff=total-v_.uart_errors;v_.uart_errors=total;
    if(!diff)return;
    v_.current_uart_errors+=diff;v_.good_run=0;run_at_=now;
    if(v_.phase==Phase::STABLE){v_.phase=Phase::VERIFY;verify_at_=now;}
  }
  void tick(uint32_t now){
    now_=now;if(!started_)start(now);
    if(v_.phase==Phase::BOOT){if(elapsed(now,boot_at_)>=1500)select_(now);return;}
    if(!selected_open_){next_(now);return;}
    uint8_t bytes[256];size_t budget=8192;
    while(budget){const size_t n=transport_.read(bytes,std::min(budget,sizeof(bytes)));if(!n)break;
      v_.bytes+=n;v_.current_bytes+=n;budget-=n;
      for(size_t j=0;j<n&&raw_count_<12;j++,raw_count_++)
        std::snprintf(v_.raw_hex+raw_count_*3,sizeof(v_.raw_hex)-raw_count_*3,"%02X ",bytes[j]);
      // Discard boundary bytes briefly after changing port/format, then parse.
      if(elapsed(now,selected_at_)<120)continue;
      for(size_t i=0;i<n;i++)feed_(bytes[i]);
    }
    const uint32_t total_bad=parser_.stats.checksum_errors+parser_.stats.length_errors+nmea_bad_;
    if(total_bad!=observed_bad_){v_.bad+=total_bad-observed_bad_;v_.current_bad+=total_bad-observed_bad_;observed_bad_=total_bad;
      v_.good_run=0;run_at_=now;
      if(v_.phase==Phase::STABLE){v_.phase=Phase::VERIFY;verify_at_=now;}
    }
    if(elapsed(now,rate_at_)>=1000){
      v_.pvt_hz=1000.f*float(v_.pvt_count-rate_base_)/float(elapsed(now,rate_at_));
      rate_base_=v_.pvt_count;rate_at_=now;
    }
    if(v_.phase==Phase::SEARCH){
      // Read-only query also discovers a quiet u-blox with UBX input enabled.
      if(!search_polled_ && elapsed(now,selected_at_)>=1200){monver_(now);search_polled_=true;}
      if(elapsed(now,selected_at_)>=2100)next_(now);
      return;
    }
    if(elapsed(now,last_query_)>=900){
      if(!cfg_port_polled_){poll_(6,0,now);cfg_port_polled_=true;}
      else if(!cfg_rate_polled_){poll_(6,8,now);cfg_rate_polled_=true;}
      else monver_(now);
    }
    if(v_.phase==Phase::VERIFY){
      if(elapsed(now,v_.last_good)>2500){v_.good_run=0;run_at_=now;}
      if(v_.good_run>=5 && elapsed(now,run_at_)>=4000 && elapsed(now,v_.last_good)<2500){
        v_.phase=Phase::STABLE;v_.stable_since=now;
      }else if(elapsed(now,verify_at_)>=14000)next_(now);
    }else if(v_.phase==Phase::STABLE && elapsed(now,v_.last_good)>4000){
      v_.phase=Phase::RECOVER;recover_at_=now;v_.lost++;v_.good_run=0;v_.tx_replies=0;
      parser_.reset();nmea_len_=0;nmea_bad_=observed_bad_=0;monver_pending_=false;
      cfg_port_polled_=cfg_rate_polled_=false;
      selected_open_=transport_.open(v_.selected);
      if(!selected_open_)v_.open_errors++; // Retry the known link first.
    }else if(v_.phase==Phase::RECOVER && elapsed(now,recover_at_)>=4000){
      v_.index=0;v_.cycle++;select_(now);
    }
  }
 private:
  static uint32_t elapsed(uint32_t now,uint32_t before){return now-before;}
  static uint16_t u2_(const uint8_t*p){return uint16_t(p[0])|(uint16_t(p[1])<<8);}
  static uint32_t u4_(const uint8_t*p){return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
  static int hex_(char c){return c>='0'&&c<='9'?c-'0':c>='A'&&c<='F'?c-'A'+10:c>='a'&&c<='f'?c-'a'+10:-1;}
  void select_(uint32_t now){
    v_.selected=candidate(v_.index);v_.phase=Phase::SEARCH;selected_at_=now;
    v_.current_bytes=0;v_.current_ubx=v_.current_nmea=v_.current_bad=v_.current_uart_errors=0;v_.max_gap=0;have_itow_=false;v_.good_run=0;v_.tx_replies=0;v_.stable_since=0;
    v_.sats=v_.fix_type=0;v_.fix_ok=false;v_.hdop=-1;v_.last_nav=0;v_.sample[0]=0;
    v_.receiver_baud=0;v_.receiver_mode=0;v_.receiver_port=255;v_.meas_ms=v_.nav_rate=0;
    v_.input_mask=v_.output_mask=0;v_.model[0]=0;std::strcpy(v_.receiver_format,"--");
    parser_.reset();nmea_len_=0;raw_count_=0;v_.raw_hex[0]=0;nmea_bad_=observed_bad_=0;
    search_polled_=cfg_port_polled_=cfg_rate_polled_=false;monver_pending_=false;
    rate_at_=now;rate_base_=v_.pvt_count;v_.pvt_hz=0;last_query_=now;
    selected_open_=transport_.open(v_.selected);
    if(!selected_open_)v_.open_errors++;
  }
  void next_(uint32_t now){if(++v_.index>=TRIALS){v_.index=0;v_.cycle++;}select_(now);}
  void good_(){
    const auto gap=elapsed(now_,v_.last_good);
    if(v_.good_run && gap>v_.max_gap)v_.max_gap=gap;
    if(!v_.good_run||gap>2500){v_.good_run=0;run_at_=now_;}
    v_.good_run++;v_.last_good=now_;
    if(v_.phase==Phase::SEARCH||v_.phase==Phase::RECOVER){
      v_.phase=Phase::VERIFY;verify_at_=now_;v_.since=now_;
    }
  }
  void feed_(uint8_t c){
    if(parser_.feed(c)){const auto f=parser_.frame();
      const bool poll_reply=(f.cls==0x0A&&f.id==4)||(f.cls==6&&(f.id==0||f.id==8));
      if(poll_reply&&f.len==0){v_.echo++;return;} // TX loopback is not GPS evidence.
      if((f.cls==0x0A&&f.id==4&&f.len<40)||(f.cls==6&&f.id==0&&f.len<20)||
         (f.cls==6&&f.id==8&&f.len<6)||(f.cls==1&&f.id==7&&f.len<92)){
        nmea_bad_++;return;
      }
      v_.ubx++;v_.current_ubx++;good_();
      const auto *p=f.payload;
      if(f.cls==1&&f.id==7&&f.len>=92){
        const auto itow=u4_(p);if(!have_itow_||itow!=last_itow_){v_.pvt_count++;last_itow_=itow;have_itow_=true;}
        v_.fix_type=p[20];v_.fix_ok=p[20]>=2&&(p[21]&1)!=0;v_.sats=p[23];v_.last_nav=now_;
      }else if(f.cls==1&&f.id==4&&f.len>=18)v_.hdop=u2_(p+12)*.01f;
      else if(f.cls==0x0A&&f.id==4&&f.len>=40){
        if(monver_pending_&&elapsed(now_,monver_at_)<=1800){v_.tx_replies++;monver_pending_=false;}
        for(unsigned i=0;i<40;i++)v_.model[i]=p[i]>=32&&p[i]<=126?char(p[i]):' ';
        v_.model[40]=0;
      }else if(f.cls==6&&f.id==0&&f.len>=20){
        v_.receiver_port=p[0];v_.receiver_mode=u4_(p+4);v_.receiver_baud=u4_(p+8);
        v_.input_mask=u2_(p+12);v_.output_mask=u2_(p+14);
        const uint32_t mode=v_.receiver_mode;const unsigned bits=5+((mode>>6)&3);
        const unsigned parity=(mode>>9)&7,stop=(mode>>12)&3;
        std::snprintf(v_.receiver_format,sizeof(v_.receiver_format),"%u%c%s",bits,
          parity==0?'E':parity==1?'O':(parity==4||parity==5)?'N':'?',stop==0?"1":stop==2?"2":stop==1?"1.5":"0.5");
      }else if(f.cls==6&&f.id==8&&f.len>=6){v_.meas_ms=u2_(p);v_.nav_rate=u2_(p+2);}
    }
    nmea_(char(c));
  }
  void nmea_(char c){
    if(c=='$'){nmea_len_=0;nmea_line_[nmea_len_++]=c;return;}
    if(!nmea_len_)return;
    if(c=='\r')return;
    if(c=='\n'){
      nmea_line_[nmea_len_]=0;parse_nmea_();nmea_len_=0;return;
    }
    if(c<32||c>126||nmea_len_>=sizeof(nmea_line_)-1){nmea_len_=0;return;}
    nmea_line_[nmea_len_++]=c;
  }
  void parse_nmea_(){
    if(nmea_len_<10)return;
    const bool standard=nmea_line_[0]=='$'&&nmea_line_[1]>='A'&&nmea_line_[1]<='Z'&&
      nmea_line_[2]>='A'&&nmea_line_[2]<='Z'&&nmea_line_[6]==',';
    const bool proprietary=std::strncmp(nmea_line_,"$PUBX,",6)==0;
    if(!standard&&!proprietary)return;
    for(unsigned i=3;standard&&i<6;i++)if(nmea_line_[i]<'A'||nmea_line_[i]>'Z')return;
    char *star=std::strchr(nmea_line_,'*');
    if(!star||size_t(nmea_line_+nmea_len_-star)!=3)return;
    const int a=hex_(star[1]),b=hex_(star[2]);if(a<0||b<0)return;
    uint8_t checksum=0;for(char *p=nmea_line_+1;p<star;p++)checksum^=uint8_t(*p);
    if(checksum!=((a<<4)|b)){nmea_bad_++;return;}
    v_.nmea++;v_.current_nmea++;good_();
    std::snprintf(v_.sample,sizeof(v_.sample),"%.42s",nmea_line_);
    if(standard&&(std::strncmp(nmea_line_+3,"GGA",3)==0||std::strncmp(nmea_line_+3,"RMC",3)==0)){
      const bool gga=std::strncmp(nmea_line_+3,"GGA",3)==0;
      *star=0;std::array<char*,16> fields{};size_t n=1;fields[0]=nmea_line_;
      for(char *p=nmea_line_;*p&&n<fields.size();p++)if(*p==','){*p=0;fields[n++]=p+1;}
      if(gga&&n>=9){
        const unsigned q=unsigned(std::strtoul(fields[6],nullptr,10));
        v_.fix_ok=q>0;v_.fix_type=q?2:0;v_.sats=std::min<unsigned>(99,std::strtoul(fields[7],nullptr,10));
        v_.hdop=fields[8][0]?std::strtof(fields[8],nullptr):-1.f;v_.last_nav=now_;
      }else if(!gga&&n>=3){v_.fix_ok=std::strcmp(fields[2],"A")==0;v_.fix_type=v_.fix_ok?2:0;v_.last_nav=now_;}
    }
  }
  void poll_(uint8_t cls,uint8_t id,uint32_t now){
    // Only read-only MON-VER / CFG-PRT / CFG-RATE polls; never VALSET/CFG-CFG/RST.
    if(v_.selected.inverted)return; // RX inversion alone does not establish TX polarity.
    const uint8_t a=uint8_t(cls+id);
    // UBX checksum over cls,id,len1,len2: B = cls + 3*(cls+id).
    const uint8_t frame[]={0xB5,0x62,cls,id,0,0,a,uint8_t(cls+3*a)};
    transport_.write(frame,sizeof(frame));v_.tx_polls++;last_query_=now;
  }
  void monver_(uint32_t now){
    if(v_.selected.inverted){last_query_=now;return;}
    poll_(0x0A,4,now);monver_pending_=true;monver_at_=now;
  }
  Transport &transport_;View v_{};ubx::Parser parser_{};
  bool selected_open_{false},started_{false},search_polled_{false},cfg_port_polled_{false},cfg_rate_polled_{false},monver_pending_{false},have_itow_{false};
  uint32_t now_{0},boot_at_{0},selected_at_{0},verify_at_{0},recover_at_{0},run_at_{0},last_query_{0},monver_at_{0};
  uint32_t rate_at_{0},rate_base_{0},last_itow_{0},nmea_bad_{0},observed_bad_{0};
  size_t nmea_len_{0},raw_count_{0};char nmea_line_[256]{};
};
}  // namespace goats_scan
