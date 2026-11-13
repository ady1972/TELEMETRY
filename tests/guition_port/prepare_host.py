from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=True)
base=root/'firmware/guition-43'
for new,name in [(True,'sessions_host.h'),(False,'legacy_sessions_host.h')]:
    folder=(sys.argv[2] if len(sys.argv)>2 else 'goats_guition_43_v1_0_22_rlcd26_usb') if new else 'goats_guition_43_v1_0_20_rlcd26_usb'
    text=(base/folder/'goats_sessions.h').read_text(encoding='utf-8')
    text=text.replace('#include "goats_sd_storage.h"','#include "fake_storage.h"')
    if not new:
        text=text[:text.index('static GoatsSessionManager GOATS_SESSIONS;')]
        for original in ['GoatsSessionManager','GoatsSessionRecord','GoatsLapRecord','GoatsTracePoint']:
            text=text.replace(original,'Legacy'+original)
    (out/name).write_text(text,encoding='utf-8')
print(out)
usb=(base/'goats_guition_43_v1_0_22_rlcd26_usb/goats_usb_tracks_v1025.h').read_text(encoding='utf-8')
adapter=usb[usb.index('// GUI adapter only:'):usb.index('inline int goats_track_dropdown_to_physical')]
(out/'dropdown_host.h').write_text(adapter,encoding='utf-8')
