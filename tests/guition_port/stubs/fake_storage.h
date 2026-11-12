#pragma once
#include <vector>
#include <map>
#include <cstdint>
namespace goats_sd_storage {
inline bool card_ready=true,opened=false,fail_write=false;
inline unsigned io_calls=0;
inline bool last_trace_ok=false;
inline std::vector<uint8_t> archive;
inline std::map<uint32_t,std::vector<uint8_t>> meta,sectors;
struct SavedTraceRow {uint32_t elapsed_ms,lap;double latitude,longitude;float speed_kmh,hdop;int satellites;};
inline std::vector<SavedTraceRow> rows;
inline bool ready(){return card_ready;}
inline bool writable(){return card_ready;}
inline bool live_open(){return opened;}
inline size_t live_points(){return rows.size();}
inline bool begin_live_session(const char*,const char*,const char*,const char*){++io_calls;opened=card_ready;rows.clear();return opened;}
inline void append_live_point(uint32_t ms,uint32_t lap,double a,double b,float s,float h,int n){++io_calls;if(fail_write){opened=false;return;}rows.push_back({ms,lap,a,b,s,h,n});}
inline bool finish_live_session(uint32_t){++io_calls;opened=false;return card_ready;}
inline void discard_live_session(){++io_calls;opened=false;rows.clear();}
inline bool write_archive(const std::vector<uint8_t>&v){++io_calls;if(!card_ready)return false;archive=v;return true;}
inline bool read_archive(std::vector<uint8_t>&v){if(!card_ready||archive.empty())return false;v=archive;return true;}
inline bool remove_archive(){archive.clear();return true;}
inline bool write_session_meta(uint32_t id,const std::vector<uint8_t>&v){++io_calls;if(!card_ready)return false;meta[id]=v;return true;}
inline bool read_session_meta(uint32_t id,std::vector<uint8_t>&v){if(!card_ready||!meta.count(id))return false;v=meta[id];return true;}
inline std::vector<uint32_t> list_session_meta_ids(){std::vector<uint32_t>v;for(auto &p:meta)v.push_back(p.first);return v;}
inline void remove_session_meta(uint32_t id){meta.erase(id);}
inline bool write_sector_file(uint32_t id,const std::vector<uint8_t>&v){++io_calls;if(!card_ready)return false;sectors[id]=v;return true;}
inline bool read_sector_file(uint32_t id,std::vector<uint8_t>&v){if(!card_ready||!sectors.count(id))return false;v=sectors[id];return true;}
inline void remove_sector_file(uint32_t id){sectors.erase(id);}
inline bool read_checkpoint(std::vector<uint8_t>&){return false;}
inline bool write_checkpoint(const std::vector<uint8_t>&){return card_ready;}
inline void remove_checkpoint(){}
inline void write_last_save_status(uint32_t,bool,bool,bool trace_ok){last_trace_ok=trace_ok;}
inline void remove_trace(uint32_t){}
inline void clear_session_files(){meta.clear();sectors.clear();archive.clear();}
template<class F>bool visit_saved_trace(uint32_t,F&&f,size_t){for(const auto&r:rows)f(r);return true;}
}
