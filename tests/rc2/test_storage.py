"""Compile and execute real RC2 naming/finalization functions against an in-memory FAT adapter."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
def function(source,name):
    start=source.rfind('static inline ',0,source.index(name+'('))
    opening=source.index('{',source.index(name+'(',start));depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]
preamble=r'''
#include <map>
#include <string>
#include <vector>
#include <cstring>
#include <strings.h>
#include <cstdio>
#include <cassert>
#include "goats_recording_clock.h"
using FRESULT=int;using UINT=unsigned;using TCHAR=char;
constexpr int FR_OK=0,FR_NO_FILE=1,FR_NO_PATH=2,FR_DISK_ERR=3,FR_EXIST=4,FR_INVALID_OBJECT=5,FR_INT_ERR=6;
constexpr int FA_READ=1,FA_WRITE=2,FA_CREATE_ALWAYS=4;
struct Data {std::string content;uint16_t date=0,time=0;};
std::map<std::string,Data> files;bool fail_stat=false,fail_stamp=false;
struct FIL{std::string name;};struct FILINFO{unsigned fsize=0;uint16_t fdate=0,ftime=0;};
int f_stat(const char*p,FILINFO*i){if(fail_stat)return FR_DISK_ERR;auto it=files.find(p);if(it==files.end())return FR_NO_FILE;i->fsize=it->second.content.size();return FR_OK;}
int f_open(FIL*f,const char*p,int flags){f->name=p;if(flags&FA_CREATE_ALWAYS)files[p]={};return files.count(p)?FR_OK:FR_NO_FILE;}
int f_write(FIL*f,const void*p,unsigned n,unsigned*w){files[f->name].content.append((const char*)p,n);*w=n;return FR_OK;}
int f_read(FIL*f,void*p,unsigned n,unsigned*w){auto&c=files[f->name].content;*w=std::min<unsigned>(n,c.size());memcpy(p,c.data(),*w);return FR_OK;}
int f_sync(FIL*){return FR_OK;}int f_close(FIL*){return FR_OK;}
int f_unlink(const char*p){return files.erase(p)?FR_OK:FR_NO_FILE;}
int f_rename(const char*a,const char*b){if(files.count(b))return FR_EXIST;if(!files.count(a))return FR_NO_FILE;files[b]=files[a];files.erase(a);return FR_OK;}
int f_utime(const char*p,const FILINFO*i){if(fail_stamp)return FR_DISK_ERR;files[p].date=i->fdate;files[p].time=i->ftime;return FR_OK;}
namespace goats_diag_v1021 {enum class SdKind{FINALIZE,METADATA};struct SdScope{SdScope(SdKind){}};}
char g_live_date_file[16]="20261106",g_live_time_file[12]="130205",g_live_track_file[40]="TARANTO";
bool g_live_is_open=true;FIL g_live;int g_last=0;
void set_fatfs_error_(const char*,int e){g_last=e;}void set_ok_(const char*){}
'''
main=r'''
int main(){
 char path[64];
 assert(progressive_trace_name_(path,sizeof(path)));assert(std::string(path)=="0:/GOATS/TA06NO01.CSV");
 files[path].content="old";
 assert(progressive_trace_name_(path,sizeof(path)));assert(std::string(path)=="0:/GOATS/TA06NO02.CSV");
 strcpy(g_live_date_file,"20261107");assert(progressive_trace_name_(path,sizeof(path)));assert(std::string(path)=="0:/GOATS/TA07NO01.CSV");
 strcpy(g_live_date_file,"20261106");files["0:/GOATS/LIVE.CSV"].content="recording";
 assert(finish_live_session(7));assert(files["0:/GOATS/TA06NO01.CSV"].content=="old");
 assert(files["0:/GOATS/TA06NO02.CSV"].content=="recording");
 const auto date=goats_clock::parse("2026-11-06","13:02:05");
 assert(files["0:/GOATS/TA06NO02.CSV"].date==goats_clock::fat_date(date));
 assert(files["0:/GOATS/TA06NO02.CSV"].time==goats_clock::fat_time(date));
 assert(trace_map_path_(7,path,sizeof(path)));assert(std::string(path)=="0:/GOATS/TA06NO02.CSV");
 for(unsigned i=1;i<=99;i++){char n[16];goats_clock::filename(date,"TA",i,n,sizeof(n));files[std::string("0:/GOATS/")+n].content="keep";}
 g_live_is_open=true;files["0:/GOATS/LIVE.CSV"].content="must survive";
 assert(!finish_live_session(8));assert(files["0:/GOATS/LIVE.CSV"].content=="must survive");
 fail_stat=true;assert(!progressive_trace_name_(path,sizeof(path)));fail_stat=false;
 files.clear();strcpy(g_live_date_file,"DATA");strcpy(g_live_time_file,"ORA");
 g_live_is_open=true;files["0:/GOATS/LIVE.CSV"].content="unknown date";
 assert(finish_live_session(42));assert(files.count("0:/GOATS/S000042.CSV"));
 assert(files["0:/GOATS/S000042.CSV"].date==0);
 files["0:/GOATS/RECOV.CSV"].content="previous recovery";
 g_live_is_open=true;files["0:/GOATS/LIVE.CSV"].content="NVS id missing";
 assert(finish_live_session(0));assert(files["0:/GOATS/RECOV.CSV"].content=="previous recovery");
 assert(files["0:/GOATS/R000000.CSV"].content=="NVS id missing");
 g_live_is_open=true;files["0:/GOATS/LIVE.CSV"].content="second recovery";
 assert(finish_live_session(0));assert(files["0:/GOATS/R000001.CSV"].content=="second recovery");
}
'''
for folder in ['firmware/rlcd-42/GOATS_RLCD_RC2','firmware/guition-43/goats_guition_43_rc2']:
    source=(root/folder/'goats_sd_storage.h').read_text()
    text=preamble+'\n'.join(function(source,name) for name in ['progressive_trace_name_','stamp_trace_','trace_map_path_','save_trace_map_','finish_live_session'])+main
    with tempfile.TemporaryDirectory() as tmp:
        cpp=Path(tmp)/'test.cpp';cpp.write_text(text)
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(root/folder),str(cpp),'-o',tmp+'/test'],check=True)
        subprocess.run([tmp+'/test'],check=True)
    print('PASS: FAT naming, day reset, collisions, timestamps, ID map, full-day preservation, unknown date:',folder)
