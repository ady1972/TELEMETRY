"""Exercise the actual summary renderer against a small LVGL state adapter."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
folder=root/'firmware/guition-43/goats_guition_43_rc2'
sessions=(folder/'goats_sessions.h').read_text()
records=sessions[sessions.index('struct GoatsTracePoint'):sessions.index('class GoatsSessionManager')]
renderer='\n'.join(line for line in (folder/'goats_summary_ui.h').read_text().splitlines() if not line.startswith('#'))
adapter=r'''
#include <array>
#include <vector>
#include <string>
#include <cstdint>
#include <cstdio>
#include <algorithm>
#include <cassert>
#include <memory>
using lv_font_t=int;
struct lv_obj_t {std::vector<lv_obj_t*> children;std::string text;unsigned bg=0,fg=0;bool hidden=false;};
constexpr int LV_OBJ_FLAG_SCROLLABLE=1,LV_OBJ_FLAG_HIDDEN=2,LV_ANIM_OFF=0,LV_OPA_COVER=255,LV_TEXT_ALIGN_CENTER=1;
std::vector<std::unique_ptr<lv_obj_t>> nodes;
lv_obj_t *lv_obj_create(lv_obj_t *parent){nodes.push_back(std::make_unique<lv_obj_t>());auto *node=nodes.back().get();parent->children.push_back(node);return node;}
lv_obj_t *lv_label_create(lv_obj_t *parent){return lv_obj_create(parent);}
void lv_obj_add_flag(lv_obj_t *o,int f){if(f==LV_OBJ_FLAG_HIDDEN)o->hidden=true;}
void lv_obj_remove_flag(lv_obj_t *o,int f){if(f==LV_OBJ_FLAG_HIDDEN)o->hidden=false;}
unsigned lv_color_hex(unsigned c){return c;}
void lv_obj_set_style_bg_color(lv_obj_t *o,unsigned c,int){o->bg=c;}
void lv_obj_set_style_text_color(lv_obj_t *o,unsigned c,int){o->fg=c;}
void lv_label_set_text(lv_obj_t *o,const char *text){o->text=text;}
void lv_obj_set_pos(lv_obj_t*,int,int){}
void lv_obj_set_size(lv_obj_t*,int,int){}
void lv_obj_set_width(lv_obj_t*,int){}
void lv_obj_set_style_pad_all(lv_obj_t*,int,int){}
void lv_obj_set_style_border_width(lv_obj_t*,int,int){}
void lv_obj_set_style_radius(lv_obj_t*,int,int){}
void lv_obj_set_style_text_font(lv_obj_t*,const lv_font_t*,int){}
void lv_obj_set_style_text_align(lv_obj_t*,int,int){}
void lv_obj_set_style_bg_opa(lv_obj_t*,int,int){}
void lv_obj_scroll_to_y(lv_obj_t*,int,int){}
'''
main=r'''
int main(){
 lv_obj_t parent;lv_font_t font=0;GoatsSessionRecord session;session.session_id=1;
 for(unsigned i=0;i<3;++i){GoatsLapRecord lap;lap.number=i+1;lap.lap_time_ms=i?50000:60000;lap.max_speed_kmh=80+i*10;lap.average_speed_kmh=50+i*5;lap.sectors_ms={20000,30000};session.laps.push_back(lap);}
 goats_summary_ui::render(&parent,&session,&font);
 assert(parent.children.size()==3);
 assert(parent.children[0]->bg==0x10141A);
 for(unsigned i=1;i<=2;++i){assert(parent.children[i]->bg==0x00D084);assert(parent.children[i]->children[4]->text=="BEST");}
 const auto &cells=parent.children[1]->children;
 assert(cells[0]->text=="2" && cells[1]->text=="0:50.000");
 assert(cells[2]->text=="90.0" && cells[3]->text=="55.0");
 session.session_id=2;session.laps.resize(2);session.laps[0].lap_time_ms=40000;
 goats_summary_ui::render(&parent,&session,&font);
 assert(parent.children[0]->bg==0x00D084 && parent.children[1]->bg==0x10141A);
 assert(parent.children[1]->children[4]->text.empty());assert(parent.children[2]->hidden);
 session.laps[0].lap_time_ms=0;session.laps[1].lap_time_ms=0;
 goats_summary_ui::render(&parent,&session,&font);
 assert(parent.children[0]->bg==0x10141A && parent.children[1]->bg==0x10141A);
 goats_summary_ui::render(&parent,nullptr,&font);
 for(auto *row:parent.children)assert(row->hidden);
}
'''
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'summary.cpp';cpp.write_text(adapter+records+renderer+main)
    exe=Path(tmp)/'summary'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS Guition summary: per-lap values, tied BEST highlight, session change, empty/zero laps')
