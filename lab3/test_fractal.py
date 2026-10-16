"""Проверки формулы, отображения координат, полос и режимов раскраски."""

import math
import threading
import unittest

import numpy as np

from fractal import DEFAULT_VIEW, View, colorize, compute_escape, orbit, simonbrot_step


def reference_escape(c: complex, limit: int) -> tuple[int, float]:
    """Независимый скалярный эталон по записи из руководства."""
    z = 0j
    for step in range(1, limit + 1):
        z = z**2 * complex(abs(z.real), abs(z.imag))**2 + c
        if abs(z) > 2:
            return step, max(0, step + 1 - math.log(math.log(abs(z))) / math.log(4))
    return 0, 0.0


class ViewTests(unittest.TestCase):
    def test_center_and_orientation(self):
        view = View(0.25, -0.5, 4)
        self.assertEqual(view.point(400, 200, 800, 400), 0.25 - 0.5j)
        self.assertEqual(view.point(400, 0, 800, 400), 0.25 + 1.5j)
        self.assertEqual(view.point(400, 400, 800, 400), 0.25 - 2.5j)

    def test_axes_use_same_scale(self):
        view = View()
        center = view.point(400, 200, 800, 400)
        horizontal = abs(view.point(401, 200, 800, 400) - center)
        vertical = abs(view.point(400, 201, 800, 400) - center)
        self.assertAlmostEqual(horizontal, vertical)
        self.assertAlmostEqual(horizontal, 3 / 400)

    def test_zoom_keeps_cursor_anchor(self):
        for factor in (0.5, 1.0, 2.0, 7.5):
            view = View(-0.3, 0.2, 3)
            zoomed = view.zoom_at(117.2, 73.6, 800, 500, factor)
            self.assertAlmostEqual(zoomed.point(117.2, 73.6, 800, 500),
                                   view.point(117.2, 73.6, 800, 500))
            self.assertAlmostEqual(zoomed.span, view.span / factor)

    def test_pan_uses_complex_coordinates(self):
        self.assertEqual(View(1, 2, 3).pan(-0.25, 0.5), View(0.75, 2.5, 3))

    def test_view_is_immutable(self):
        with self.assertRaises(AttributeError):
            DEFAULT_VIEW.span = 10

    def test_invalid_view_and_zoom(self):
        for span in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                View(span=span)
        for factor in (0, -2, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                DEFAULT_VIEW.zoom_at(0, 0, 100, 100, factor)


class FractalTests(unittest.TestCase):
    def test_step_uses_coordinatewise_absolute_values(self):
        c = -0.23 + 0.17j
        for z in (0j, 0.4 + 0.7j, -0.4 + 0.7j, -0.4 - 0.7j, 0.4 - 0.7j):
            expected = z**2 * complex(abs(z.real), abs(z.imag))**2 + c
            self.assertAlmostEqual(simonbrot_step(z, c), expected)
        z = 0.4 + 0.7j
        self.assertNotAlmostEqual(simonbrot_step(z, c), z**2 * abs(z)**2 + c)

    def test_orbit_includes_zero_and_first_escape(self):
        self.assertEqual(orbit(1 + 0j, 20), [0j, 1 + 0j, 2 + 0j, 17 + 0j])
        self.assertEqual(orbit(0j, 3), [0j, 0j, 0j, 0j])
        self.assertEqual(orbit(3j, 10), [0j, 3j])

    def test_escape_on_last_iteration_is_external(self):
        view = View(1, 0, 1)
        before, _ = compute_escape(view, 1, 1, 2)
        counts, smooth = compute_escape(view, 1, 1, 3)
        self.assertEqual(before[0, 0], 0)
        self.assertEqual(counts[0, 0], 3)
        self.assertGreater(smooth[0, 0], 0)

    def test_radius_two_is_not_yet_escape(self):
        counts, _ = compute_escape(View(2, 0, 1), 1, 1, 1)
        self.assertEqual(counts[0, 0], 0)
        counts, _ = compute_escape(View(2.001, 0, 1), 1, 1, 1)
        self.assertEqual(counts[0, 0], 1)

    def test_vector_result_matches_independent_scalar_orbits(self):
        width, height, limit = 17, 13, 37
        view = View(-0.13, -0.19, 2.9)
        counts, smooth = compute_escape(view, width, height, limit)
        for row in range(height):
            for column in range(width):
                c = complex(
                    view.center_x + (column + 0.5 - width / 2) * view.span / height,
                    view.center_y + (height / 2 - row - 0.5) * view.span / height,
                )
                expected_count, expected_smooth = reference_escape(c, limit)
                self.assertEqual(counts[row, column], expected_count)
                self.assertAlmostEqual(smooth[row, column], expected_smooth, places=9)

    def test_tiles_match_whole_image(self):
        view = View(-0.3, -0.1, 3.1)
        whole = compute_escape(view, 31, 23, 60)
        tiles = [compute_escape(view, 31, size, 60, row_start=start, total_height=23)
                 for start, size in ((0, 7), (7, 9), (16, 7))]
        np.testing.assert_array_equal(np.concatenate([t[0] for t in tiles]), whole[0])
        np.testing.assert_array_equal(np.concatenate([t[1] for t in tiles]), whole[1])

    def test_arrays_have_expected_types_and_finite_values(self):
        counts, smooth = compute_escape(DEFAULT_VIEW, 81, 51, 200)
        self.assertEqual(counts.shape, (51, 81))
        self.assertEqual(counts.dtype, np.int32)
        self.assertEqual(smooth.dtype, np.float64)
        self.assertTrue(np.all(np.isfinite(smooth)))
        self.assertTrue(np.all((counts >= 0) & (counts <= 200)))
        self.assertTrue(np.any(counts == 0))
        self.assertTrue(np.any(counts > 0))
        self.assertTrue(np.all(smooth[counts == 0] == 0))

    def test_already_cancelled_computation_returns_none(self):
        cancelled = threading.Event()
        cancelled.set()
        self.assertIsNone(compute_escape(DEFAULT_VIEW, 80, 50, 200, cancelled))

    def test_cancellation_is_checked_during_iteration(self):
        class CancelAfterThreeChecks:
            checks = 0

            def is_set(self):
                self.checks += 1
                return self.checks >= 3

        cancelled = CancelAfterThreeChecks()
        self.assertIsNone(compute_escape(View(0, 0, 0.01), 20, 10, 200, cancelled))
        self.assertEqual(cancelled.checks, 3)

    def test_invalid_calculation_arguments(self):
        for width, height, limit in ((0, 2, 10), (2, -1, 10), (2, 2, 0), (2, 2, 1.5)):
            with self.assertRaises(ValueError):
                compute_escape(DEFAULT_VIEW, width, height, limit)
        with self.assertRaises(ValueError):
            compute_escape(DEFAULT_VIEW, 2, 3, 10, row_start=2, total_height=4)


class ColorTests(unittest.TestCase):
    def setUp(self):
        self.counts = np.array([[0, 1, 2], [3, 12, 25]], dtype=np.int32)
        self.smooth = np.array([[0, 1.2, 2.8], [3.2, 12.1, 25.7]], dtype=np.float64)

    def test_all_modes_return_rgb_and_black_interior(self):
        for mode in ("bw", "discrete", "smooth"):
            rgb = colorize(self.counts, self.smooth, mode)
            self.assertEqual(rgb.shape, (2, 3, 3))
            self.assertEqual(rgb.dtype, np.uint8)
            np.testing.assert_array_equal(rgb[0, 0], [0, 0, 0])
            self.assertTrue(np.all(np.any(rgb[self.counts > 0] > 0, axis=1)))

    def test_bw_uses_only_black_and_white(self):
        rgb = colorize(self.counts, self.smooth, "bw")
        self.assertTrue(np.all(rgb[self.counts > 0] == 255))

    def test_discrete_color_uses_iteration_number(self):
        first = colorize(self.counts, self.smooth, "discrete")
        other = colorize(self.counts, self.smooth + 17, "discrete")
        np.testing.assert_array_equal(first, other)
        self.assertFalse(np.array_equal(first[0, 1], first[0, 2]))

    def test_smooth_color_changes_with_fractional_iteration(self):
        counts = np.ones((1, 2), dtype=np.int32)
        rgb = colorize(counts, np.array([[5.1, 5.9]]), "smooth")
        self.assertFalse(np.array_equal(rgb[0, 0], rgb[0, 1]))

    def test_invalid_mode_and_shape(self):
        with self.assertRaises(ValueError):
            colorize(self.counts, self.smooth, "missing")
        with self.assertRaises(ValueError):
            colorize(self.counts, np.zeros((1, 1)))


if __name__ == "__main__":
    unittest.main()
