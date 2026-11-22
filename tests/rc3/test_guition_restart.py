"""Exercise two saves on the same Guition circuit with no restart."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "firmware/guition-43/goats_guition_43_rc3"
YAML = G.with_suffix(".yaml").read_text()
DISMISS = "- script.execute: dismiss_session_summary"
assert DISMISS in YAML.split("id: session_summary_panel", 1)[1].split("# Avviso NEW BEST", 1)[0]
assert DISMISS in YAML.split("# V11.0.2.40 - timeout riepilogo fine sessione.", 1)[1].split(
    "# V7.1 - Timer CHECK BENZINA.", 1)[0]
BODY = YAML.split("  - id: dismiss_session_summary\n", 1)[1].split(
    "      - lvgl.widget.hide: session_summary_panel", 1)[0].split("      - lambda: |-\n")[1]

with tempfile.TemporaryDirectory() as temp:
    tmp = Path(temp)
    (tmp / "goats_pipeline.h").write_bytes((G / "goats_pipeline.h").read_bytes())
    sessions = (G / "goats_sessions.h").read_text().replace(
        '#include "goats_sd_storage.h"', '#include "fake_storage.h"'
    )
    (tmp / "goats_sessions.h").write_text(sessions)
    (tmp / "dismiss.inc").write_text(BODY)
    source = tmp / "test.cpp"
    source.write_text(r'''
#include <cassert>
#include <cstdint>
#include "goats_track_types.h"

int64_t fake_us = 0;
unsigned log_lines = 0;
uint32_t millis() { return static_cast<uint32_t>(fake_us / 1000); }
void taskYIELD() {}
uint32_t goats_track_revision() { return 1; }

#include "goats_laptimer.h"
#include "goats_pipeline.h"

static bool session_summary_visible = true;
static uint32_t session_summary_hide_at_ms = 15000;
static void dismiss_summary() {
#define id(name) name
#include "dismiss.inc"
#undef id
}

int main() {
  GoatsTrackUsb track;
  track.name = "Same circuit";
  track.start_lat = track.finish_lat = 45.0;
  track.start_lon = 9.0;
  track.finish_lon = 9.001;
  track.trigger_radius_m = 20;

  GOATS_SESSIONS.setup();
  auto point = [&](double latitude, uint32_t time) {
    fake_us = int64_t(time) * 1000;
    goats_nav_queue::push(true, latitude, 9.0005, 40, time, time, 0.8f, 12);
    goats_pipeline::drain(&track, "", "");
    GOATS_SESSIONS.storage_tick();
  };
  auto stint = [&](uint32_t start) {
    point(44.9997, start);
    assert(!GOATS_SESSIONS.active());
    point(45.0003, start + 40);
    assert(GOATS_SESSIONS.active());
    assert(goats_laptimer_running());
    point(45.0004, start + 80);
    point(44.9997, start + 10040);
    assert(goats_laptimer_last_lap_ms() == 10000);
    GOATS_SESSIONS.finish_manual(start + 10100);
    assert(GOATS_SESSIONS.last_save_ok());
    assert(!GOATS_SESSIONS.active());
    assert(!GOATS_SESSIONS.accepts_samples());
  };

  stint(1000);
  assert(GOATS_SESSIONS.count() == 1);
  const uint32_t first_id = GOATS_SESSIONS.display_session(0)->session_id;
  dismiss_summary();
  assert(!session_summary_visible && session_summary_hide_at_ms == 0);
  stint(25000);
  assert(GOATS_SESSIONS.count() == 2);
  const auto* first = GOATS_SESSIONS.display_session(1);
  const auto* second = GOATS_SESSIONS.display_session(0);
  assert(first->session_id == first_id && second->session_id != first_id);
  assert(first->laps.size() == 1 && second->laps.size() == 1);
  assert(first->best_lap_ms == 10000 && second->best_lap_ms == 10000);
}
''')
    executable = tmp / "test"
    subprocess.run([
        "g++", "-std=c++17", "-Wno-misleading-indentation", "-I", tmp, "-I", G,
        "-I", ROOT / "tests/guition_port/stubs", "-I", ROOT / "firmware/rlcd-42/GOATS_RLCD_RC3",
        source, "-o", executable,
    ], check=True)
    subprocess.run([executable], check=True)

print("PASS Guition RC3: save, automatic summary dismissal, same-track finish, second timed lap and save")
