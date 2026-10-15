#!/usr/bin/env python3
"""Carnelian Conduit — neon pipe-flow arcade for ElbowOS. Python 3 + pygame."""

import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv

if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/workspace/artifacts/CARNELIAN_CONDUIT_ElbowOS.mp4")
TITLE, HANDLE = "CARNELIAN CONDUIT", "x.com/ElbowOS"

BG = (8, 6, 22)
CYAN = (0, 255, 220)
MAG = (255, 40, 180)
GOLD = (255, 200, 40)
ORANGE = (255, 120, 30)
WHITE = (240, 240, 255)
DIM = (40, 30, 70)

# Directions: N=0, E=1, S=2, W=3
DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]

COLS, ROWS = 7, 12
CELL = 110
OX = (W - COLS * CELL) // 2
OY = 280

class Pipe:
    def __init__(self, kind, rot=0):
        self.kind = kind  # 0=straight, 1=elbow, 2=T, 3=cross
        self.rot = rot % 4
    def openings(self):
        if self.kind == 0:  # straight
            base = {0, 2}
        elif self.kind == 1:  # elbow
            base = {0, 1}
        elif self.kind == 2:  # T
            base = {0, 1, 2}
        else:  # cross
            base = {0, 1, 2, 3}
        return {(d + self.rot) % 4 for d in base}
    def has(self, d):
        return d in self.openings()
    def rotate(self):
        self.rot = (self.rot + 1) % 4

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self.screen = pygame.display.set_mode((W, H), pygame.HIDDEN)
        self.font = pygame.font.SysFont("arial", 72, bold=True)
        self.sfont = pygame.font.SysFont("arial", 48, bold=True)
        self.tiny = pygame.font.SysFont("arial", 32)
        self.clock = pygame.time.Clock()
        self.reset()

    def reset(self):
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        # Generate a path from top to bottom
        path = [(0, COLS//2)]
        cy, cx = 0, COLS//2
        for _ in range(ROWS * 2):
            opts = []
            for d in [2, 1, 3, 0]:  # prefer down
                ny, nx = cy + DY[d], cx + DX[d]
                if 0 <= ny < ROWS and 0 <= nx < COLS and (ny, nx) not in path[-5:]:
                    opts.append((ny, nx, d))
            if not opts:
                break
            ny, nx, d = random.choice(opts[:3] or opts)
            path.append((ny, nx))
            cy, cx = ny, nx
            if ny == ROWS - 1:
                break
        self.path = path
        # Place pipes along path with correct rotation, then scramble
        for i, (y, x) in enumerate(path):
            if i == 0:
                kind = random.choice([0, 1])
                self.grid[y][x] = Pipe(kind, 0)
            else:
                py, px = path[i-1]
                incoming = ( (py - y) * 2 + (px - x) )  # rough
                # set kind and rot so it connects
                self.grid[y][x] = Pipe(random.choice([0,1,1,2]), random.randint(0,3))
        # Fill rest randomly
        for y in range(ROWS):
            for x in range(COLS):
                if self.grid[y][x] is None:
                    self.grid[y][x] = Pipe(random.choice([0,1,1,2,3]), random.randint(0,3))
        # Scramble all rotations
        for y in range(ROWS):
            for x in range(COLS):
                for _ in range(random.randint(0, 3)):
                    self.grid[y][x].rotate()
        self.flow_y, self.flow_x = 0, COLS // 2
        self.flow_dir = 2  # down
        self.progress = 0.0
        self.score = 0
        self.leaks = 0
        self.selected = (2, COLS//2)
        self.time = 0.0
        self.particles = []

    def step_flow(self, dt):
        self.progress += dt * 1.8
        while self.progress >= 1.0:
            self.progress -= 1.0
            y, x = self.flow_y, self.flow_x
            pipe = self.grid[y][x]
            if pipe is None or not pipe.has((self.flow_dir + 2) % 4):
                self.leaks += 1
                self.score = max(0, self.score - 5)
                # restart flow near top
                self.flow_y, self.flow_x = 0, random.randint(1, COLS-2)
                self.flow_dir = 2
                continue
            # choose exit
            exits = [d for d in pipe.openings() if d != (self.flow_dir + 2) % 4]
            if not exits:
                self.leaks += 1
                self.flow_y, self.flow_x = 0, random.randint(1, COLS-2)
                self.flow_dir = 2
                continue
            out = random.choice(exits)
            ny = y + DY[out]
            nx = x + DX[out]
            if not (0 <= ny < ROWS and 0 <= nx < COLS):
                self.score += 25
                self.flow_y, self.flow_x = 0, random.randint(1, COLS-2)
                self.flow_dir = 2
                continue
            self.flow_y, self.flow_x = ny, nx
            self.flow_dir = out
            self.score += 10
            self.particles.append([x * CELL + OX + CELL//2, y * CELL + OY + CELL//2, random.uniform(-1,1), random.uniform(0.5,2), 1.0])

    def ai_act(self):
        # Rotate pipes near the flow head to try to connect
        y, x = int(self.flow_y), int(self.flow_x)
        for dy in range(0, 3):
            for dx in range(-1, 2):
                ny, nx = y + dy, x + dx
                if 0 <= ny < ROWS and 0 <= nx < COLS:
                    if random.random() < 0.15:
                        self.grid[ny][nx].rotate()

    def draw_pipe(self, surf, y, x, pipe, sel=False):
        cx = OX + x * CELL + CELL // 2
        cy = OY + y * CELL + CELL // 2
        r = 28
        col = CYAN if not sel else GOLD
        ops = pipe.openings()
        for d in ops:
            dx, dy = DX[d], DY[d]
            pygame.draw.line(surf, col, (cx, cy), (cx + dx * (CELL//2 - 4), cy + dy * (CELL//2 - 4)), 10)
        pygame.draw.circle(surf, col, (cx, cy), 12)
        if sel:
            pygame.draw.rect(surf, GOLD, (OX + x*CELL + 4, OY + y*CELL + 4, CELL-8, CELL-8), 3)

    def draw(self, surf):
        surf.fill(BG)
        # grid bg
        for y in range(ROWS):
            for x in range(COLS):
                pygame.draw.rect(surf, DIM, (OX + x*CELL, OY + y*CELL, CELL-2, CELL-2), 1)
                self.draw_pipe(surf, y, x, self.grid[y][x], (y, x) == self.selected)
        # flow head
        fx = OX + self.flow_x * CELL + CELL // 2
        fy = OY + self.flow_y * CELL + CELL // 2
        pygame.draw.circle(surf, MAG, (int(fx), int(fy)), 18)
        pygame.draw.circle(surf, WHITE, (int(fx), int(fy)), 8)
        # particles
        for p in self.particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 0.03
            if p[4] > 0:
                pygame.draw.circle(surf, MAG, (int(p[0]), int(p[1])), int(4 * p[4]))
            else:
                self.particles.remove(p)
        # HUD
        t = self.font.render(TITLE, True, GOLD)
        surf.blit(t, (W//2 - t.get_width()//2, 40))
        sc = self.sfont.render(f"SCORE {self.score}", True, CYAN)
        surf.blit(sc, (W//2 - sc.get_width()//2, 140))
        h = self.tiny.render(HANDLE, True, WHITE)
        surf.blit(h, (W//2 - h.get_width()//2, H - 80))
        if self.leaks:
            lk = self.tiny.render(f"LEAKS {self.leaks}", True, ORANGE)
            surf.blit(lk, (40, 200))

    def play_interactive(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_LEFT, pygame.K_a):
                        y, x = self.selected
                        self.selected = (y, max(0, x-1))
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        y, x = self.selected
                        self.selected = (y, min(COLS-1, x+1))
                    elif e.key in (pygame.K_UP, pygame.K_w):
                        y, x = self.selected
                        self.selected = (max(0, y-1), x)
                    elif e.key in (pygame.K_DOWN, pygame.K_s):
                        y, x = self.selected
                        self.selected = (min(ROWS-1, y+1), x)
                    elif e.key == pygame.K_SPACE:
                        y, x = self.selected
                        self.grid[y][x].rotate()
                    elif e.key == pygame.K_r:
                        self.reset()
            self.step_flow(dt)
            self.draw(self.screen)
            pygame.display.flip()
        pygame.quit()

    def record(self):
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
            "-i", "-", "-an", "-vcodec", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-movflags", "+faststart", OUT
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frames = FPS * SECS
        for i in range(frames):
            dt = 1.0 / FPS
            self.time += dt
            if i % 8 == 0:
                self.ai_act()
            # occasional select move for visual
            if i % 20 == 0:
                self.selected = (random.randint(0, ROWS-1), random.randint(0, COLS-1))
            self.step_flow(dt)
            self.draw(self.screen)
            raw = pygame.image.tostring(self.screen, "RGB")
            try:
                proc.stdin.write(raw)
            except BrokenPipeError:
                break
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1500:]}")
        print("wrote", OUT)
        pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()
