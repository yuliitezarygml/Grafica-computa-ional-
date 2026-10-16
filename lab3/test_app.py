"""Проверка управления, фонового построения и экспорта без монитора."""

import argparse
import json
import os
from pathlib import Path
import queue
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import numpy as np
import pygame as pg

from app import (
    HEADER, HEIGHT, WIDTH, FractalApp, RenderMessage, RenderRequest,
    RenderWorker, clip_segment, iteration_value,
)
from fractal import DEFAULT_VIEW, MAX_ITERATIONS, MIN_ITERATIONS


def finish_render(app):
    deadline = time.monotonic() + 5
    while app.rendering and time.monotonic() < deadline:
        app.poll_render()
        time.sleep(0.005)
    if app.rendering or app.error:
        raise AssertionError(f"Построение не завершено: {app.error}")


class AppTests(unittest.TestCase):
    def make_app(self, grade=10):
        app = FractalApp(grade, iterations=50)
        self.addCleanup(app.close)
        return app

    def key(self, app, key):
        app.handle_event(pg.event.Event(pg.KEYDOWN, key=key))

    def click(self, app, position, button=1):
        app.handle_event(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=position, button=button))

    def test_lower_grade_does_not_enable_higher_grade_controls(self):
        app = self.make_app(5)
        for key in (pg.K_UP, pg.K_b, pg.K_o):
            self.key(app, key)
        self.click(app, (600, HEADER + 200))
        self.assertEqual(app.iterations, 50)
        self.assertEqual(app.mode, "bw")
        self.assertEqual(app.view, DEFAULT_VIEW)
        self.assertFalse(app.show_orbit)

    def test_iteration_controls_and_limits(self):
        app = self.make_app(8)
        self.key(app, pg.K_UP)
        self.assertEqual(app.iterations, 100)
        self.key(app, pg.K_DOWN)
        self.assertEqual(app.iterations, 50)
        app.change_iterations(-10000)
        self.assertEqual(app.iterations, MIN_ITERATIONS)
        app.change_iterations(10000)
        self.assertEqual(app.iterations, MAX_ITERATIONS)
        self.key(app, pg.K_b)
        self.assertEqual(app.mode, "bw")
        self.key(app, pg.K_b)
        self.assertEqual(app.mode, "smooth")

    def test_cursor_zoom_and_reset(self):
        app = self.make_app(9)
        position = (650, HEADER + 210)
        anchor = app.view.point(650, 210, WIDTH, HEIGHT)
        self.click(app, position)
        self.assertEqual(app.zoom, 2)
        self.assertAlmostEqual(abs(app.view.point(650, 210, WIDTH, HEIGHT) - anchor), 0)
        view = app.view
        self.click(app, (100, 30))
        self.assertEqual(app.view, view)
        self.key(app, pg.K_r)
        self.assertEqual(app.view, DEFAULT_VIEW)
        self.assertEqual(app.iterations, 50)

    def test_orbit_select_toggle_and_draw(self):
        app = self.make_app()
        self.click(app, (620, HEADER + 180), button=2)
        self.assertTrue(app.show_orbit)
        self.assertEqual(app.selected_c, app.view.point(620, 180, WIDTH, HEIGHT))
        self.assertEqual(app.orbit_points[0], 0j)
        app.draw()
        self.key(app, pg.K_o)
        self.assertFalse(app.show_orbit)

    def test_render_export_has_matching_pixels_and_parameters(self):
        app = self.make_app()
        finish_render(app)
        with tempfile.TemporaryDirectory() as directory:
            path = app.save_snapshot(directory)
            self.assertIsInstance(path, Path)
            saved = pg.image.load(str(path))
            self.assertEqual(saved.get_size(), (900, 740))
            np.testing.assert_array_equal(
                pg.surfarray.array3d(saved.subsurface(app.canvas_rect)),
                pg.surfarray.array3d(app.image),
            )
            data = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(data["center"]["real"], app.view.center_x)
            self.assertEqual(data["vertical_span"], app.view.span)
            self.assertEqual(data["iterations"], 50)
            self.assertEqual(data["palette"], "smooth")

    def test_export_waits_for_complete_image_and_ignores_stale_results(self):
        app = self.make_app()
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(app.save_snapshot(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])
        app.worker.results.put(RenderMessage(app.generation - 1, "error", error="stale"))
        app.poll_render()
        self.assertEqual(app.error, "")

    def test_window_labels_have_no_unsupported_math_symbols(self):
        app = self.make_app()
        labels = []
        with patch.object(app, "text", side_effect=lambda value, *args, **kwargs: labels.append(value)):
            app.draw()
        for text in labels:
            for char in text:
                self.assertTrue(ord(char) < 128 or "А" <= char <= "я" or char in "Ёё", text)


class WorkerAndInputTests(unittest.TestCase):
    def test_latest_request_finishes_after_superseding_previous(self):
        worker = RenderWorker()
        self.addCleanup(worker.close)
        worker.request(RenderRequest(DEFAULT_VIEW, 2000, "smooth", 300, 200))
        latest = worker.request(RenderRequest(DEFAULT_VIEW, 25, "bw", 120, 80))
        deadline = time.monotonic() + 5
        messages = []
        while time.monotonic() < deadline:
            try:
                message = worker.results.get(timeout=0.1)
            except queue.Empty:
                continue
            if message.generation == latest:
                messages.append(message)
                if message.kind in ("done", "error"):
                    break
        self.assertTrue(messages)
        self.assertEqual(messages[-1].kind, "done")
        tiles = [message for message in messages if message.kind == "tile"]
        self.assertEqual(sum(message.pixels.shape[0] for message in tiles), 80)
        self.assertTrue(all(set(np.unique(message.pixels)).issubset({0, 255}) for message in tiles))

    def test_clipping_extreme_coordinates_and_outside_lines(self):
        rect = pg.Rect(0, HEADER, WIDTH, HEIGHT)
        self.assertEqual(clip_segment((-1e20, 300), (1e20, 300), rect), ((0, 300), (899, 300)))
        self.assertEqual(clip_segment((400, -1e20), (400, 1e20), rect), ((400, 104), (400, 663)))
        self.assertIsNone(clip_segment((-20, 200), (-1, 300), rect))

    def test_iteration_input_validation(self):
        self.assertEqual(iteration_value("300"), 300)
        for text in ("0", "-1", "2001", "abc", "1.5"):
            with self.assertRaises(argparse.ArgumentTypeError):
                iteration_value(text)


if __name__ == "__main__":
    unittest.main()
