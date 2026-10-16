"""Проверки на настоящем OpenGL: RUN_OPENGL_TESTS=1 python -m unittest ..."""

import os
from pathlib import Path
import tempfile
import unittest

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import numpy as np
import pygame as pg
from OpenGL import GL as gl

from app import FOOTER, HEADER, HEIGHT, WIDTH, OpenGLApp
from state import SceneState


@unittest.skipUnless(os.environ.get("RUN_OPENGL_TESTS") == "1", "Нужен настоящий контекст OpenGL")
class OpenGLTests(unittest.TestCase):
    def setUp(self):
        self.app = OpenGLApp(hidden=True)
        self.addCleanup(self.app.close)

    def scene_pixels(self):
        data = gl.glReadPixels(0, FOOTER, WIDTH, HEIGHT - HEADER - FOOTER,
                               gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
        return np.frombuffer(bytes(data), dtype=np.uint8).copy()

    def test_all_grades_render_and_preserve_matrix_and_depth_state(self):
        self.assertGreaterEqual(pg.display.gl_get_attribute(pg.GL_DEPTH_SIZE), 16)
        for grade in range(5, 11):
            with self.subTest(grade=grade):
                self.app.state = SceneState(grade)
                self.app.draw()
                self.assertTrue(gl.glIsEnabled(gl.GL_DEPTH_TEST))
                self.assertEqual(int(gl.glGetIntegerv(gl.GL_MODELVIEW_STACK_DEPTH)), 1)
                self.assertEqual(int(gl.glGetIntegerv(gl.GL_PROJECTION_STACK_DEPTH)), 1)
                matrix = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)
                self.assertAlmostEqual(float(matrix[3][3]), 0 if grade >= 7 else 1)
                pixels = self.scene_pixels().reshape(-1, 3)
                background = pixels[0]
                self.assertGreater(np.count_nonzero(np.any(pixels != background, axis=1)), 500)
                self.assertEqual(gl.glGetError(), gl.GL_NO_ERROR)

    def test_lighting_texture_and_animation_change_visible_scene(self):
        self.app.draw()
        original = self.scene_pixels()
        self.app.state.textured = False
        self.app.draw()
        self.assertGreater(np.count_nonzero(original != self.scene_pixels()), 1000)
        self.app.state.lighting = False
        self.app.draw()
        unlit = self.scene_pixels()
        self.assertGreater(np.count_nonzero(original != unlit), 1000)
        self.app.state.door_open = True
        self.app.state.auto_rotate = False
        self.app.update(1)
        self.app.draw()
        self.assertGreater(np.count_nonzero(unlit != self.scene_pixels()), 500)
        self.assertTrue(gl.glIsTexture(self.app.wall_texture))
        self.assertEqual(gl.glGetError(), gl.GL_NO_ERROR)

    def test_depth_rejects_far_face_drawn_after_near_face(self):
        gl.glViewport(0, 0, WIDTH, HEIGHT)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(-1, 1, -1, 1, -10, 10)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_BLEND)
        for depth_enabled, expected in ((True, (255, 0, 0)), (False, (0, 0, 255))):
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            (gl.glEnable if depth_enabled else gl.glDisable)(gl.GL_DEPTH_TEST)
            for z, color in ((1, (1, 0, 0)), (-1, (0, 0, 1))):
                gl.glColor3fv(color)
                gl.glBegin(gl.GL_QUADS)
                for x, y in ((-.8, -.8), (.8, -.8), (.8, .8), (-.8, .8)):
                    gl.glVertex3f(x, y, z)
                gl.glEnd()
            pixel = bytes(gl.glReadPixels(WIDTH//2, HEIGHT//2, 1, 1, gl.GL_RGB, gl.GL_UNSIGNED_BYTE))
            self.assertEqual(tuple(pixel), expected)

    def test_capture_matches_framebuffer_and_hud_labels_fit(self):
        self.app.draw(60)
        with tempfile.TemporaryDirectory() as directory:
            path = self.app.capture(Path(directory) / "scene.png")
            saved = pg.image.load(str(path))
            self.assertEqual(saved.get_size(), (WIDTH, HEIGHT))
            # Переворот из нижнего начала OpenGL в верхнее начало PNG.
            data = bytes(gl.glReadPixels(0, 0, WIDTH, HEIGHT, gl.GL_RGB, gl.GL_UNSIGNED_BYTE))
            actual = pg.image.tobytes(pg.transform.flip(saved, False, True), "RGB")
            self.assertEqual(actual, data)
        for label in self.app.hud_lines(60):
            self.assertLessEqual(self.app.small.size(label)[0], WIDTH - 40)
            for char in label:
                self.assertTrue(ord(char) < 128 or "А" <= char <= "я" or char in "Ёё")


if __name__ == "__main__":
    unittest.main()
