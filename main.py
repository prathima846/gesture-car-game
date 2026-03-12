import os
os.environ['SDL_VIDEO_WINDOW_POS'] = "420,0"
import pygame
import sys
import cv2
import mediapipe as mp
import random
import math

pygame.init()

# ---------------------------
# SCREEN
# ---------------------------
WIDTH  = 1000
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gesture Controlled Car Game")
clock = pygame.time.Clock()

# ---------------------------
# LOAD IMAGES
# ---------------------------
background       = pygame.image.load("background.png")
background       = pygame.transform.scale(background, (WIDTH, HEIGHT))
car_img          = pygame.image.load("car.png")
car_img          = pygame.transform.scale(car_img, (120, 70))
obstacle_img     = pygame.image.load("obstacle.png")
obstacle_img     = pygame.transform.scale(obstacle_img, (55, 55))
air_obstacle_img = pygame.transform.scale(obstacle_img, (50, 50))

# ---------------------------
# CONSTANTS
# ---------------------------
CAR_WIDTH     = 120
CAR_HEIGHT    = 70
OBSTACLE_SIZE = 55
AIR_OBS_SIZE  = 50
GROUND_LEVEL  = 405
AIR_OBS_Y     = GROUND_LEVEL - 155

COIN_RADIUS      = 13
COIN_COLOR       = (255, 215, 0)
COIN_SHINE_COLOR = (255, 255, 180)

# ---------------------------
# SPEED SETTINGS
# ---------------------------
INITIAL_SPEED   = 9.0
MAX_SPEED       = 16.0
SPEED_INCREMENT = 0.005

# ---------------------------
# NEON COLOR PALETTE
# ---------------------------
NEON_CYAN    = (0, 255, 255)
NEON_PINK    = (255, 0, 180)
NEON_YELLOW  = (255, 230, 0)
NEON_GREEN   = (0, 255, 120)
NEON_ORANGE  = (255, 140, 0)
NEON_PURPLE  = (180, 0, 255)
NEON_BLUE    = (0, 140, 255)
DARK_BG      = (8, 8, 20)
CARD_BG      = (15, 15, 35)

# ---------------------------
# FONTS
# ---------------------------
font       = pygame.font.SysFont("Consolas", 28, bold=True)
small_font = pygame.font.SysFont("Consolas", 20)
hint_font  = pygame.font.SysFont("Consolas", 16)
big_font   = pygame.font.SysFont("Consolas", 46, bold=True)
title_font = pygame.font.SysFont("Consolas", 52, bold=True)
menu_font  = pygame.font.SysFont("Consolas", 18, bold=True)
card_font  = pygame.font.SysFont("Consolas", 16)

# ---------------------------
# SCREENS
# ---------------------------
SCREEN_MENU    = "menu"
SCREEN_PLAYING = "playing"
current_screen = SCREEN_MENU

# ---------------------------
# PARTICLE SYSTEM
# ---------------------------
class Particle:
    def __init__(self, x, y, color, vel_x=None, vel_y=None, size=None, life=None):
        self.x     = float(x)
        self.y     = float(y)
        self.color = color
        self.vx    = vel_x if vel_x is not None else random.uniform(-3, 3)
        self.vy    = vel_y if vel_y is not None else random.uniform(-5, -1)
        self.size  = size  if size  is not None else random.randint(3, 7)
        self.life  = life  if life  is not None else random.randint(30, 60)
        self.max_life = self.life

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.vy   += 0.15   # gravity
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = int(255 * (self.life / self.max_life))
        r = max(1, int(self.size * (self.life / self.max_life)))
        col = (*self.color[:3], alpha)
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, col, (r, r), r)
        surface.blit(surf, (int(self.x) - r, int(self.y) - r))

particles = []

def burst_particles(x, y, color, count=18):
    for _ in range(count):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 7)
        particles.append(Particle(
            x, y, color,
            vel_x=math.cos(angle) * speed,
            vel_y=math.sin(angle) * speed - 2,
            size=random.randint(3, 8),
            life=random.randint(25, 50)
        ))

def exhaust_particles(x, y):
    """Car exhaust trail"""
    for _ in range(2):
        particles.append(Particle(
            x, y,
            random.choice([(180, 180, 200), (120, 120, 150), (200, 200, 220)]),
            vel_x=random.uniform(-3, -1),
            vel_y=random.uniform(-1, 1),
            size=random.randint(2, 5),
            life=random.randint(15, 30)
        ))

# ---------------------------
# GLOW HELPER
# ---------------------------
def draw_glow(surface, color, x, y, radius, intensity=80):
    for r in range(radius, 0, -8):
        alpha = int(intensity * (1 - r / radius) ** 2)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (r, r), r)
        surface.blit(s, (x - r, y - r))

def draw_glow_rect(surface, color, rect, radius=8, intensity=60):
    pad = 12
    for i in range(4):
        alpha = int(intensity * (1 - i / 4) ** 2)
        s = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha),
                         (i, i, rect.width + pad * 2 - i * 2, rect.height + pad * 2 - i * 2),
                         border_radius=radius + 2)
        surface.blit(s, (rect.x - pad, rect.y - pad))

def draw_neon_text(surface, text, font_obj, color, x, y, center=True, glow_strength=3):
    """Draw text with neon glow effect"""
    # Glow layers
    for g in range(glow_strength, 0, -1):
        alpha = int(80 * (1 - g / glow_strength))
        glow_surf = font_obj.render(text, True, (*color, alpha))
        glow_surf.set_alpha(alpha)
        gx = x - glow_surf.get_width() // 2 - g if center else x - g
        gy = y - g
        surface.blit(glow_surf, (gx, gy))
        gx = x - glow_surf.get_width() // 2 + g if center else x + g
        surface.blit(glow_surf, (gx, gy + g))
    # Main text
    surf = font_obj.render(text, True, color)
    tx = x - surf.get_width() // 2 if center else x
    surface.blit(surf, (tx, y))
    return surf

# ---------------------------


# ---------------------------
# ANIMATED SCANLINES
# ---------------------------
scanline_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for y in range(0, HEIGHT, 3):
    pygame.draw.line(scanline_surf, (0, 0, 0, 25), (0, y), (WIDTH, y))

# ---------------------------
# COIN CLASS
# ---------------------------
class Coin:
    def __init__(self, x):
        self.x      = float(x)
        self.y      = float(GROUND_LEVEL - COIN_RADIUS - 4)
        self.active = True
        self.anim   = random.uniform(0, math.pi * 2)

    def update(self, speed):
        self.x   -= speed
        self.anim += 0.12
        if self.x < -COIN_RADIUS * 2:
            self.active = False

    def draw(self, surface):
        if not self.active:
            return
        pulse = int(1.5 * math.sin(self.anim))
        r = COIN_RADIUS + pulse
        # Glow
        draw_glow(surface, COIN_COLOR, int(self.x), int(self.y), r + 8, intensity=60)
        pygame.draw.circle(surface, COIN_COLOR,       (int(self.x), int(self.y)), r)
        pygame.draw.circle(surface, COIN_SHINE_COLOR, (int(self.x) - r // 3, int(self.y) - r // 3), r // 3)
        pygame.draw.circle(surface, (200, 160, 0),    (int(self.x), int(self.y)), r, 2)

    def get_rect(self):
        r = COIN_RADIUS
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)


# ---------------------------
# OBSTACLE CLASS
# ---------------------------
class Obstacle:
    def __init__(self, x, is_air=False):
        self.x      = float(x)
        self.is_air = is_air
        self.y      = float(AIR_OBS_Y if is_air else GROUND_LEVEL - OBSTACLE_SIZE)
        self.passed = False
        self.active = True
        self.size   = AIR_OBS_SIZE if is_air else OBSTACLE_SIZE
        self.warn_alpha = 0   # warning flash when approaching

    def update(self, speed):
        self.x -= speed
        dist = self.x - 200
        if 0 < dist < 300:
            self.warn_alpha = int(120 * (1 - dist / 300))
        else:
            self.warn_alpha = 0
        if self.x < -self.size - 20:
            self.active = False

    def draw(self, surface):
        # Warning glow when approaching
        if self.warn_alpha > 0:
            draw_glow(surface, NEON_ORANGE,
                      int(self.x + self.size // 2),
                      int(self.y + self.size // 2),
                      self.size + 20, intensity=self.warn_alpha)

        img = air_obstacle_img if self.is_air else obstacle_img
        surface.blit(img, (int(self.x), int(self.y)))

        # Red danger outline when close
        if self.warn_alpha > 60:
            r = pygame.Rect(int(self.x), int(self.y), self.size, self.size)
            pygame.draw.rect(surface, (*NEON_ORANGE, self.warn_alpha), r, 2, border_radius=4)

    def get_rect(self):
        pad = 10
        return pygame.Rect(int(self.x) + pad, int(self.y) + pad,
                           self.size - pad * 2, self.size - pad * 2)


# ---------------------------
# SPAWN LOGIC
# ---------------------------
def next_gap(speed):
    base = 700 + int(speed * 30)
    return random.randint(base, base + 400)

def spawn_wave(obstacles, coins, from_x, speed):
    gap = next_gap(speed)
    ox  = from_x + gap
    obstacles.append(Obstacle(ox, is_air=False))
    rightmost = ox
    if random.random() < 0.20:
        air_offset = random.randint(180, 320)
        obstacles.append(Obstacle(ox + air_offset, is_air=True))
        rightmost  = ox + air_offset
    n_coins      = random.randint(3, 5)
    coin_start   = from_x + gap // 4
    coin_spacing = (gap // 2) // max(n_coins, 1)
    for i in range(n_coins):
        coins.append(Coin(coin_start + i * coin_spacing))
    return rightmost

# ---------------------------
# GAME STATE
# ---------------------------
def make_initial_state():
    obs = []
    cns = []
    rx  = WIDTH + 500
    for _ in range(3):
        rx = spawn_wave(obs, cns, rx, INITIAL_SPEED)
    return obs, cns, rx

obstacles, coins, last_spawn_x = make_initial_state()

car_x        = 100
car_y        = float(GROUND_LEVEL - CAR_HEIGHT)
car_velocity = 0.0
gravity      = 0.75
jump_power   = -19.0

bg_x           = 0.0
bg_speed       = INITIAL_SPEED * 0.7
obstacle_speed = INITIAL_SPEED

score           = 0
hi_score        = 0
coins_collected = 0
frames_alive    = 0
game_time       = 0   # for animations

game_started = False
game_paused  = False
game_over    = False
popups       = []

# Game over animation
go_scale     = 0.0
go_alpha     = 0

# ---------------------------
# MENU DRAW
# ---------------------------
def draw_hand(surface, cx, cy, fingers, color, scale=1.0):
    palm_w = int(50 * scale)
    palm_h = int(40 * scale)
    palm_x = cx - palm_w // 2
    palm_y = cy + int(55 * scale)

    # Palm with glow
    pygame.draw.rect(surface, color, (palm_x, palm_y, palm_w, palm_h), border_radius=int(8 * scale))
    dark = tuple(max(0, c - 80) for c in color)

    finger_configs = [
        (-28, 10,  10, 50, 22),
        (-16,  0,  10, 58, 22),
        ( -5, -5,  10, 62, 22),
        (  6,  0,  10, 55, 22),
        ( 17,  8,  10, 44, 18),
    ]

    for i, (ox, oy, fw, fh_up, fh_down) in enumerate(finger_configs):
        fh = int((fh_up if fingers[i] else fh_down) * scale)
        fw = int(fw * scale)
        fx = palm_x + palm_w // 2 + int(ox * scale) - fw // 2
        fy = palm_y + int(oy * scale) - fh
        pygame.draw.rect(surface, color, (fx, fy, fw, fh), border_radius=int(5 * scale))
        pygame.draw.rect(surface, dark,  (fx, fy, fw, fh), 1, border_radius=int(5 * scale))

def draw_menu(surface, t):
    # Use the actual game background slowly scrolling
    menu_bg_x = int((t * 0.5) % WIDTH)
    surface.blit(background, (-menu_bg_x, 0))
    surface.blit(background, (WIDTH - menu_bg_x, 0))

    # Dark overlay so cards/text are readable
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 155))
    surface.blit(overlay, (0, 0))

    # Top neon glow bar
    glow_bar = pygame.Surface((WIDTH, 3), pygame.SRCALPHA)
    glow_bar.fill((*NEON_YELLOW, 200))
    surface.blit(glow_bar, (0, 0))

    # Title with neon glow — pulsing
    pulse = 0.85 + 0.15 * math.sin(t * 0.04)
    tc = tuple(int(c * pulse) for c in NEON_YELLOW)
    draw_neon_text(surface, "GESTURE  CAR  GAME", title_font, tc, WIDTH // 2, 22, glow_strength=5)

    # Subtitle
    sub_alpha = int(160 + 60 * math.sin(t * 0.03))
    sub = hint_font.render("Master your hand gestures to control the car", True, (200, 230, 200))
    sub.set_alpha(sub_alpha)
    surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 88))

    # Gesture cards
    gestures = [
        ("OPEN HAND",  "Start / Resume", [1,1,1,1,1], NEON_GREEN,  (10, 35, 20)),
        ("PEACE SIGN", "Jump",           [0,1,1,0,0], NEON_BLUE,   (10, 20, 45)),
        ("FIST",       "Pause",          [0,0,0,0,0], NEON_ORANGE, (45, 20, 5)),
        ("POINT UP",   "Restart",        [0,1,0,0,0], NEON_PURPLE, (35, 5,  50)),
        ("THUMBS UP",  "Exit Game",      [1,0,0,0,0], NEON_PINK,   (50, 5,  25)),
    ]

    card_w  = 158
    card_h  = 210
    spacing = 16
    total_w = len(gestures) * card_w + (len(gestures) - 1) * spacing
    start_x = (WIDTH - total_w) // 2
    card_y  = 108

    for i, (name, action, fingers, color, bg) in enumerate(gestures):
        cx   = start_x + i * (card_w + spacing)
        # Staggered float animation
        float_y = int(4 * math.sin(t * 0.04 + i * 0.8))
        cy = card_y + float_y

        card_rect = pygame.Rect(cx, cy, card_w, card_h)

        # Card glow
        draw_glow_rect(surface, color, card_rect, radius=12, intensity=50)

        # Card background
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((*bg, 230))
        surface.blit(card_surf, (cx, cy))

        # Card border (neon)
        pygame.draw.rect(surface, color, card_rect, 2, border_radius=12)

        # Inner top accent line
        pygame.draw.rect(surface, (*color, 120),
                         (cx + 2, cy + 2, card_w - 4, 3), border_radius=2)

        # Hand drawing
        hand_surf = pygame.Surface((card_w, 130), pygame.SRCALPHA)
        draw_hand(hand_surf, card_w // 2, -10, fingers, color, scale=0.9)
        surface.blit(hand_surf, (cx, cy + 8))

        # Divider
        pygame.draw.line(surface, (*color, 100),
                         (cx + 12, cy + card_h - 68),
                         (cx + card_w - 12, cy + card_h - 68), 1)

        # Gesture name
        draw_neon_text(surface, name, menu_font, color,
                       cx + card_w // 2, cy + card_h - 62, glow_strength=2)

        # Action
        act = card_font.render(action, True, (190, 210, 230))
        surface.blit(act, (cx + card_w // 2 - act.get_width() // 2, cy + card_h - 36))

    # Pulsing start prompt
    prompt_pulse = int(200 + 55 * math.sin(t * 0.05))
    prompt_color = (prompt_pulse, prompt_pulse, 80)
    draw_neon_text(surface, ">> Show OPEN HAND to Start <<",
                   font, prompt_color, WIDTH // 2, card_y + card_h + 22, glow_strength=3)

    # Hi score
    if hi_score > 0:
        hs = small_font.render(f"BEST: {hi_score}", True, NEON_YELLOW)
        surface.blit(hs, (WIDTH // 2 - hs.get_width() // 2, card_y + card_h + 60))

    # Bottom scanlines
    surface.blit(scanline_surf, (0, 0))

    # Bottom bar
    pygame.draw.line(surface, (*NEON_CYAN, 120), (0, HEIGHT - 1), (WIDTH, HEIGHT - 1), 2)


# ---------------------------
# HUD DRAW
# ---------------------------
def draw_hud(surface, stable_gesture, obstacle_speed, score, hi_score, coins_collected):
    # Left panel — semi-transparent
    panel = pygame.Surface((220, 70), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    surface.blit(panel, (10, 8))
    pygame.draw.rect(surface, (*NEON_CYAN, 80), (10, 8, 220, 70), 1, border_radius=6)

    g_surf = font.render(f"GESTURE: {stable_gesture}", True, NEON_CYAN)
    surface.blit(g_surf, (18, 14))

    # Speed bar
    spd_pct = max(0, (obstacle_speed - INITIAL_SPEED) / (MAX_SPEED - INITIAL_SPEED))
    bar_x, bar_y, bar_w, bar_h = 18, 50, 160, 10
    pygame.draw.rect(surface, (30, 30, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=5)
    if spd_pct > 0:
        fill_color = (
            int(50 + 200 * spd_pct),
            int(220 - 150 * spd_pct),
            50
        )
        pygame.draw.rect(surface, fill_color,
                         (bar_x, bar_y, int(bar_w * spd_pct), bar_h), border_radius=5)
        draw_glow_rect(surface, fill_color,
                       pygame.Rect(bar_x, bar_y, int(bar_w * spd_pct), bar_h),
                       radius=5, intensity=40)
    spd_label = hint_font.render(f"SPEED  {obstacle_speed:.1f}", True, (150, 180, 200))
    surface.blit(spd_label, (bar_x + bar_w + 6, bar_y - 2))

    # Right panel
    r_panel = pygame.Surface((200, 90), pygame.SRCALPHA)
    r_panel.fill((0, 0, 0, 120))
    surface.blit(r_panel, (WIDTH - 210, 8))
    pygame.draw.rect(surface, (*NEON_YELLOW, 80), (WIDTH - 210, 8, 200, 90), 1, border_radius=6)

    sc_surf = font.render(f"SCORE  {score}", True, NEON_YELLOW)
    surface.blit(sc_surf, (WIDTH - sc_surf.get_width() - 18, 14))

    hi_surf = small_font.render(f"BEST   {hi_score}", True, (180, 180, 100))
    surface.blit(hi_surf, (WIDTH - hi_surf.get_width() - 18, 48))

    coin_surf = small_font.render(f"COINS  {coins_collected}", True, COIN_COLOR)
    surface.blit(coin_surf, (WIDTH - coin_surf.get_width() - 18, 72))


# ---------------------------
# MEDIAPIPE
# ---------------------------
cap = cv2.VideoCapture(0)
cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Camera", 400, 600)
cv2.moveWindow("Camera", 0, 0)
mp_hands = mp.solutions.hands
hands    = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw  = mp.solutions.drawing_utils

# ---------------------------
# GESTURE STABILITY
# ---------------------------
prev_gesture        = "None"
gesture_count       = 0
stable_gesture      = "None"
last_stable_gesture = "None"
GESTURE_THRESHOLD   = 6

def detect_gesture(hand_landmarks):
    lm      = hand_landmarks.landmark
    fingers = [1 if lm[4].x > lm[3].x else 0]
    for tip in [8, 12, 16, 20]:
        fingers.append(1 if lm[tip].y < lm[tip - 2].y else 0)
    total = sum(fingers)
    if total == 5:                return "Start"
    if fingers == [0,1,1,0,0]:   return "Peace"
    if total == 0:                return "Stop"
    if fingers == [0,1,0,0,0]:   return "Restart"
    if fingers == [1,0,0,0,0]:   return "Exit"
    return "None"

# ---------------------------
# RESET
# ---------------------------
def reset_game():
    global car_x, car_y, car_velocity, score, coins_collected
    global obstacles, coins, last_spawn_x, game_started, game_paused, game_over
    global popups, obstacle_speed, frames_alive, bg_x, bg_speed
    global current_screen, particles, go_scale, go_alpha
    car_x           = 100
    car_y           = float(GROUND_LEVEL - CAR_HEIGHT)
    car_velocity    = 0.0
    score           = 0
    coins_collected = 0
    frames_alive    = 0
    obstacle_speed  = INITIAL_SPEED
    bg_speed        = INITIAL_SPEED * 0.7
    bg_x            = 0.0
    popups          = []
    particles       = []
    go_scale        = 0.0
    go_alpha        = 0
    obstacles, coins, last_spawn_x = make_initial_state()
    game_started   = True
    game_paused    = False
    game_over      = False
    current_screen = SCREEN_PLAYING

# ---------------------------
# MAIN LOOP
# ---------------------------
running = True
while running:
    clock.tick(60)
    game_time += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # -------- CAMERA --------
    ret, frame = cap.read()
    raw_gesture = "None"
    if ret:
        frame     = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results   = hands.process(frame_rgb)
        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)
                raw_gesture = detect_gesture(handLms)
        cv2.imshow("Camera", frame)
        cv2.waitKey(1)

    # -------- GESTURE STABILITY --------
    if raw_gesture == prev_gesture:
        gesture_count += 1
    else:
        gesture_count = 0
        prev_gesture  = raw_gesture

    if gesture_count >= GESTURE_THRESHOLD:
        last_stable_gesture = stable_gesture
        stable_gesture      = raw_gesture

    peace_triggered   = (stable_gesture == "Peace"   and last_stable_gesture != "Peace")
    stop_triggered    = (stable_gesture == "Stop"    and last_stable_gesture != "Stop")
    start_triggered   = (stable_gesture == "Start"   and last_stable_gesture != "Start")
    restart_triggered = (stable_gesture == "Restart" and last_stable_gesture != "Restart")

    # ==============================
    # MENU SCREEN
    # ==============================
    if current_screen == SCREEN_MENU:
        draw_menu(screen, game_time)

        # Live gesture indicator
        det_color = NEON_GREEN if stable_gesture != "None" else (100, 100, 100)
        det = hint_font.render(f"Detected: {stable_gesture}", True, det_color)
        screen.blit(det, (WIDTH // 2 - det.get_width() // 2, HEIGHT - 28))

        if stable_gesture == "Exit":
            running = False
        if start_triggered:
            current_screen = SCREEN_PLAYING
            game_started   = True

        pygame.display.update()
        continue

    # ==============================
    # PLAYING SCREEN
    # ==============================

    # -------- GESTURE ACTIONS --------
    if stable_gesture == "Exit":
        running = False
    if stop_triggered and game_started and not game_over:
        game_paused = True
    if start_triggered and game_paused:
        game_paused = False
    if restart_triggered:
        reset_game()

    # -------- JUMP --------
    is_on_ground = (car_y >= GROUND_LEVEL - CAR_HEIGHT - 2)
    if peace_triggered and is_on_ground and game_started and not game_paused and not game_over:
        car_velocity = jump_power
        # Jump particles
        for _ in range(8):
            particles.append(Particle(
                car_x + CAR_WIDTH // 2, car_y + CAR_HEIGHT,
                NEON_CYAN,
                vel_x=random.uniform(-2, 2),
                vel_y=random.uniform(1, 4),
                size=random.randint(2, 5), life=20
            ))

    # -------- PHYSICS --------
    active = game_started and not game_paused and not game_over

    if active:
        car_velocity += gravity
        car_y        += car_velocity
        if car_y >= GROUND_LEVEL - CAR_HEIGHT:
            car_y        = float(GROUND_LEVEL - CAR_HEIGHT)
            car_velocity = 0.0

        obstacle_speed = min(MAX_SPEED, obstacle_speed + SPEED_INCREMENT)
        bg_speed       = obstacle_speed * 0.7

        frames_alive += 1
        if frames_alive % 6 == 0:
            score += 1

        # Exhaust trail
        if frames_alive % 3 == 0:
            exhaust_particles(car_x - 5, car_y + CAR_HEIGHT - 15)

    # -------- BACKGROUND SCROLL --------
    if active:
        bg_x -= bg_speed
        if bg_x <= -WIDTH:
            bg_x = 0.0

    # -------- UPDATE OBSTACLES & COINS --------
    if active:
        car_rect = pygame.Rect(car_x + 12, int(car_y) + 10,
                               CAR_WIDTH - 24, CAR_HEIGHT - 14)

        for obs in obstacles:
            obs.update(obstacle_speed)
            if not obs.passed and obs.x + obs.size < car_x:
                obs.passed = True
                score += 5
                popups.append([car_x + CAR_WIDTH // 2, int(car_y) - 10, "+5", 50, NEON_GREEN])
                burst_particles(car_x + CAR_WIDTH, int(car_y) + CAR_HEIGHT // 2, NEON_GREEN, 12)
            if car_rect.colliderect(obs.get_rect()):
                game_over = True
                hi_score  = max(hi_score, score)
                burst_particles(car_x + CAR_WIDTH // 2, int(car_y) + CAR_HEIGHT // 2,
                                NEON_ORANGE, 35)

        obstacles = [o for o in obstacles if o.active]

        rightmost = max((o.x for o in obstacles), default=WIDTH + 100)
        while rightmost < WIDTH + 1800:
            last_spawn_x = spawn_wave(obstacles, coins, rightmost, obstacle_speed)
            rightmost    = last_spawn_x

        for coin in coins:
            coin.update(obstacle_speed)
            if coin.active and car_rect.colliderect(coin.get_rect()):
                coin.active      = False
                coins_collected += 1
                score           += 2
                popups.append([int(coin.x), int(coin.y) - 15, "+2", 40, COIN_COLOR])
                burst_particles(int(coin.x), int(coin.y), COIN_COLOR, 10)

        coins = [c for c in coins if c.active]

    # -------- PARTICLES --------
    particles[:] = [p for p in particles if p.update()]

    # -------- POPUPS --------
    popups = [[x, y, t, f - 1, c] for x, y, t, f, c in popups if f > 0]

    # -------- DRAW GAME --------
    screen.blit(background, (int(bg_x), 0))
    screen.blit(background, (int(bg_x) + WIDTH, 0))

    # Ground glow line
    glow_line = pygame.Surface((WIDTH, 6), pygame.SRCALPHA)
    glow_line.fill((*NEON_GREEN, 40))
    screen.blit(glow_line, (0, GROUND_LEVEL - 3))

    for coin in coins:
        coin.draw(screen)
    for obs in obstacles:
        obs.draw(screen)

    # Car glow
    draw_glow(screen, NEON_CYAN,
              car_x + CAR_WIDTH // 2, int(car_y) + CAR_HEIGHT // 2,
              50, intensity=30)
    screen.blit(car_img, (car_x, int(car_y)))

    # Particles
    for p in particles:
        p.draw(screen)

    # Floating popups
    for (px, py, txt, frames, col) in popups:
        draw_neon_text(screen, txt, small_font, col,
                       px, py - (50 - frames), glow_strength=2)

    # Scanlines on game too (subtle)
    screen.blit(scanline_surf, (0, 0))

    # HUD
    draw_hud(screen, stable_gesture, obstacle_speed, score, hi_score, coins_collected)

    # -------- PAUSE SCREEN --------
    if game_paused and not game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        draw_neon_text(screen, "PAUSED", big_font, NEON_YELLOW, WIDTH // 2, HEIGHT // 2 - 80, glow_strength=6)
        draw_neon_text(screen, "Show [Open Hand] to Resume", font, NEON_CYAN, WIDTH // 2, HEIGHT // 2, glow_strength=3)
        draw_neon_text(screen, "[Point] to Restart", hint_font, (160, 160, 200), WIDTH // 2, HEIGHT // 2 + 55, glow_strength=1)

    # -------- GAME OVER SCREEN --------
    if game_over:
        # Animate in
        go_alpha = min(160, go_alpha + 8)
        go_scale = min(1.0, go_scale + 0.05)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, go_alpha))
        screen.blit(overlay, (0, 0))

        # Flashing GAME OVER
        flash = int(200 + 55 * math.sin(game_time * 0.1))
        draw_neon_text(screen, "GAME  OVER", big_font, (flash, 50, 50),
                       WIDTH // 2, HEIGHT // 2 - 90, glow_strength=8)

        # Stats box
        box_w, box_h = 500, 80
        box_x = WIDTH // 2 - box_w // 2
        box_y = HEIGHT // 2 - 20
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box_surf.fill((20, 5, 5, 180))
        screen.blit(box_surf, (box_x, box_y))
        pygame.draw.rect(screen, (*NEON_PINK, 150), (box_x, box_y, box_w, box_h), 2, border_radius=8)

        draw_neon_text(screen, f"SCORE: {score}", font, NEON_YELLOW,
                       WIDTH // 2, box_y + 8, glow_strength=2)
        draw_neon_text(screen, f"BEST: {hi_score}   COINS: {coins_collected}", small_font,
                       (200, 200, 180), WIDTH // 2, box_y + 46, glow_strength=1)

        draw_neon_text(screen, "Show [Point Finger] to Restart", font,
                       NEON_CYAN, WIDTH // 2, HEIGHT // 2 + 75, glow_strength=3)

        # Particle burst on game over
        if game_time % 30 == 0:
            burst_particles(random.randint(200, 800),
                            random.randint(150, 400),
                            random.choice([NEON_PINK, NEON_ORANGE, NEON_YELLOW]), 8)

    pygame.display.update()

cap.release()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()