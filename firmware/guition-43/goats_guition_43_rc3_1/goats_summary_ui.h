#pragma once
#include <array>
#include "esphome/components/lvgl/lvgl_esphome.h"
#include "goats_sessions.h"
namespace goats_summary_ui {
inline void render(lv_obj_t *parent,const GoatsSessionRecord *session,const lv_font_t *font){
 // All cells of a row share the same background; BEST remains visible when scrolling.
 static std::array<lv_obj_t*,80> rows{};
 static std::array<std::array<lv_obj_t*,5>,80> labels{};
 static uint32_t last_session=0;
 const uint32_t id=session?session->session_id:0;
 if(id!=last_session){lv_obj_scroll_to_y(parent,0,LV_ANIM_OFF);last_session=id;}
 const size_t count=session?std::min<size_t>(80,session->laps.size()):0;
 uint32_t best=0;
 if(session)for(const auto &lap:session->laps)
   if(lap.lap_time_ms && (!best||lap.lap_time_ms<best))best=lap.lap_time_ms;
 for(size_t i=0;i<80;++i){
   if(i>=count){if(rows[i])lv_obj_add_flag(rows[i],LV_OBJ_FLAG_HIDDEN);continue;}
   if(!rows[i]){
     rows[i]=lv_obj_create(parent);
     lv_obj_remove_flag(rows[i],LV_OBJ_FLAG_SCROLLABLE);
     lv_obj_set_pos(rows[i],0,i*30);lv_obj_set_size(rows[i],450,29);
     lv_obj_set_style_pad_all(rows[i],0,0);lv_obj_set_style_border_width(rows[i],0,0);
     lv_obj_set_style_radius(rows[i],0,0);
     constexpr int x[]={0,48,181,278,376};constexpr int width[]={46,131,95,96,72};
     for(size_t c=0;c<5;++c){
       labels[i][c]=lv_label_create(rows[i]);
       lv_obj_set_pos(labels[i][c],x[c],3);lv_obj_set_width(labels[i][c],width[c]);
       lv_obj_set_style_text_font(labels[i][c],font,0);
       lv_obj_set_style_text_align(labels[i][c],LV_TEXT_ALIGN_CENTER,0);
     }
   }
   lv_obj_remove_flag(rows[i],LV_OBJ_FLAG_HIDDEN);
   const auto &lap=session->laps[i];const bool is_best=lap.lap_time_ms>0 && lap.lap_time_ms==best;
   lv_obj_set_style_bg_opa(rows[i],LV_OPA_COVER,0);
   lv_obj_set_style_bg_color(rows[i],lv_color_hex(is_best?0x00D084:0x10141A),0);
   for(auto *label:labels[i])lv_obj_set_style_text_color(label,lv_color_hex(is_best?0x000000:0xFFFFFF),0);
   char text[32];snprintf(text,sizeof(text),"%u",unsigned(lap.number));lv_label_set_text(labels[i][0],text);
   snprintf(text,sizeof(text),"%lu:%02lu.%03lu",(unsigned long)(lap.lap_time_ms/60000),
     (unsigned long)((lap.lap_time_ms/1000)%60),(unsigned long)(lap.lap_time_ms%1000));lv_label_set_text(labels[i][1],text);
   snprintf(text,sizeof(text),"%.1f",(double)lap.max_speed_kmh);lv_label_set_text(labels[i][2],text);
   snprintf(text,sizeof(text),"%.1f",(double)lap.average_speed_kmh);lv_label_set_text(labels[i][3],text);
   lv_label_set_text(labels[i][4],is_best?"BEST":"");
 }
}
}
