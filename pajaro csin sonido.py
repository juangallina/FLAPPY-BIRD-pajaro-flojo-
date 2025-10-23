import pygame, sys, os, json, random, math
from collections import deque

pygame.init()
ANCHO, ALTO = 480, 720
VENTANA = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Pajaro Flojo - Menú Integrado")
FPS = 60

# Fuentes
FUENTE = pygame.font.SysFont("Showcard Gothic", 20)
FUENTE_GRANDE = pygame.font.SysFont("Showcard Gothic", 38, bold=True)

# Colores
BLANCO = (255,255,255)
NEGRO = (0,0,0)
CELESTE = (95,165,255)
VERDE = (60,180,75)
ROJO = (214,70,70)
AMARILLO = (245,200,60)
AZUL = (80,140,210)
GRIS = (160,160,160)

DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"highscore":0, "last_scores":[], "skin":"amarillo", "difficulty":"Normal"}, f)

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

data = load_data()

# --------------------
# UI Button
# --------------------
class Button:
    def __init__(self, text, x, y, w, h, col, col_hover, action=None):
        self.text = text
        self.rect = pygame.Rect(x,y,w,h)
        self.col = col
        self.col_hover = col_hover
        self.action = action
    def draw(self, surf):
        mouse = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mouse)
        color = self.col_hover if hover else self.col
        pygame.draw.rect(surf, color, self.rect, border_radius=10)
        txt = FUENTE.render(self.text, True, NEGRO)
        surf.blit(txt, txt.get_rect(center=self.rect.center))
    def click(self, pos):
        if self.rect.collidepoint(pos) and self.action:
            self.action()

# --------------------
# Bird
# --------------------
class Bird:
    def __init__(self, x, y, skin="amarillo"):
        self.x = x
        self.y = y
        self.vy = 0.0
        self.radius = 18
        self.time = 0.0
        self.skin = skin
        self.alive = True
    def flap(self):
        self.vy = -9.5
    def update(self, dt):
        self.time += dt
        g = 0.6
        self.vy += g
        self.y += self.vy
    def draw(self, surf):
        colors = {
            "amarillo": (245,200,60),
            "rojo": (214,70,70),
            "azul": (80,140,210),
            "verde": (60,180,75),
            "rainbow": None
        }
        body_col = colors.get(self.skin, (245,200,60))
        body_rect = pygame.Rect(0,0, self.radius*2+6, int(self.radius*1.4))
        surf_body = pygame.Surface(body_rect.size, pygame.SRCALPHA)
        if self.skin == "rainbow":
            bands = [(245,70,70),(245,140,60),(245,200,60),(80,180,100),(60,140,220)]
            for i,c in enumerate(bands):
                r = int(body_rect.height*(1 - i*0.12))
                pygame.draw.ellipse(surf_body, c, pygame.Rect(0+i*2, i*2, body_rect.width-i*4, r))
        else:
            pygame.draw.ellipse(surf_body, body_col, pygame.Rect(0,0,body_rect.width,body_rect.height))
        pygame.draw.circle(surf_body, BLANCO, (int(body_rect.width*0.68), int(body_rect.height*0.3)), max(2, self.radius//6))
        pygame.draw.circle(surf_body, NEGRO, (int(body_rect.width*0.73), int(body_rect.height*0.3)), max(1, self.radius//9))
        pygame.draw.polygon(surf_body, (255,160,40), [(int(body_rect.width*0.9), int(body_rect.height*0.45)), (int(body_rect.width*1.12), int(body_rect.height*0.5)), (int(body_rect.width*0.9), int(body_rect.height*0.6))])
        wing_offset = math.sin(self.time*12) * 6
        pygame.draw.ellipse(surf_body, (220,160,80), pygame.Rect(int(body_rect.width*0.12), int(body_rect.height*0.5+wing_offset), int(body_rect.width*0.9), int(body_rect.height*0.9)))
        rotated = pygame.transform.rotate(surf_body, int(self.vy*3))
        surf.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))
    @property
    def rect(self):
        return pygame.Rect(int(self.x-self.radius), int(self.y-self.radius), self.radius*2, self.radius*2)

# --------------------
# Tube
# --------------------
class Tube:
    WIDTH = 84
    def __init__(self, x, gap_y, gap_h):
        self.x = x
        self.gap_y = gap_y
        self.gap_h = gap_h
        self.passed = False
    def update(self, speed):
        self.x -= speed
    def draw(self, surf):
        top_h = int(self.gap_y - self.gap_h//2)
        bot_y = int(self.gap_y + self.gap_h//2)
        pygame.draw.rect(surf, (60,160,60), (int(self.x), 0, self.WIDTH, top_h))
        pygame.draw.rect(surf, (60,160,60), (int(self.x), bot_y, self.WIDTH, ALTO - bot_y))
        pygame.draw.rect(surf, (30,110,30), (int(self.x), max(0,top_h-12), self.WIDTH, 12))
        pygame.draw.rect(surf, (30,110,30), (int(self.x), bot_y, self.WIDTH, 12))
    def collides(self, bird: Bird):
        br = bird.rect
        top_rect = pygame.Rect(int(self.x), 0, self.WIDTH, int(self.gap_y - self.gap_h/2))
        bot_rect = pygame.Rect(int(self.x), int(self.gap_y + self.gap_h/2), self.WIDTH, ALTO - int(self.gap_y + self.gap_h/2))
        return br.colliderect(top_rect) or br.colliderect(bot_rect)

# --------------------
# Play logic
# --------------------
def play_game():
    global data
    clock = pygame.time.Clock()
    diff = data.get("difficulty","Normal")
    if diff == "Easy":
        gap = 200; speed = 3.6; spawn_interval = 1.8
    elif diff == "Hard":
        gap = 150; speed = 5.0; spawn_interval = 1.1
    else:
        gap = 175; speed = 4.2; spawn_interval = 1.4

    bird = Bird(ANCHO*0.28, ALTO*0.5, skin=data.get("skin","amarillo"))
    tubes = []
    spawn_timer = 0.0
    score = 0
    running = True
    game_over = False
    ground_y = ALTO - 80

    while running:
        dt = clock.tick(FPS) / 1000.0
        spawn_timer += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if not game_over: bird.flap()
                    else: return score
                if event.key == pygame.K_ESCAPE:
                    return score
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not game_over: bird.flap()

        if not game_over:
            bird.update(dt)
            if spawn_timer >= spawn_interval:
                spawn_timer = 0.0
                margin = 120
                gap_y = random.randint(margin + gap//2, ALTO - margin - gap//2 - 80)
                tubes.append(Tube(ANCHO + 20, gap_y, gap))
            for t in tubes:
                t.update(speed)
                if (not t.passed) and (bird.x > t.x + Tube.WIDTH):
                    t.passed = True
                    score += 1
            tubes = [t for t in tubes if t.x + Tube.WIDTH > -50]
            for t in tubes:
                if t.collides(bird):
                    game_over = True
                    bird.alive = False
            if bird.y - bird.radius < 0:
                bird.y = bird.radius
                bird.vy = 0
            if bird.y + bird.radius > ground_y:
                game_over = True
                bird.alive = False

        # DRAW
        VENTANA.fill(CELESTE)
        for i in range(3):
            cx = (i*200 + pygame.time.get_ticks()*0.02) % (ANCHO+120) - 60
            pygame.draw.ellipse(VENTANA, (255,255,255,50), (cx, 60 + i*40, 140, 40))
        for t in tubes:
            t.draw(VENTANA)
        pygame.draw.rect(VENTANA, (90,60,40), (0, ground_y, ANCHO, ALTO-ground_y))
        bird.draw(VENTANA)
        srf = FUENTE_GRANDE.render(str(score), True, BLANCO)
        VENTANA.blit(srf, (ANCHO//2 - srf.get_width()//2, 28))
        if game_over:
            over = FUENTE_GRANDE.render("¡PERDISTE!", True, ROJO)
            VENTANA.blit(over, (ANCHO//2 - over.get_width()//2, ALTO//2 - 20))
            tip = FUENTE.render("Pulsa ESPACIO para reiniciar o ESC para salir", True, BLANCO)
            VENTANA.blit(tip, (ANCHO//2 - tip.get_width()//2, ALTO//2 + 36))

        pygame.display.flip()

# --------------------
# Menus y estados
# --------------------
state = "menu"
clock = pygame.time.Clock()
def set_state(s): global state; state = s

def main_menu_buttons():
    return [
        Button("Jugar", ANCHO//2-110, 220, 220, 48, VERDE, AMARILLO, lambda: set_state("play")),
        Button("Skins", ANCHO//2-110, 290, 220, 48, AZUL, AMARILLO, lambda: set_state("skins")),
        Button("Récords", ANCHO//2-110, 360, 220, 48, GRIS, AMARILLO, lambda: set_state("records")),
        Button("Opciones", ANCHO//2-110, 430, 220, 48, GRIS, AMARILLO, lambda: set_state("options")),
        Button("Salir", ANCHO//2-110, 500, 220, 48, ROJO, AMARILLO, lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)))
    ]

def skins_buttons():
    x = ANCHO//2 - 110
    return [
        Button("Amarillo", x, 220, 220, 44, AMARILLO, BLANCO, lambda: choose_skin("amarillo")),
        Button("Rojo", x, 280, 220, 44, ROJO, BLANCO, lambda: choose_skin("rojo")),
        Button("Azul", x, 340, 220, 44, AZUL, BLANCO, lambda: choose_skin("azul")),
        Button("Verde", x, 400, 220, 44, VERDE, BLANCO, lambda: choose_skin("verde")),
        Button("Rainbow", x, 460, 220, 44, (255,130,130), BLANCO, lambda: choose_skin("rainbow")),
        Button("Volver", x, 520, 220, 44, GRIS, AMARILLO, lambda: set_state("menu"))
    ]

def records_buttons():
    return [Button("Volver", ANCHO//2-110, ALTO-140, 220, 44, GRIS, AMARILLO, lambda: set_state("menu"))]

def options_buttons():
    return [
        Button(f"Dificultad: {data.get('difficulty','Normal')}", ANCHO//2-110, 290, 220, 44, GRIS, AMARILLO, toggle_difficulty),
        Button("Volver", ANCHO//2-110, ALTO-140, 220, 44, GRIS, AMARILLO, lambda:set_state("menu"))
    ]

def choose_skin(name):
    global data
    data["skin"] = name
    save_data(data)
    set_state("menu")

def toggle_difficulty():
    cur = data.get("difficulty","Normal")
    order = ["Easy","Normal","Hard"]
    i = (order.index(cur)+1) % len(order)
    data["difficulty"] = order[i]
    save_data(data)
    set_state("options")

# --------------------
# Main loop
# --------------------
def main():
    global state, data
    botones = main_menu_buttons()

    while True:
        clock.tick(FPS)
        VENTANA.fill(CELESTE)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                for b in botones:
                    b.click(pos)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state != "menu":
                    set_state("menu")

        if state == "menu":
            t = (pygame.time.get_ticks() * 0.002) % (2*math.pi)
            title_y = 110 + math.sin(t)*8
            txt = FUENTE_GRANDE.render("PÁJARO FLOJO", True, BLANCO)
            VENTANA.blit(txt, (ANCHO//2 - txt.get_width()//2, int(title_y)))
            subtitle = FUENTE.render("Espacio/Click para aletear  •  ESC: menú", True, BLANCO)
            VENTANA.blit(subtitle, (ANCHO//2 - subtitle.get_width()//2, 170))
            botones = main_menu_buttons()
            for b in botones:
                b.draw(VENTANA)

        elif state == "play":
            sc = play_game()
            data = load_data()
            if sc > data.get("highscore",0):
                data["highscore"] = sc
            ls = deque(data.get("last_scores",[]), maxlen=10)
            ls.appendleft(sc)
            data["last_scores"] = list(ls)[:10]
            save_data(data)
            state = "menu"

        elif state == "skins":
            txt = FUENTE_GRANDE.render("Skins", True, BLANCO)
            VENTANA.blit(txt, (ANCHO//2 - txt.get_width()//2, 110))
            botones = skins_buttons()
            for b in botones:
                b.draw(VENTANA)

        elif state == "records":
            data = load_data()
            txt = FUENTE_GRANDE.render("Récords", True, BLANCO)
            VENTANA.blit(txt, (ANCHO//2 - txt.get_width()//2, 40))
            hs = FUENTE.render(f"Highscore: {data.get('highscore',0)}", True, BLANCO)
            VENTANA.blit(hs, (ANCHO//2 - hs.get_width()//2, 120))
            last = data.get("last_scores",[])
            for i, s in enumerate(last[:5]):
                sc_txt = FUENTE.render(f"{i+1}. {s}", True, BLANCO)
                VENTANA.blit(sc_txt, (ANCHO//2 - sc_txt.get_width()//2, 160 + i*30))
            botones = records_buttons()
            for b in botones:
                b.draw(VENTANA)

        elif state == "options":
            txt = FUENTE_GRANDE.render("Opciones", True, BLANCO)
            VENTANA.blit(txt, (ANCHO//2 - txt.get_width()//2, 110))
            botones = options_buttons()
            for b in botones:
                b.draw(VENTANA)

        pygame.display.flip()

if __name__ == "__main__":
    main()
