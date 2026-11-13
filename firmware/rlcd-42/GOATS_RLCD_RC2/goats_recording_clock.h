#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
namespace goats_clock {
struct DateTime { int year{},month{},day{},hour{},minute{},second{}; };
inline bool leap(int y){return y%4==0 && (y%100!=0 || y%400==0);}
inline int days(int y,int m){static constexpr int d[]={31,28,31,30,31,30,31,31,30,31,30,31};return m>=1&&m<=12?d[m-1]+(m==2&&leap(y)):0;}
inline bool valid(const DateTime &t){return t.year>=2020 && t.year<=2099 && t.month>=1 && t.month<=12 && t.day>=1 && t.day<=days(t.year,t.month) && t.hour>=0&&t.hour<24&&t.minute>=0&&t.minute<60&&t.second>=0&&t.second<60;}
inline int weekday(int y,int m,int d){if(m<3){m+=12;--y;}int k=y%100,j=y/100;return ((d+13*(m+1)/5+k+k/4+j/4+5*j)%7+6)%7;}
inline int last_sunday(int y,int m){int n=days(y,m);return n-weekday(y,m,n);}
inline DateTime rome(DateTime utc){
 if(!valid(utc))return {};
 const bool dst=(utc.month>3&&utc.month<10) ||
  (utc.month==3 && (utc.day>last_sunday(utc.year,3)||(utc.day==last_sunday(utc.year,3)&&utc.hour>=1))) ||
  (utc.month==10 && (utc.day<last_sunday(utc.year,10)||(utc.day==last_sunday(utc.year,10)&&utc.hour<1)));
 utc.hour+=dst?2:1;
 if(utc.hour>=24){utc.hour-=24;if(++utc.day>days(utc.year,utc.month)){utc.day=1;if(++utc.month>12){utc.month=1;++utc.year;}}}
 return valid(utc)?utc:DateTime{};
}
inline DateTime from_pvt(const uint8_t *p){if(!p||(p[11]&3)!=3)return {};return rome({int(p[4]|uint16_t(p[5])<<8),p[6],p[7],p[8],p[9],p[10]});}
inline void format(const DateTime &t,char *date,size_t nd,char *time,size_t nt){
 if(!valid(t)){if(nd)date[0]=0;if(nt)time[0]=0;return;}
 std::snprintf(date,nd,"%04d-%02d-%02d",t.year,t.month,t.day);
 std::snprintf(time,nt,"%02d:%02d:%02d",t.hour,t.minute,t.second);
}
inline DateTime parse(const char *date,const char *time){
 DateTime t{};if(!date||!time)return t;
 if(std::strchr(date,'/')){if(std::sscanf(date,"%d/%d/%d",&t.day,&t.month,&t.year)!=3)return {};}
 else if(std::strchr(date,'-')){if(std::sscanf(date,"%d-%d-%d",&t.year,&t.month,&t.day)!=3)return {};}
 else if(std::strlen(date)!=8||std::sscanf(date,"%4d%2d%2d",&t.year,&t.month,&t.day)!=3)return {};
 if(std::strchr(time,':')){if(std::sscanf(time,"%d:%d:%d",&t.hour,&t.minute,&t.second)!=3)return {};}
 else if(std::strlen(time)!=6||std::sscanf(time,"%2d%2d%2d",&t.hour,&t.minute,&t.second)!=3)return {};
 return valid(t)?t:DateTime{};
}
inline bool filename(const DateTime&t,const char *track,unsigned sequence,char *out,size_t size){
 if(!valid(t)||sequence<1||sequence>99||size<13)return false;
 static const char *months[]={"GE","FE","MZ","AP","MG","GI","LG","AG","SE","OT","NO","DI"};
 char prefix[3]={'A','U',0};unsigned count=0;
 for(const char *p=track?track:"";*p&&count<2;++p){char c=*p;if(c>='a'&&c<='z')c-=32;if(c>='A'&&c<='Z')prefix[count++]=c;}
 if(count==1)prefix[1]='X';
 return std::snprintf(out,size,"%s%02d%s%02u.CSV",prefix,t.day,months[t.month-1],sequence)==12;
}
inline bool is_rc2_name(const char *name){
 if(!name||std::strlen(name)!=12||std::strcmp(name+8,".CSV"))return false;
 if(!((name[0]>='A'&&name[0]<='Z')||(name[0]>='0'&&name[0]<='9')) || !((name[1]>='A'&&name[1]<='Z')||(name[1]>='0'&&name[1]<='9')))return false;
 int day=(name[2]-'0')*10+name[3]-'0';
 if(name[2]<'0'||name[2]>'3'||name[3]<'0'||name[3]>'9'||day<1||day>31||name[6]<'0'||name[6]>'9'||name[7]<'0'||name[7]>'9'||(name[6]=='0'&&name[7]=='0'))return false;
 static const char *months[]={"GE","FE","MZ","AP","MG","GI","LG","AG","SE","OT","NO","DI"};
 for(auto month:months)if(name[4]==month[0]&&name[5]==month[1])return true;
 return false;
}
inline bool is_legacy_name(const char *name){
 if(!name||std::strlen(name)!=11||std::strcmp(name+7,".CSV"))return false;
 if(name[2]<'0'||name[2]>'9'||name[5]<'0'||name[5]>'9'||name[6]<'0'||name[6]>'9')return false;
 static const char *months[]={"GE","FE","MZ","AP","MG","GI","LG","AG","SE","OT","NO","DI"};
 for(auto month:months)if(name[3]==month[0]&&name[4]==month[1])return true;
 return false;
}
inline int64_t epoch(DateTime t){
 if(!valid(t))return 0;
 int64_t total=0;for(int y=1970;y<t.year;++y)total+=leap(y)?366:365;
 for(int m=1;m<t.month;++m)total+=days(t.year,m);
 return ((total+t.day-1)*24+t.hour)*3600+t.minute*60+t.second;
}
inline DateTime latest{};
inline DateTime utc_latest{};
inline uint32_t observed_ms{};
inline void observe_pvt(const uint8_t*p,uint32_t now){
 utc_latest={};if(p&&(p[11]&3)==3)utc_latest={int(p[4]|uint16_t(p[5])<<8),p[6],p[7],p[8],p[9],p[10]};
 latest=rome(utc_latest);observed_ms=now;
}
inline uint16_t fat_date(const DateTime&t){return valid(t)?uint16_t((t.year-1980)<<9|t.month<<5|t.day):0;}
inline uint16_t fat_time(const DateTime&t){return valid(t)?uint16_t(t.hour<<11|t.minute<<5|t.second/2):0;}

}
