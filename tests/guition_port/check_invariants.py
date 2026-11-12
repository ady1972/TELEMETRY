from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
base=root/'firmware/guition-43'
a=base/'goats_guition_43_v1_0_20_rlcd26_usb'
b=base/'goats_guition_43_v1_0_22_rlcd26_usb'
assert (a/'goats_laptimer.h').read_bytes()==(b/'goats_laptimer.h').read_bytes()
for file in ['goats_ubx_m9n_v11.h','goats_gnss_assist_v1023.h','goats_usb_tracks_v1025.h','goats_usb_sd_msc.h']:
    old=(a/file).read_text(encoding='utf-8')
    new=(b/file).read_text(encoding='utf-8')
    if file=='goats_usb_tracks_v1025.h':
        new=re.sub(r'  // Read-only guard:.*?\n  void suspend_for_msc','  void suspend_for_msc',new,flags=re.S)
    assert old==new,file
def section(text,key):
    return re.search(r'^'+key+r':\n.*?(?=^[A-Za-z_]+:|\Z)',text,re.M|re.S)[0]
old=(base/'goats_guition_43_v1_0_20_rlcd26_usb.yaml').read_text(encoding='utf-8')
new=(base/'goats_guition_43_v1_0_22_rlcd26_usb.yaml').read_text(encoding='utf-8')
for key in ['uart','esp32','logger','display','globals']:assert section(old,key)==section(new,key),key
ui=section(old,'lvgl').replace('V1.0.20 RLCD26 USB','V1.0.22 RLCD26 USB').replace('Build: 05/11/2026 LAYOUT8','Build: 12/11/2026 RLCD26 USB')
assert ui==section(new,'lvgl'),'LVGL geometry/content changed'
assert not re.search(r'^(wifi|ota|web_server|api):',new,re.M)
text=(b/'goats_sessions.h').read_text(encoding='utf-8')
consumer=text[text.index('  void update('):text.index('  // RLCD-style bounded I/O')]
assert 'goats_sd_storage::' not in consumer and 'nvs_' not in consumer
original=(a/'goats_sessions.h').read_text(encoding='utf-8')
for begin,end in [('  bool parse_archive_(', '  static bool hydrate_trace_from_sd_'),('  static void serialize_session_(', '  template<typename T>')]:
    assert original[original.index(begin):original.index(end,original.index(begin))]==text[text.index(begin):text.index(end,text.index(begin))]
storage=(b/'goats_sd_storage.h').read_text(encoding='utf-8')
for token in ['elapsed_ms,lap,latitude,longitude,speed_kmh,hdop,satellites\\n','%lu,%lu,%.7f,%.7f,%.1f,%.2f,%d\\n']:
    assert token in storage and token in (a/'goats_sd_storage.h').read_text(encoding='utf-8')
print('PASS: timing engine/GNSS/UART/Racing/wire serializers/CSV unchanged; NAV consumer has no SD/NVS calls')
