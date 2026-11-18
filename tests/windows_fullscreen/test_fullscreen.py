"""Exercise fullscreen controls and the rendered map with synthetic telemetry."""
import importlib.util
import itertools
import math
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[2]
VERSION = os.environ.get('GOATS_WINDOWS_VERSION', '5.4.15.5')
APP = ROOT / ('windows/v'+VERSION+'-burst4')
sys.path.insert(0, str(APP))
spec = importlib.util.spec_from_file_location('fullscreen_manager', APP / ('goats_rt_manager_v'+VERSION.replace('.', '_')+'.py'))
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


def render_map_html(show_brakes=False, empty=False):
    series, events = {}, []
    if not empty:
        for lap in (1, 2):
            rows = []
            for i in range(301):
                angle = 2 * math.pi * i / 300
                rows.append(dict(latitude=45 + .001 * math.cos(angle),
                                 longitude=9 + .001 * math.sin(angle),
                                 speed_kmh=60 + 20 * math.cos(2 * angle),
                                 elapsed_ms=(lap - 1) * 12000 + i * 40))
            series[f'Giro {lap}'] = rows
            for zone, index in ((1, 65), (2, 210)):
                row = rows[index]
                events.append(dict(lap=lap, zone=zone, latitude=row['latitude'],
                                   longitude=row['longitude'], start_ms=row['elapsed_ms'],
                                   end_ms=row['elapsed_ms'] + 600, start_speed=75.,
                                   min_speed=42., norm_m=index * 2., delta_m=lap - 1.,
                                   duration_s=.6, corner_entry_speed=70., corner_min_speed=42.,
                                   corner_exit_speed=65., reference_lap=1))
    captured = {}
    host = SimpleNamespace(
        _analysis_track_data=lambda: {}, _analysis_focus_lap=None,
        _analysis_lap_stats_by_no={}, _analysis_show_brakes=show_brakes,
        _analysis_brake_table_mode='both',
        _analysis_build_brake_analysis=lambda selected: (events, []),
        _analysis_color_for_series=lambda name, index: ('#00d084', '#ff8040')[index],
        _analysis_color_for_lap=lambda lap: ('#00d084', '#ff8040')[lap - 1],
        map=SimpleNamespace(setHtml=lambda html, url: captured.update(html=html)),
    )
    manager.Main.render_map(host, series)
    return captured['html']


class NativeControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = manager.QApplication.instance() or manager.QApplication([])

    def setUp(self):
        self.host = manager.QMainWindow()
        self.host._last_map_html = render_map_html()
        self.host._analysis_brake_table_mode = 'both'
        self.host.replay_speed_combo = manager.QComboBox()
        self.host.replay_speed_combo.addItem('1x', 1.)
        self.addCleanup(self.host.close)

    def open_dialog(self, inspect):
        class FakeWebView(manager.QWidget):
            loadFinished = manager.Signal(bool)

            def __init__(self, parent=None):
                super().__init__(parent)
                self.scripts = []

            def setHtml(self, html, url):
                pass

            def page(self):
                return self

            def runJavaScript(self, script):
                self.scripts.append(script)

        with patch.object(manager, 'QWebEngineView', FakeWebView), \
             patch.object(manager.QTimer, 'singleShot', side_effect=lambda *args: None), \
             patch.object(manager.QDialog, 'exec', new=inspect):
            manager.Main._analysis_open_fullscreen_map(self.host)

    def test_toggles_late_load_and_reopen(self):
        def inspect(dialog):
            checks = [dialog.findChild(manager.QCheckBox, name) for name in (
                'fullscreenBrakingCheck', 'fullscreenCornerSpeedCheck', 'fullscreenSpeedGraphCheck')]
            self.assertTrue(all(check is not None for check in checks))
            self.assertTrue(all(check.isChecked() for check in checks))
            checks[0].setChecked(False)
            checks[2].setChecked(False)
            view = dialog.findChildren(manager.QWidget)
            view = next(child for child in view if hasattr(child, 'scripts'))
            # Late web loading must apply the current choices, not initial defaults.
            view.loadFinished.emit(True)
            self.assertIn('goatsSetFullscreenOverlays(false,true,false)', view.scripts[-1])
            self.assertEqual(self.host._fullscreen_overlay_visibility, (False, True, False))
            dialog.close()
            return 0
        self.open_dialog(inspect)

        def reopen(dialog):
            for name, checked in (('fullscreenBrakingCheck', False),
                                  ('fullscreenCornerSpeedCheck', True),
                                  ('fullscreenSpeedGraphCheck', False)):
                self.assertEqual(dialog.findChild(manager.QCheckBox, name).isChecked(), checked)
            dialog.close()
            return 0
        self.open_dialog(reopen)

    def test_initial_mode_follows_analysis_selection(self):
        for mode, expected in (('brake', (True, False)), ('speed', (False, True))):
            with self.subTest(mode=mode):
                self.host._analysis_brake_table_mode = mode
                self.host._fullscreen_overlay_visibility = None

                def inspect(dialog):
                    actual = tuple(dialog.findChild(manager.QCheckBox, name).isChecked() for name in (
                        'fullscreenBrakingCheck', 'fullscreenCornerSpeedCheck'))
                    self.assertEqual(actual, expected)
                    dialog.close()
                    return 0
                self.open_dialog(inspect)


class RenderedMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.assets = {}
        for name in ('leaflet.js', 'leaflet.css'):
            cached = os.environ.get('GOATS_LEAFLET_DIR')
            if cached:
                cls.assets[name] = (Path(cached) / name).read_bytes()
            else:
                with urllib.request.urlopen('https://unpkg.com/leaflet@1.9.4/dist/' + name, timeout=30) as response:
                    cls.assets[name] = response.read()
        cls.playwright = sync_playwright().start()
        executable = os.environ.get('GOATS_CHROMIUM') or shutil.which('chromium')
        cls.browser = cls.playwright.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport=dict(width=1400, height=850))
        self.addCleanup(self.page.close)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

        def route_request(route):
            name = route.request.url.rsplit('/', 1)[-1]
            if name in self.assets:
                route.fulfill(body=self.assets[name], content_type='application/javascript' if name.endswith('.js') else 'text/css')
            else:
                route.abort()
        self.page.route('**/*', route_request)
        self.page.set_content(render_map_html(), wait_until='load')
        self.page.wait_for_function("typeof window.goatsSetFullscreenOverlays === 'function'")

    def test_all_eight_visibility_combinations_preserve_map(self):
        self.page.evaluate('window.goatsSetFullscreenMode(true); window.originalMap=map; window.originalZoom=map.getZoom(); window.originalCenter=map.getCenter();')
        for braking, corner, graph in itertools.product((False, True), repeat=3):
            with self.subTest(braking=braking, corner=corner, graph=graph):
                self.page.evaluate('(flags) => window.goatsSetFullscreenOverlays(...flags)', [braking, corner, graph])
                self.page.wait_for_timeout(180)
                self.assertEqual(self.page.locator('.brake-zone-table').count(), 2 if braking or corner else 0)
                self.assertEqual(self.page.locator('#fsSpeedPanel').is_visible(), graph)
                self.assertEqual(self.page.locator('#legend').count(), 0)
                self.assertFalse(self.page.locator('#brakeModeControl').is_visible())
                markers_visible = self.page.evaluate('brakeMarkers.every(marker => map.hasLayer(marker))')
                self.assertEqual(markers_visible, braking or corner)
                self.assertTrue(self.page.evaluate('map===window.originalMap && map.getZoom()===window.originalZoom && map.getCenter().equals(window.originalCenter)'))
                if braking or corner:
                    headings = self.page.locator('.brake-zone-table').first.locator('th').all_text_contents()
                    self.assertEqual('Δ PUNTO' in headings, braking)
                    self.assertEqual('V IN' in headings, corner)
                if graph:
                    self.assertEqual(self.page.locator('#fsSpeedSvg .fsSpeedPath').count(), 1)
        self.assertEqual(self.errors, [])

    def test_toggling_during_replay_does_not_stop_it(self):
        self.page.evaluate('window.goatsSetFullscreenMode(true); window.goatsReplayStart(1);')
        self.page.wait_for_timeout(80)
        self.page.evaluate('window.goatsSetFullscreenOverlays(false,false,false);')
        self.assertTrue(self.page.evaluate('replayRunning'))
        self.assertEqual(self.page.locator('.brake-zone-table').count(), 0)
        self.assertFalse(self.page.locator('#fsSpeedPanel').is_visible())
        self.page.evaluate('window.goatsReplayPause();')
        self.assertFalse(self.page.evaluate('replayRunning'))
        self.assertGreater(self.page.evaluate('replayElapsed'), 0)
        self.page.evaluate('window.goatsReplayReset();')
        self.assertEqual(self.page.evaluate('replayElapsed'), 0)
        self.assertEqual(self.errors, [])

    def test_embedded_map_has_no_description_and_no_fullscreen_panels(self):
        self.assertEqual(self.page.locator('#legend').count(), 0)
        self.assertEqual(self.page.locator('.brake-zone-table').count(), 0)
        self.assertFalse(self.page.locator('#fsSpeedPanel').is_visible())
        self.page.evaluate('window.goatsSetFullscreenMode(true); window.goatsSetFullscreenMode(false);')
        self.assertEqual(self.page.locator('.brake-zone-table').count(), 0)
        self.assertFalse(self.page.locator('#fsSpeedPanel').is_visible())
        self.assertEqual(self.errors, [])

    def test_empty_session_controls(self):
        self.page.goto('about:blank')
        self.page.set_content(render_map_html(empty=True), wait_until='load')
        self.page.evaluate('window.goatsSetFullscreenMode(true); window.goatsSetFullscreenOverlays(true,true,true);')
        self.page.wait_for_timeout(180)
        self.assertEqual(self.page.locator('.brake-zone-table').count(), 0)
        self.assertEqual(self.page.locator('#fsSpeedValue').inner_text(), 'Dati velocità non disponibili')
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
