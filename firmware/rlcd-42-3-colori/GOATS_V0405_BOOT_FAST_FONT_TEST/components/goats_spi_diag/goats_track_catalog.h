#pragma once
// GTC3: formato catalogo originale GOATS RLCD V1.7.18, solo LETTURA.
#include <cstdint>
#include <cstring>
#include <vector>
#include <string>
#include <cmath>
#include <nvs.h>
#include <nvs_flash.h>
struct GoatsSectorUsb {std::string name;double lat1{},lon1{},lat2{},lon2{};};
struct GoatsTrackUsb {std::string name;double start_lat{},start_lon{},finish_lat{},finish_lon{};float trigger_radius_m{20.f};uint8_t direction{0};std::vector<GoatsSectorUsb> sectors;};
namespace goats_tracks {
inline std::vector<GoatsTrackUsb> tracks;
inline uint32_t crc32(const uint8_t *data,size_t n){uint32_t c=0xffffffffu;for(size_t i=0;i<n;i++){c^=data[i];for(int j=0;j<8;j++)c=(c>>1)^(0xedb88320u & (0u-(c&1u)));}return c^0xffffffffu;}
template<typename T> bool read(const std::vector<uint8_t>&d,size_t&at,T &v){if(at+sizeof(T)>d.size())return false;memcpy(&v,d.data()+at,sizeof(T));at+=sizeof(T);return true;}
inline bool str(const std::vector<uint8_t>&d,size_t&at,std::string&v){uint8_t n=0;if(!read(d,at,n)||at+n>d.size())return false;v.assign((const char*)d.data()+at,n);at+=n;return true;}
inline bool parse(const std::vector<uint8_t>&d){if(d.size()<8||memcmp(d.data(),"GTC3",4))return false;size_t at=4;uint16_t ver=0,n=0;if(!read(d,at,ver)||!read(d,at,n)||ver!=1||n>50)return false;std::vector<GoatsTrackUsb> temp;for(unsigned i=0;i<n;i++){GoatsTrackUsb t;uint8_t cnt=0;if(!str(d,at,t.name)||!read(d,at,t.start_lat)||!read(d,at,t.start_lon)||!read(d,at,t.finish_lat)||!read(d,at,t.finish_lon)||!read(d,at,t.trigger_radius_m)||!read(d,at,t.direction)||!read(d,at,cnt)||cnt>12||t.name.empty()||!std::isfinite(t.start_lat)||!std::isfinite(t.finish_lat)||std::abs(t.start_lat)>90||std::abs(t.finish_lat)>90||std::abs(t.start_lon)>180||std::abs(t.finish_lon)>180)return false;for(unsigned j=0;j<cnt;j++){GoatsSectorUsb v;if(!str(d,at,v.name)||!read(d,at,v.lat1)||!read(d,at,v.lon1)||!read(d,at,v.lat2)||!read(d,at,v.lon2))return false;t.sectors.push_back(v);}temp.push_back(std::move(t));}if(at!=d.size())return false;tracks=std::move(temp);return true;}
inline bool load(){tracks.clear();nvs_handle_t h; if(nvs_open("goats_tracks",NVS_READONLY,&h)!=ESP_OK)return false;size_t sz=0;esp_err_t e=nvs_get_blob(h,"catalog",nullptr,&sz);if(e!=ESP_OK||sz<8||sz>60000){nvs_close(h);return false;}std::vector<uint8_t>d(sz);e=nvs_get_blob(h,"catalog",d.data(),&sz);uint32_t check=0;bool has_crc=nvs_get_u32(h,"catalog_crc",&check)==ESP_OK;nvs_close(h);if(e!=ESP_OK||(has_crc&&crc32(d.data(),d.size())!=check))return false;return parse(d);}
inline const GoatsTrackUsb* get(int i){return (i>=0&&(size_t)i<tracks.size())?&tracks[i]:nullptr;}
inline float dist_m(double a,double b,double c,double d){const double rad=0.017453292519943295;double dy=(a-c)*111195.0;double dx=(b-d)*111195.0*std::cos(a*rad);return std::sqrt(dx*dx+dy*dy);}
inline int nearest(double lat,double lon,float threshold_m=350.f){int best=-1;float distance=threshold_m;for(size_t i=0;i<tracks.size();i++){auto &t=tracks[i];float d=dist_m(lat,lon,(t.start_lat+t.finish_lat)/2,(t.start_lon+t.finish_lon)/2);if(d<distance){distance=d;best=(int)i;}}return best;}
}
