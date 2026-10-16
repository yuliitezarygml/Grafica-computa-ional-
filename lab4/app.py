"""Учебная сцена OpenGL 2.1: матрицы, глубина, нормали, свет и текстуры."""

import argparse
from datetime import datetime
from pathlib import Path
import time

import pygame as pg
from OpenGL import GL as gl
from OpenGL.GLU import gluLookAt, gluPerspective

from geometry import CUBE, ROOF, CUBE_COLORS, WALL_COLORS, ROOF_COLORS
from state import SceneState


WIDTH, HEIGHT = 1000, 760
HEADER, FOOTER = 96, 94
ASSETS = Path(__file__).resolve().parent / "assets"
BACKGROUND = (12, 19, 30)
TEXT = (228, 236, 246)
MUTED = (162, 180, 201)
ACCENT = (89, 218, 206)


class OpenGLApp:
    def __init__(self, grade=10, hidden=False):
        self.state = SceneState(grade)
        self.running = True
        self.dragging = False
        self.held = set()
        self.snapshot_requested = False
        self.notice = ""
        self.notice_until = 0.0
        self.hud_updated = -1.0
        self.hud_texture = None
        self.wall_texture = None
        pg.display.init()
        pg.font.init()
        # Контекст совместимости нужен для учебных glBegin/glMatrixMode/glLight.
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 2)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 1)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, 24)
        pg.display.gl_set_attribute(pg.GL_DOUBLEBUFFER, 1)
        flags = pg.OPENGL | pg.DOUBLEBUF | (pg.HIDDEN if hidden else 0)
        try:
            pg.display.set_mode((WIDTH, HEIGHT), flags)
            pg.display.set_caption(f"OpenGL - лабораторная 4 - уровень {grade}")
            version = gl.glGetString(gl.GL_VERSION)
            if not version:
                raise RuntimeError("Не удалось создать контекст OpenGL")
            self.gl_version = version.decode("ascii", errors="replace")
            self.renderer = gl.glGetString(gl.GL_RENDERER).decode("utf-8", errors="replace")
            self.font = pg.font.SysFont("Arial", 16)
            self.small = pg.font.SysFont("Arial", 14)
            self.title_font = pg.font.SysFont("Arial", 26, bold=True)
            self.canvas_rect = pg.Rect(0, HEADER, WIDTH, HEIGHT - HEADER - FOOTER)
            gl.glClearColor(0.065, 0.10, 0.15, 1.0)
            gl.glClearDepth(1.0)
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthFunc(gl.GL_LEQUAL)
            # Обратная транспонированная матрица преобразует нормали;
            # GL_NORMALIZE возвращает единичную длину после glScalef.
            gl.glEnable(gl.GL_NORMALIZE)
            gl.glShadeModel(gl.GL_SMOOTH)
            gl.glEnable(gl.GL_COLOR_MATERIAL)
            gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (0.45, 0.45, 0.45, 1))
            gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 36)
            gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT, (0.22, 0.22, 0.25, 1))
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (0.12, 0.12, 0.12, 1))
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (0.90, 0.86, 0.77, 1))
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, (1, 1, 1, 1))
            if grade >= 10:
                # Растровый PNG действительно читается с диска, а не рисуется вместо текстуры.
                self.wall_texture = self.upload_texture(pg.image.load(str(ASSETS / "wall.png")))
            self.hud_texture = self.upload_texture(pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA))
        except Exception:
            self.close()
            raise

    def upload_texture(self, surface):
        texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, *surface.get_size(), 0,
                        gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, pg.image.tobytes(surface, "RGBA", True))
        return texture

    def mesh(self, faces, color=None, palette=None, texture=None):
        if texture:
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        else:
            gl.glDisable(gl.GL_TEXTURE_2D)
        for index, face in enumerate(faces):
            gl.glColor3fv(color if color is not None else palette[index])
            gl.glBegin(gl.GL_TRIANGLES if len(face.vertices) == 3 else gl.GL_QUADS)
            gl.glNormal3fv(face.normal)
            for uv, vertex in zip(face.uv, face.vertices):
                gl.glTexCoord2fv(uv)
                gl.glVertex3fv(vertex)
            gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)

    def solid(self, mesh, position, size, color=None, palette=None, texture=None):
        # Локальные преобразования не затрагивают следующий объект.
        gl.glPushMatrix()
        gl.glTranslatef(*position)
        gl.glScalef(*size)
        self.mesh(mesh, color, palette, texture)
        gl.glPopMatrix()

    def box(self, position, size, color, texture=None):
        self.solid(CUBE, position, size, color=color, texture=texture)

    def draw_house(self):
        wall_texture = self.wall_texture if self.state.textured else None
        self.solid(CUBE, (-0.7, 0.3, 0), (2, 2, 1.8), palette=WALL_COLORS, texture=wall_texture)
        self.solid(ROOF, (-0.7, 1.3, 0), (2.45, 1.0, 2.2), palette=ROOF_COLORS)
        self.box((-.25, 1.95, -.42), (.32, 1.0, .32), (.53, .29, .23))
        self.box((-.25, 2.45, -.42), (.44, .12, .44), (.33, .24, .23))

        # Окно на передней стене: рама, стекло, два переплёта.
        frame, glass = (.97, .94, .83), (.22, .61, .73)
        self.box((-.15, .50, .94), (.64, .69, .10), frame)
        self.box((-.15, .50, 1.0), (.52, .57, .04), glass)
        self.box((-.15, .50, 1.03), (.035, .57, .025), frame)
        self.box((-.15, .50, 1.03), (.52, .035, .025), frame)
        self.box((.34, .50, -.10), (.10, .69, .70), frame)
        self.box((.40, .50, -.10), (.04, .57, .58), glass)
        self.box((.43, .50, -.10), (.025, .57, .035), frame)

        # Поворот двери вокруг петли: T(петля) * R * T(центр двери) * S.
        gl.glPushMatrix()
        gl.glTranslatef(-1.35, -.7, .96)
        gl.glRotatef(-self.state.door_angle, 0, 1, 0)
        self.box((.24, .52, 0), (.48, 1.04, .09), (.31, .19, .13))
        self.box((.40, .52, .07), (.045, .045, .055), (.98, .76, .30))
        gl.glPopMatrix()

    def draw_windmill(self):
        self.box((1.65, .35, -.15), (.36, 2.1, .36), (.54, .38, .25))
        self.box((1.65, -.64, -.15), (.75, .13, .75), (.59, .61, .56))
        # Дочерние лопасти вращаются вокруг общей оси независимо от сцены.
        gl.glPushMatrix()
        gl.glTranslatef(1.65, 1.45, .14)
        gl.glRotatef(self.state.blade_angle, 0, 0, 1)
        for _ in range(4):
            self.box((0, .65, .04), (.18, 1.15, .08), (.96, .90, .72))
            self.box((0, 1.1, .09), (.20, .23, .035), (.83, .32, .24))
            gl.glRotatef(90, 0, 0, 1)
        self.box((0, 0, .11), (.31, .31, .19), (.93, .68, .29))
        gl.glPopMatrix()

    def draw_scene(self):
        if self.state.grade < 8:
            self.solid(CUBE, (0, 0, 0), (2, 2, 2),
                       color=(.30, .84, .81) if self.state.grade == 5 else None,
                       palette=CUBE_COLORS)
            return
        self.box((0, -.80, 0), (6.2, .18, 4.4), (.29, .42, .34))
        self.box((-1.11, -.695, 1.58), (.68, .04, 1.18), (.73, .71, .60))
        self.draw_house()
        if self.state.grade >= 10:
            self.draw_windmill()

    def draw(self, fps=0.0):
        state = self.state
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glViewport(0, FOOTER, WIDTH, self.canvas_rect.height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        aspect = WIDTH / self.canvas_rect.height
        if state.grade >= 7:
            gluPerspective(45, aspect, .1, 60)
        else:
            gl.glOrtho(-2.6 * aspect, 2.6 * aspect, -2.6, 2.6, .1, 60)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        target_y = .55 if state.grade >= 8 else 0.0
        gluLookAt(*state.eye(), 0, target_y, 0, 0, 1, 0)
        if state.lighting:
            gl.glEnable(gl.GL_LIGHTING)
            gl.glEnable(gl.GL_LIGHT0)
            # Источник закреплён в мире: вызов после камеры, до вращения модели.
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (4, 7, 5, 1))
        else:
            gl.glDisable(gl.GL_LIGHTING)
            gl.glDisable(gl.GL_LIGHT0)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE if state.wireframe else gl.GL_FILL)
        gl.glPushMatrix()
        gl.glRotatef(state.rotation_x, 1, 0, 0)
        gl.glRotatef(state.rotation_y, 0, 1, 0)
        gl.glRotatef(state.rotation_z, 0, 0, 1)
        self.draw_scene()
        gl.glPopMatrix()
        self.draw_hud(fps)

    def hud_lines(self, fps):
        state = self.state
        description = {
            5: "Куб одного цвета. Каркасная модель.",
            6: "Разноцветные грани куба. Проверка глубины.",
            7: "Перспективная проекция. Автоматическое вращение.",
            8: "Составная фигура: домик, крыша, дымоход. Управление с клавиатуры.",
            9: "Освещение и нормали граней. Обзор сцены с помощью мыши.",
            10: "Текстура из PNG. Открывающаяся дверь и анимация мельницы.",
        }[state.grade]
        status = f"Проекция: {'перспективная' if state.grade >= 7 else 'ортогональная'}"
        status += f"   |   Вращение: {'включено' if state.auto_rotate else 'пауза'}"
        if state.grade >= 9:
            status += f"   |   Свет: {'включен' if state.lighting else 'выключен'}"
        if state.grade >= 10:
            status += f"   |   Текстура: {'включена' if state.textured else 'выключена'}"
        first = "Esc: выход"
        if state.grade >= 7:
            first += "   |   Space: вращение"
        if state.grade >= 8:
            first = "Стрелки: X/Y   |   Q/E: Z   |   W/S или +/-: камера   |   R: сброс   |   F: каркас   |   " + first
        second = ""
        if state.grade >= 9:
            second = "Зажатая левая кнопка мыши: обзор   |   Колесо: камера   |   L: свет"
        if state.grade >= 10:
            second += "   |   T: текстура   |   H: дверь   |   M: мельница"
        third = "Буфер глубины включен"
        if state.grade >= 8:
            third = (f"Камера: {state.distance:.1f}   |   Углы X: {state.rotation_x:.0f}  Y: {state.rotation_y:.0f}  Z: {state.rotation_z:.0f}"
                     "   |   P: сохранить снимок")
        bottom = self.notice if time.monotonic() < self.notice_until else f"OpenGL {self.gl_version}   |   {fps:.0f} кадров/с"
        return description, status, first, second, third, bottom

    def draw_hud(self, fps):
        now = time.monotonic()
        if now - self.hud_updated >= .12:
            surface = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            pg.draw.rect(surface, (*BACKGROUND, 255), (0, 0, WIDTH, HEADER))
            pg.draw.rect(surface, (*BACKGROUND, 255), (0, HEIGHT - FOOTER, WIDTH, FOOTER))
            def text(value, pos, font=None, color=TEXT):
                surface.blit((font or self.font).render(value, True, color), pos)
            text("ОСНОВЫ 3D-ГРАФИКИ", (20, 9), self.title_font)
            text(f"ЛАБОРАТОРНАЯ 04  /  УРОВЕНЬ {self.state.grade}", (688, 21), self.small, MUTED)
            description, status, first, second, third, bottom = self.hud_lines(fps)
            text(description, (20, 45), color=MUTED)
            text(status, (20, 72), self.small, ACCENT)
            for index, value in enumerate((first, second, third, bottom)):
                text(value, (20, HEIGHT - FOOTER + 7 + index * 21), self.small,
                     ACCENT if index == 3 else TEXT if index == 0 else MUTED)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_texture)
            gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, WIDTH, HEIGHT, gl.GL_RGBA,
                              gl.GL_UNSIGNED_BYTE, pg.image.tobytes(surface, "RGBA", True))
            self.hud_updated = now
        # Для текста временно переходим к экранным координатам, затем
        # восстанавливаем матрицы и состояния трёхмерной сцены.
        gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT
                        | gl.GL_TEXTURE_BIT | gl.GL_POLYGON_BIT | gl.GL_VIEWPORT_BIT | gl.GL_CURRENT_BIT)
        gl.glViewport(0, 0, WIDTH, HEIGHT)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.hud_texture)
        gl.glColor4f(1, 1, 1, 1)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, WIDTH, HEIGHT, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glBegin(gl.GL_QUADS)
        for uv, point in (((0, 1), (0, 0)), ((1, 1), (WIDTH, 0)),
                          ((1, 0), (WIDTH, HEIGHT)), ((0, 0), (0, HEIGHT))):
            gl.glTexCoord2fv(uv)
            gl.glVertex2fv(point)
        gl.glEnd()
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopAttrib()

    def handle_event(self, event):
        state = self.state
        if event.type == pg.QUIT:
            self.running = False
        elif event.type == pg.KEYDOWN:
            self.held.add(event.key)
            if event.key == pg.K_ESCAPE:
                self.running = False
            elif state.grade >= 7 and event.key == pg.K_SPACE:
                state.auto_rotate = not state.auto_rotate
            elif state.grade >= 8:
                if event.key == pg.K_r:
                    state.reset()
                    self.held.clear()
                elif event.key == pg.K_f:
                    state.wireframe = not state.wireframe
                elif event.key == pg.K_p:
                    self.snapshot_requested = True
                elif event.key in (pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT, pg.K_q, pg.K_e):
                    state.auto_rotate = False
            if state.grade >= 9 and event.key == pg.K_l:
                state.lighting = not state.lighting
            if state.grade >= 10:
                if event.key == pg.K_t:
                    state.textured = not state.textured
                elif event.key == pg.K_h:
                    state.door_open = not state.door_open
                elif event.key == pg.K_m:
                    state.windmill_running = not state.windmill_running
            self.hud_updated = -1
        elif event.type == pg.KEYUP:
            self.held.discard(event.key)
        elif event.type == pg.WINDOWFOCUSLOST:
            self.held.clear()
            self.dragging = False
        elif state.grade >= 9:
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                self.dragging = self.canvas_rect.collidepoint(event.pos)
                if self.dragging:
                    state.auto_rotate = False
            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            elif event.type == pg.MOUSEMOTION and self.dragging:
                state.orbit_camera(*event.rel)
            elif event.type == pg.MOUSEWHEEL and self.canvas_rect.collidepoint(pg.mouse.get_pos()):
                state.zoom(-event.y * .5)

    def update(self, dt):
        state = self.state
        if state.grade >= 8:
            held = self.held
            state.rotate(x=((pg.K_DOWN in held) - (pg.K_UP in held)) * 65 * dt,
                         y=((pg.K_RIGHT in held) - (pg.K_LEFT in held)) * 65 * dt,
                         z=((pg.K_e in held) - (pg.K_q in held)) * 65 * dt)
            farther = any(key in held for key in (pg.K_s, pg.K_MINUS, pg.K_KP_MINUS))
            closer = any(key in held for key in (pg.K_w, pg.K_PLUS, pg.K_EQUALS, pg.K_KP_PLUS))
            state.zoom((farther - closer) * 4 * dt)
        state.update(dt)

    def capture(self, path=None):
        if path is None:
            stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
            path = Path(__file__).resolve().parent / "screenshots" / f"opengl_{stamp}.png"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
        gl.glReadBuffer(gl.GL_BACK)
        pixels = gl.glReadPixels(0, 0, WIDTH, HEIGHT, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
        surface = pg.image.frombytes(bytes(pixels), (WIDTH, HEIGHT), "RGB")
        pg.image.save(pg.transform.flip(surface, False, True), str(path))
        self.notice = f"Сохранено: {path.name}"
        self.notice_until = time.monotonic() + 5
        self.hud_updated = -1
        return path

    def run(self, frames=None, screenshot=None):
        clock = pg.time.Clock()
        count = 0
        try:
            while self.running:
                dt = min(clock.tick(60) / 1000, .1)
                for event in pg.event.get():
                    self.handle_event(event)
                self.update(dt)
                self.draw(clock.get_fps())
                count += 1
                if self.snapshot_requested:
                    try:
                        self.capture()
                    except (OSError, pg.error) as error:
                        self.notice = f"Ошибка сохранения: {error}"
                        self.notice_until = time.monotonic() + 5
                    self.snapshot_requested = False
                if frames is not None and count >= frames:
                    if screenshot is not None:
                        self.capture(screenshot)
                    self.running = False
                pg.display.flip()
        finally:
            self.close()

    def close(self):
        textures = [texture for texture in (self.wall_texture, self.hud_texture) if texture is not None]
        try:
            if textures and pg.display.get_surface() is not None:
                gl.glDeleteTextures(textures)
        finally:
            self.wall_texture = self.hud_texture = None
            pg.quit()


def main(grade=None):
    parser = argparse.ArgumentParser(description="Лабораторная 4: основы 3D-графики в OpenGL")
    if grade is None:
        parser.add_argument("--grade", type=int, choices=range(5, 11), default=10)
    parser.add_argument("--frames", type=int, help="завершить после указанного числа кадров")
    parser.add_argument("--screenshot", type=Path, help="сохранить последний кадр в PNG; используется с --frames")
    args = parser.parse_args()
    if args.frames is not None and args.frames <= 0:
        parser.error("число кадров должно быть положительным")
    if args.screenshot is not None and args.frames is None:
        parser.error("--screenshot используется вместе с --frames")
    try:
        app = OpenGLApp(grade if grade is not None else args.grade)
        print(f"OpenGL: {app.gl_version}\nВидеоустройство: {app.renderer}")
        app.run(args.frames, args.screenshot)
    except (pg.error, RuntimeError, OSError) as error:
        parser.exit(1, f"Не удалось запустить приложение: {error}\n")
