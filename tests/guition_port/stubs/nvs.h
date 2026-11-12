#pragma once
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>
using nvs_handle_t=int;
constexpr int ESP_OK=0,ESP_FAIL=-1,ESP_ERR_NVS_NOT_FOUND=1,NVS_READWRITE=0;
inline bool fake_nvs_fail=false;
inline std::map<std::string,std::vector<uint8_t>> fake_nvs;
inline int nvs_open(const char*,int,nvs_handle_t*h){*h=1;return fake_nvs_fail?ESP_FAIL:ESP_OK;}
inline void nvs_close(nvs_handle_t){}
inline int nvs_get_blob(nvs_handle_t,const char*k,void*p,size_t*n){
  auto it=fake_nvs.find(k);if(it==fake_nvs.end())return ESP_ERR_NVS_NOT_FOUND;
  if(*n<it->second.size())return ESP_FAIL;*n=it->second.size();std::memcpy(p,it->second.data(),*n);return ESP_OK;
}
inline int nvs_set_blob(nvs_handle_t,const char*k,const void*p,size_t n){
  if(fake_nvs_fail)return ESP_FAIL;const auto*b=static_cast<const uint8_t*>(p);fake_nvs[k]={b,b+n};return ESP_OK;
}
inline int nvs_get_u32(nvs_handle_t h,const char*k,uint32_t*p){size_t n=4;return nvs_get_blob(h,k,p,&n);}
inline int nvs_set_u32(nvs_handle_t h,const char*k,uint32_t p){return nvs_set_blob(h,k,&p,4);}
inline int nvs_commit(nvs_handle_t){return fake_nvs_fail?ESP_FAIL:ESP_OK;}
inline int nvs_erase_key(nvs_handle_t,const char*k){return fake_nvs.erase(k)?ESP_OK:ESP_ERR_NVS_NOT_FOUND;}
