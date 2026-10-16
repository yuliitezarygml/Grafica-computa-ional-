"""Геометрия, анимация и управление; графический контекст не требуется."""

import math
import os
import unittest

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame as pg

from app import HEADER, HEIGHT, WIDTH, FOOTER, OpenGLApp
from geometry import CUBE, ROOF, make_face
from state import SceneState


class GeometryTests(unittest.TestCase):
    def test_normals_are_unit_outward_and_faces_are_planar(self):
        for mesh, inside in ((CUBE, (0, 0, 0)), (ROOF, (0, .3, 0))):
            for face in mesh:
                self.assertAlmostEqual(sum(v*v for v in face.normal), 1)
                center = tuple(sum(p[i] for p in face.vertices) / len(face.vertices) for i in range(3))
                self.assertGreater(sum((center[i]-inside[i])*face.normal[i] for i in range(3)), 0)
                for vertex in face.vertices:
                    self.assertAlmostEqual(sum((vertex[i]-center[i])*face.normal[i] for i in range(3)), 0)
                self.assertEqual(len(face.vertices), len(face.uv))
                self.assertTrue(all(0 <= value <= 1 for uv in face.uv for value in uv))

    def test_cube_has_six_different_normals(self):
        self.assertEqual(len({face.normal for face in CUBE}), 6)
        with self.assertRaises(ValueError):
            make_face((0, 0, 0), (1, 0, 0), (2, 0, 0))


class StateTests(unittest.TestCase):
    def test_animation_does_not_depend_on_frame_rate(self):
        first, second = SceneState(), SceneState()
        first.door_open = second.door_open = True
        first.update(1)
        for _ in range(100):
            second.update(.01)
        for field in ("rotation_y", "blade_angle", "door_angle"):
            self.assertAlmostEqual(getattr(first, field), getattr(second, field))

    def test_door_finishes_in_both_directions_without_overshoot(self):
        state = SceneState()
        state.door_open = True
        state.update(10)
        self.assertEqual(state.door_angle, 100)
        state.door_open = False
        state.update(10)
        self.assertEqual(state.door_angle, 0)

    def test_camera_has_correct_distance_and_limits(self):
        state = SceneState()
        state.orbit_camera(10000, 10000)
        state.zoom(-10000)
        self.assertEqual(state.camera_pitch, 80)
        self.assertEqual(state.distance, 3.8)
        eye = state.eye()
        self.assertAlmostEqual(math.sqrt(eye[0]**2 + (eye[1]-.55)**2 + eye[2]**2), state.distance)
        state.orbit_camera(0, -10000)
        state.zoom(10000)
        self.assertEqual(state.camera_pitch, -5)
        self.assertEqual(state.distance, 20)

    def test_grade_features_reset_and_invalid_input(self):
        for grade in range(5, 11):
            state = SceneState(grade)
            state.update(1)
            self.assertEqual(state.rotation_y, 18 if grade >= 7 else 0)
            self.assertEqual(state.lighting, grade >= 9)
            self.assertEqual(state.textured, grade >= 10)
            state.rotate(12, 17, 34)
            state.distance = 15
            state.reset()
            self.assertEqual(state, SceneState(grade))
        for invalid in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                SceneState().update(invalid)
        with self.assertRaises(ValueError):
            SceneState(4)


class ControlTests(unittest.TestCase):
    def make_app(self, grade=10):
        # Контроллеру событий OpenGL не нужен.
        app = OpenGLApp.__new__(OpenGLApp)
        app.state = SceneState(grade)
        app.held = set()
        app.dragging = False
        app.running = True
        app.snapshot_requested = False
        app.hud_updated = -1
        app.canvas_rect = pg.Rect(0, HEADER, WIDTH, HEIGHT - HEADER - FOOTER)
        return app

    def key(self, app, key, event_type=pg.KEYDOWN):
        app.handle_event(pg.event.Event(event_type, key=key))

    def test_keyboard_rotation_and_camera_then_reset(self):
        app = self.make_app(8)
        self.key(app, pg.K_RIGHT)
        self.key(app, pg.K_q)
        self.key(app, pg.K_w)
        app.update(.5)
        self.assertEqual(app.state.rotation_y, 32.5)
        self.assertEqual(app.state.rotation_z, 327.5)
        self.assertAlmostEqual(app.state.distance, 6.8)
        self.assertFalse(app.state.auto_rotate)
        self.key(app, pg.K_r)
        self.assertEqual(app.state, SceneState(8))
        self.assertFalse(app.held)

    def test_mouse_drag_starts_only_over_scene_and_focus_loss_stops_controls(self):
        app = self.make_app(9)
        app.handle_event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(30, 20)))
        self.assertFalse(app.dragging)
        app.handle_event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(400, 300)))
        app.handle_event(pg.event.Event(pg.MOUSEMOTION, rel=(20, 10)))
        self.assertEqual(app.state.camera_yaw, 23)
        self.assertEqual(app.state.camera_pitch, 25.5)
        self.key(app, pg.K_w)
        app.handle_event(pg.event.Event(pg.WINDOWFOCUSLOST))
        self.assertFalse(app.dragging)
        self.assertFalse(app.held)

    def test_individual_animation_toggles_and_pause(self):
        app = self.make_app()
        self.key(app, pg.K_h)
        self.key(app, pg.K_m)
        self.key(app, pg.K_SPACE)
        app.update(1)
        self.assertEqual(app.state.door_angle, 90)
        self.assertEqual(app.state.blade_angle, 12)
        self.assertEqual(app.state.rotation_y, 0)
        self.key(app, pg.K_t)
        self.key(app, pg.K_l)
        self.assertFalse(app.state.textured)
        self.assertFalse(app.state.lighting)

    def test_controls_do_not_unlock_higher_grades(self):
        app = self.make_app(5)
        for key in (pg.K_RIGHT, pg.K_SPACE, pg.K_h, pg.K_t, pg.K_l):
            self.key(app, key)
        app.update(1)
        self.assertEqual(app.state, SceneState(5))


if __name__ == "__main__":
    unittest.main()
