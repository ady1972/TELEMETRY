FILES={
'esp_heap_caps.h':r'''#pragma once
#include <cstddef>
#define MALLOC_CAP_8BIT 1
inline size_t test_heap=512*1024;
inline size_t heap_caps_get_free_size(int){return test_heap;}
inline size_t heap_caps_get_largest_free_block(int){return test_heap;}
''',
'esp_partition.h':r'''#pragma once
#include <cstdint>
#include <cstring>
#include <vector>
#include <cassert>
#include "nvs.h"
#define ESP_PARTITION_TYPE_DATA 1
#define ESP_PARTITION_SUBTYPE_ANY 0xff
struct esp_partition_t{size_t size=2*1024*1024;};
inline esp_partition_t test_partition;
inline std::vector<uint8_t> flash_bytes(2*1024*1024,255);
inline unsigned flash_reads=0,flash_writes=0,flash_erases=0;
inline bool inside_pvt=false,write_failure=false;
inline const esp_partition_t*esp_partition_find_first(int,int,const char *label){assert(!strcmp(label,"goatsfs"));return &test_partition;}
inline int esp_partition_read(const esp_partition_t*,size_t at,void *out,size_t n){assert(!inside_pvt&&at+n<=test_partition.size);++flash_reads;memcpy(out,flash_bytes.data()+at,n);return ESP_OK;}
inline int esp_partition_write(const esp_partition_t*,size_t at,const void*in,size_t n){assert(!inside_pvt&&at%4==0&&n%4==0&&at+n<=test_partition.size&&n<=256);++flash_writes;if(write_failure)return 99;auto*p=(const uint8_t*)in;for(size_t i=0;i<n;i++){assert((flash_bytes[at+i]&p[i])==p[i]);flash_bytes[at+i]=p[i];}return ESP_OK;}
inline int esp_partition_erase_range(const esp_partition_t*,size_t at,size_t n){assert(!inside_pvt&&at%4096==0&&n==4096&&at+n<=test_partition.size);++flash_erases;memset(flash_bytes.data()+at,255,n);return ESP_OK;}
''',
'nvs.h':r'''#pragma once
#include <cstdint>
#include <cstring>
#include <vector>
#include <map>
#include <string>
#include <cassert>
#define ESP_OK 0
#define ESP_FAIL 99
#define ESP_ERR_INVALID_STATE 0x103
#define ESP_ERR_NVS_NOT_FOUND 1
#define NVS_READONLY 0
#define NVS_READWRITE 1
using esp_err_t=int;using nvs_handle_t=int;
extern bool inside_pvt;
inline unsigned nvs_calls=0,nvs_writes=0;
inline int next_handle=0;
inline bool nvs_failure=false;
inline std::map<std::string,std::vector<uint8_t>> nvs_values;
inline std::map<int,std::string> nvs_names;
inline std::map<int,std::map<std::string,std::vector<uint8_t>>> nvs_pending;
inline int nvs_open(const char *ns,int,nvs_handle_t*out){assert(!inside_pvt);++nvs_calls;*out=++next_handle;nvs_names[*out]=ns;return 0;}
inline int nvs_get_blob(nvs_handle_t h,const char*key,void*out,size_t*n){assert(!inside_pvt);++nvs_calls;auto it=nvs_values.find(nvs_names[h]+"/"+key);if(it==nvs_values.end())return 1;if(!out){*n=it->second.size();return 0;}if(*n<it->second.size())return 2;*n=it->second.size();memcpy(out,it->second.data(),*n);return 0;}
inline int nvs_get_u32(nvs_handle_t h,const char*k,uint32_t*out){size_t n=4;return nvs_get_blob(h,k,out,&n);}
inline int nvs_set_blob(nvs_handle_t h,const char*k,const void*p,size_t n){assert(!inside_pvt);++nvs_calls;++nvs_writes;nvs_pending[h][nvs_names[h]+"/"+k]=std::vector<uint8_t>((const uint8_t*)p,(const uint8_t*)p+n);return 0;}
inline int nvs_set_u32(nvs_handle_t h,const char*k,uint32_t v){return nvs_set_blob(h,k,&v,4);}
inline int nvs_commit(nvs_handle_t h){assert(!inside_pvt);++nvs_calls;if(nvs_failure)return 99;for(auto &item:nvs_pending[h])nvs_values[item.first]=item.second;return 0;}
inline void nvs_close(nvs_handle_t h){assert(!inside_pvt);++nvs_calls;nvs_pending.erase(h);nvs_names.erase(h);}
''',
'driver/usb_serial_jtag.h':r'''#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
#include <deque>
#include <cassert>
#include <algorithm>
#define pdMS_TO_TICKS(x) (x)
inline unsigned usb_installs=0,usb_reads=0,usb_writes=0;
inline bool usb_connected=true;
inline unsigned usb_limit=512;
inline std::deque<uint8_t>usb_rx;
inline std::vector<uint8_t>usb_tx;
struct usb_serial_jtag_driver_config_t {size_t rx_buffer_size,tx_buffer_size;};
inline int usb_serial_jtag_driver_install(const usb_serial_jtag_driver_config_t*c){assert(c->rx_buffer_size==8192&&c->tx_buffer_size==4096);++usb_installs;return 0;}
inline int usb_serial_jtag_write_bytes(const void*p,size_t n,unsigned wait){assert(wait==0);++usb_writes;if(!usb_connected)return 0;n=std::min<size_t>(n,usb_limit);auto*b=(const uint8_t*)p;usb_tx.insert(usb_tx.end(),b,b+n);return n;}
inline int usb_serial_jtag_read_bytes(void*p,size_t n,unsigned wait){assert(wait==0);++usb_reads;size_t i=0;auto*b=(uint8_t*)p;while(i<n&&!usb_rx.empty()){b[i++]=usb_rx.front();usb_rx.pop_front();}return i;}
'''
}
