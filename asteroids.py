import os
os.environ['PYGBAG_DEBUG'] = '1'
os.environ['PYGBAG_ARCHIVE'] = 'https://github.com/pygame-web/builds/releases/download/0.9/'

import pygame
import math
import random
from collections import deque
import itertools

# Configuration initiale
PLAYER_LIVES = 3  # Nombre de vies initiales
MAX_LIVES = 5     # Nombre de vies maximum
INVULNERABILITY_DURATION = 2000  # 2 secondes en ms
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SPEED = 0.3  # Accélération du vaisseau (réduit)
BULLET_SPEED = 7
MAX_SPEED = 3       # Vitesse max du vaisseau (réduit)
PARTICLE_LIFETIME = 40
PARTICLE_START_COLOR = (0, 0, 255)  # Bleu
PARTICLE_END_COLOR = (255, 160, 0)    # Jaune-orange
PARTICLE_MAX_SIZE = 5
ASTEROID_COLORS = [(180,180,180), (140,140,140), (100,100,100)]
ASTEROID_SPAWN_INTERVAL = (5000, 10000)  # 5-10s en ms
STAR_COUNT = 120
STAR_BASE_COLORS = [  # Types spectraux plus doux
    (240,240,255),   # Blanc doux
    (255,235,120),   # Jaune pâle
    (255,120,120),   # Rouge doux
    (140,180,255),   # Bleu pâle
]

# --- Power-ups ---
POWERUP_TYPES = [
    'life',         # Vie supplémentaire
    'triple_shot',  # Tir triple temporaire
    'invincible',   # Invincibilité temporaire
    'slowmo',       # Ralentissement du temps temporaire
    'laser',        # Rayon laser destructeur temporaire
    'bomb',         # Bombe de déflagration
]
POWERUP_COLORS = {
    'life': (0,255,0),
    'triple_shot': (0,200,255),
    'invincible': (255,255,0),
    'slowmo': (180,100,255),
    'laser': (255, 50, 200),
    'bomb': (255, 120, 0),
}
POWERUP_RADIUS = 14
POWERUP_DURATION = {
    'triple_shot': 10000,   # ms
    'invincible': 5000,     # ms
    'slowmo': 5000,         # ms
    'laser': 3000,          # ms
    # bomb: effet immédiat
}

class Player:
    def __init__(self):
        self.x = SCREEN_WIDTH/2
        self.y = SCREEN_HEIGHT/2
        self.angle = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.lives = PLAYER_LIVES
        self.last_hit_time = 0
        self.shield_active = False
        self.shield_end_time = 0
        self.score = 0
        
    def update(self):
        current_time = pygame.time.get_ticks()
        if self.shield_active and current_time > self.shield_end_time:
            self.shield_active = False
        
        # Limitation de la vitesse (plus lisible)
        self.velocity_x = max(-MAX_SPEED, min(MAX_SPEED, self.velocity_x))
        self.velocity_y = max(-MAX_SPEED, min(MAX_SPEED, self.velocity_y))
        self.x = (self.x + self.velocity_x) % SCREEN_WIDTH
        self.y = (self.y + self.velocity_y) % SCREEN_HEIGHT
        
    def draw(self, screen, keys, particles):
        current_time = pygame.time.get_ticks()
        if self.shield_active:
            shield_radius = 35
            time_left = self.shield_end_time - current_time
            alpha = int(100 * (time_left / 3000))
            shield_surface = pygame.Surface((shield_radius*2, shield_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surface, (0, 150, 255, alpha), (shield_radius, shield_radius), shield_radius, 5)
            screen.blit(shield_surface, (int(self.x - shield_radius), int(self.y - shield_radius)))
            
            # Affichage du chrono
            if time_left > 0:
                font = pygame.font.Font(None, 24)
                text = font.render(f"Bouclier: {time_left//1000}s", True, (0, 150, 255))
                text_rect = text.get_rect(center=(self.x, self.y - 50))
                screen.blit(text, text_rect)
        
        # Dessiner le vaisseau
        color = (255, 255, 255) if not self.shield_active else (200, 200, 255)
        points = self._get_ship_points()
        pygame.draw.polygon(screen, color, points, 2)
        
        # Ajout des particules de propulsion (list comprehension)
        if keys[pygame.K_UP] or keys[pygame.K_DOWN]:
            particles.extend([
                {
                    'x': self.x - math.cos(self.angle) * 25,
                    'y': self.y - math.sin(self.angle) * 25,
                    'vx': math.cos(self.angle + math.pi + random.uniform(-0.3, 0.3)) * random.uniform(1, 3),
                    'vy': math.sin(self.angle + math.pi + random.uniform(-0.3, 0.3)) * random.uniform(1, 3),
                    'life': PARTICLE_LIFETIME,
                    'size': random.randint(2, PARTICLE_MAX_SIZE)
                }
                for _ in range(3)
            ])
        
    def _get_ship_points(self):
        # Factorisation du calcul des points du vaisseau
        return [
            (self.x + math.cos(self.angle) * 20, self.y + math.sin(self.angle) * 20),
            (self.x + math.cos(self.angle + 2.5) * 15, self.y + math.sin(self.angle + 2.5) * 15),
            (self.x + math.cos(self.angle - 2.5) * 15, self.y + math.sin(self.angle - 2.5) * 15)
        ]

class Asteroid:
    def __init__(self, size=3, x=None, y=None):
        self.size = size
        self.radius = size * 10
        self.x = x if x is not None else random.randint(0, SCREEN_WIDTH)
        self.y = y if y is not None else random.randint(0, SCREEN_HEIGHT)
        if self.size == 3:
            speed_factor = 2
        elif self.size == 2:
            speed_factor = 1.2
        else:
            speed_factor = 0.7
        vx = random.uniform(-2, 2) * speed_factor
        vy = random.uniform(-2, 2) * speed_factor
        self.base_velocity_x = vx  # Vitesse d'origine
        self.base_velocity_y = vy
        self.velocity_x = vx
        self.velocity_y = vy
        self.color = random.choice(ASTEROID_COLORS)
        self.rotation = 0
        self.num_points = 10
        self.points = self.generate_shape()

    def generate_shape(self):
        # Génère un contour irrégulier RELATIF au centre (0,0)
        angle_step = 2 * math.pi / self.num_points
        return [
            (
                math.cos(i * angle_step) * self.radius * random.uniform(0.8, 1.2),
                math.sin(i * angle_step) * self.radius * random.uniform(0.8, 1.2)
            )
            for i in range(self.num_points)
        ]

    def update(self):
        self.x = (self.x + self.velocity_x) % SCREEN_WIDTH
        self.y = (self.y + self.velocity_y) % SCREEN_HEIGHT

    def draw(self, screen):
        # Dessine l'astéroïde à la position (self.x, self.y)
        points = [
            (self.x + px, self.y + py)
            for (px, py) in self.points
        ]
        if points:
            points.append(points[0])  # Ferme le polygone
        # Remplissage
        pygame.draw.polygon(screen, self.color, points)
        # Contour (optionnel, couleur plus claire)
        pygame.draw.polygon(screen, (200, 200, 200), points, 2)

    def split(self):
        """Divise l'astéroïde en deux plus petits si possible."""
        if self.size > 1:
            return [Asteroid(self.size - 1, self.x, self.y) for _ in range(2)]
        return []

class PowerUp:
    _id_iter = itertools.count()
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.color = POWERUP_COLORS[type]
        self.radius = POWERUP_RADIUS
        self.spawn_time = pygame.time.get_ticks()
        self.id = next(PowerUp._id_iter)
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        font = pygame.font.Font(None, 22)
        initials = {
            'life': 'V',          # Vie
            'triple_shot': 'T',  # Tir triple
            'invincible': 'B',   # Bouclier
            'slowmo': 'R',       # Ralenti
            'laser': 'L',        # Laser
            'bomb': 'B',         # Bombe
        }
        symbol = initials[self.type]
        text = font.render(symbol, True, (30,30,30))
        rect = text.get_rect(center=(self.x, self.y))
        screen.blit(text, rect)

class FloatingText:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.opacity = 255
        self.lifetime = 1200  # ms
        self.start_time = pygame.time.get_ticks()
    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        self.y -= 0.7  # Slide vers le haut
        self.opacity = max(0, 255 - int(255 * (elapsed / self.lifetime)))
        return elapsed < self.lifetime
    def draw(self, screen):
        font = pygame.font.Font(None, 34)
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(self.opacity)
        rect = surf.get_rect(center=(self.x, self.y))
        screen.blit(surf, rect)

def check_collision(obj1, obj2):
    dx = obj1['x'] - obj2.x
    dy = obj1['y'] - obj2.y
    return math.sqrt(dx**2 + dy**2) < 30

def check_player_collision(player, asteroids):
    current_time = pygame.time.get_ticks()
    if player.shield_active or current_time - player.last_hit_time < INVULNERABILITY_DURATION:
        return False
    
    collision = False
    for asteroid in list(asteroids):
        dx = player.x - asteroid.x
        dy = player.y - asteroid.y
        distance = math.hypot(dx, dy)
        if distance < asteroid.radius + 25:
            asteroids.remove(asteroid)
            asteroids.extend(asteroid.split())
            collision = True
    return collision

def show_game_over(screen):
    font = pygame.font.Font(None, 74)
    text = font.render('GAME OVER', True, (255, 0, 0))
    text_rect = text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50))
    
    font_small = pygame.font.Font(None, 36)
    restart_text = font_small.render('Appuyez sur R pour rejouer', True, (255,255,255))
    restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 50))
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
        
        screen.fill((0,0,0))
        screen.blit(text, text_rect)
        screen.blit(restart_text, restart_rect)
        pygame.display.flip()
        pygame.time.Clock().tick(60)

def create_explosion(x, y, color=(255, 255, 0)):
    return [
        {
            'x': x + random.uniform(-20,20),
            'y': y + random.uniform(-20,20),
            'vx': random.uniform(-5,5),
            'vy': random.uniform(-5,5),
            'life': PARTICLE_LIFETIME,
            'size': random.randint(3,6),
            'color': color
        }
        for _ in range(50)
    ]

def generate_stars():
    # Majorité de petites étoiles, quelques grandes
    sizes = [1]*65 + [2]*35 + [3]*15 + [4]*5  # 120 étoiles
    random.shuffle(sizes)
    # Parallaxe : plus la taille est grande, plus la vitesse est grande (valeurs réduites pour plus de lisibilité)
    size_to_speed = {1: 0.08, 2: 0.15, 3: 0.25, 4: 0.4}
    return [
        {
            'x': random.randint(0, SCREEN_WIDTH),
            'y': random.randint(0, SCREEN_HEIGHT),
            'radius': sizes[i],
            'color': random_star_color(),
            'speed': size_to_speed[sizes[i]]
        }
        for i in range(STAR_COUNT)
    ]

def draw_stars(screen, stars, player):
    # Parallaxe : décale les étoiles selon la vitesse du joueur et leur profondeur
    for star in stars:
        # Décalage en fonction de la vitesse du joueur
        star['x'] = (star['x'] - player.velocity_x * star['speed']) % SCREEN_WIDTH
        star['y'] = (star['y'] - player.velocity_y * star['speed']) % SCREEN_HEIGHT
        pygame.draw.circle(screen, star['color'], (int(star['x']), int(star['y'])), star['radius'])

def random_star_color():
    base = random.choice(STAR_BASE_COLORS)
    # Variation plus faible pour garder la couleur vive
    return tuple(
        max(0, min(255, c + random.randint(-8, 8)))
        for c in base
    )

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroids")
    clock = pygame.time.Clock()
    running = True
    bomb_active = False
    bomb_radius = 0
    bomb_center = (0,0)
    bomb_start_time = 0
    BOMB_MAX_RADIUS = 450  # Plus grand rayon
    BOMB_DURATION = 1200   # Plus lent (ms)
    while running:
        # --- Initialisation d'une nouvelle partie ---
        player = Player()
        player.laser = False  # Toujours initialiser l'attribut laser
        bullets = []
        # --- Système de niveaux ---
        score = 0
        level = 1
        asteroids = [Asteroid() for _ in range(3)]  # Lvl 1 = 3 astéroïdes
        particles = deque(maxlen=300)
        stars = generate_stars()  # Génération du fond étoilé
        last_spawn_time = pygame.time.get_ticks()
        powerups = []
        floating_texts = []
        game_over = False
        # Activation du bouclier au démarrage
        now = pygame.time.get_ticks()
        player.invincible = True
        player.shield_active = True
        player.shield_end_time = now + POWERUP_DURATION['invincible']
        player.powerup_timers = {'invincible': now + POWERUP_DURATION['invincible']}
        # --- Boucle de jeu ---
        while not game_over:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    game_over = True
            
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Tirer un projectile
                        if getattr(player, 'triple_shot', False):
                            spread = [-0.18, 0, 0.18]
                            for s in spread:
                                bullet = {
                                    'x': player.x,
                                    'y': player.y,
                                    'dx': math.cos(player.angle+s) * BULLET_SPEED,
                                    'dy': math.sin(player.angle+s) * BULLET_SPEED,
                                    'life': 60,
                                    'color': (0, 255, 0)
                                }
                                bullets.append(bullet)
                        else:
                            bullet = {
                                'x': player.x,
                                'y': player.y,
                                'dx': math.cos(player.angle) * BULLET_SPEED,
                                'dy': math.sin(player.angle) * BULLET_SPEED,
                                'life': 60,
                                'color': (0, 255, 0)
                            }
                            bullets.append(bullet)
        
            current_time = pygame.time.get_ticks()
            # Génération aléatoire d'astéroïdes
            if current_time - last_spawn_time > random.randint(*ASTEROID_SPAWN_INTERVAL):
                asteroids.append(Asteroid())
                last_spawn_time = current_time
        
            # Respawn rapide des astéroïdes si trop peu
            # --- Système de niveau et ajustement du nombre d'astéroïdes ---
            level = 1 + player.score // 1000
            min_asteroids = 3 + (level - 1)
            asteroids_target = min_asteroids
            if len(asteroids) < min_asteroids:
                for _ in range(asteroids_target - len(asteroids)):
                    asteroids.append(Asteroid())
        
            # Contrôles
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                player.angle -= 0.1
            if keys[pygame.K_RIGHT]:
                player.angle += 0.1
            if keys[pygame.K_UP]:
                player.velocity_x += math.cos(player.angle) * PLAYER_SPEED
                player.velocity_y += math.sin(player.angle) * PLAYER_SPEED
            if keys[pygame.K_DOWN]:  # Nouveau contrôle de décélération
                player.velocity_x -= math.cos(player.angle) * PLAYER_SPEED
                player.velocity_y -= math.sin(player.angle) * PLAYER_SPEED
        
            # Mise à jour des entités
            player.update()
            for asteroid in asteroids:
                asteroid.update()
        
            # Mise à jour des balles
            for bullet in list(bullets):  # Copie pour itération safe
                bullet['x'] += bullet['dx']
                bullet['y'] += bullet['dy']
                # Ajout de particules de traînée
                for _ in range(3):
                    particles.append({
                        'x': bullet['x'] + random.uniform(-2,2),
                        'y': bullet['y'] + random.uniform(-2,2),
                        'vx': bullet['dx'] * 0.3 + random.uniform(-0.5,0.5),
                        'vy': bullet['dy'] * 0.3 + random.uniform(-0.5,0.5),
                        'life': 25,
                        'size': 3,
                        'color': (random.randint(0,50), 255, random.randint(0,50))
                    })
                bullet['life'] -= 1
                if bullet['life'] <= 0:
                    bullets.remove(bullet)
        
            # Gestion des collisions balles/astéroïdes
            for bullet in list(bullets):
                for asteroid in list(asteroids):
                    if check_collision(bullet, asteroid):
                        if bullet in bullets:
                            bullets.remove(bullet)
                        if asteroid in asteroids:
                            asteroids.remove(asteroid)
                            player.score += 10 * asteroid.size  # Incrémentation
                            asteroids.extend(asteroid.split())
                            particles.extend(create_explosion(asteroid.x, asteroid.y, color=(255, 200, 0)))  # Jaune-orangé
                            particles.extend(create_explosion(asteroid.x, asteroid.y, color=(255, 200, 0)))  # Jaune-orangé
                            if random.random() < 0.15:
                                pu_type = random.choice(POWERUP_TYPES)
                                powerups.append(PowerUp(asteroid.x, asteroid.y, pu_type))
        
            if check_player_collision(player, asteroids):
                player.lives -= 1
                player.last_hit_time = current_time
                player.shield_active = True
                player.shield_end_time = current_time + 3000  # 3 secondes
                particles.extend([
                    {**p, 'life_loss': True} for p in create_explosion(player.x, player.y, color=(255, 50, 50))
                ])
                particles.extend([
                    {**p, 'life_loss': True} for p in create_explosion(player.x, player.y, color=(255, 50, 50))
                ])
                if player.lives <= 0:
                    game_over = True
        
            # Mise à jour des particules
            new_particles = []
            for p in particles:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['life'] -= 1
                if p['life'] > 0:
                    new_particles.append(p)
            particles = deque(new_particles, maxlen=300)
        
            # --- Gestion des power-ups actifs sur le joueur ---
            if not hasattr(player, 'powerup_timers'):
                player.powerup_timers = {}
                player.triple_shot = False
                player.invincible = False
                player.slowmo = False
                player.laser = False
            now = pygame.time.get_ticks()
            # Désactivation des effets temporaires
            for ptype, endtime in list(player.powerup_timers.items()):
                if now > endtime:
                    if ptype == 'triple_shot': player.triple_shot = False
                    if ptype == 'invincible': player.invincible = False
                    if ptype == 'slowmo': player.slowmo = False
                    if ptype == 'laser': player.laser = False
                    del player.powerup_timers[ptype]

            # --- Gestion de la collecte ---
            for pu in list(powerups):
                dx = player.x - pu.x
                dy = player.y - pu.y
                if dx*dx + dy*dy < (pu.radius+20)**2:
                    if pu.type == 'life':
                        if player.lives < MAX_LIVES:
                            player.lives += 1
                            floating_texts.append(FloatingText('Vie +1', player.x, player.y-40, POWERUP_COLORS['life']))
                        # Si déjà au max, pas de vie ajoutée ni de texte
                    elif pu.type in POWERUP_DURATION:
                        # Prolonge la durée si déjà actif
                        player.powerup_timers[pu.type] = now + POWERUP_DURATION[pu.type]
                        if pu.type == 'triple_shot':
                            player.triple_shot = True
                            floating_texts.append(FloatingText('Tir triple', player.x, player.y-40, POWERUP_COLORS['triple_shot']))
                        if pu.type == 'invincible':
                            player.invincible = True
                            player.shield_active = True
                            player.shield_end_time = now + POWERUP_DURATION['invincible']
                            floating_texts.append(FloatingText('Bouclier', player.x, player.y-40, POWERUP_COLORS['invincible']))
                        if pu.type == 'slowmo':
                            player.slowmo = True
                            floating_texts.append(FloatingText('Ralenti', player.x, player.y-40, POWERUP_COLORS['slowmo']))
                        if pu.type == 'laser':
                            player.laser = True
                            floating_texts.append(FloatingText('Laser', player.x, player.y-40, POWERUP_COLORS['laser']))
                    elif pu.type == 'bomb':
                        bomb_active = True
                        bomb_radius = 0
                        bomb_center = (player.x, player.y)
                        bomb_start_time = pygame.time.get_ticks()
                        floating_texts.append(FloatingText('Bombe', player.x, player.y-40, POWERUP_COLORS['bomb']))
                    powerups.remove(pu)

            # --- Animation et effet de la bombe ---
            if bomb_active:
                elapsed = pygame.time.get_ticks() - bomb_start_time
                progress = min(1.0, elapsed / BOMB_DURATION)
                ease = progress ** 0.5  # Courbe exponentielle (ease-out)
                bomb_radius = int(BOMB_MAX_RADIUS * ease)
                # Destruction des astéroïdes dans le rayon
                for asteroid in list(asteroids):
                    ax, ay = asteroid.x, asteroid.y
                    if (ax-bomb_center[0])**2 + (ay-bomb_center[1])**2 < bomb_radius**2:
                        asteroids.remove(asteroid)
                        player.score += 20  # Score réduit, comme le laser
                        particles.extend(create_explosion(ax, ay, color=(255, 140, 0)))
                # Fin de l'effet
                if elapsed > BOMB_DURATION:
                    bomb_active = False

            # --- Application du slowmo (sans effet permanent) ---
            slowmo_factor = 0.4 if getattr(player, 'slowmo', False) else 1.0
            for asteroid in asteroids:
                asteroid.velocity_x = asteroid.base_velocity_x * slowmo_factor
                asteroid.velocity_y = asteroid.base_velocity_y * slowmo_factor
            # (Les projectiles NE SONT PAS ralentis)
            # Les power-ups flottants pourraient aussi être ralentis ici si besoin

            # --- Mise à jour et affichage des textes flottants ---
            floating_texts = [ft for ft in floating_texts if ft.update()]

            # --- Dessin ---
            screen.fill((0, 0, 10))  # Fond très sombre
            draw_stars(screen, stars, player)  # Dessine les étoiles avec parallaxe
            for asteroid in asteroids:
                asteroid.draw(screen)
            player.draw(screen, keys, particles)
            for bullet in bullets:
                pygame.draw.circle(screen, (0, 255, 0), (int(bullet['x']), int(bullet['y'])), 3)  # Vert vif, taille 3
            for p in particles:
                # Si la particule vient de la perte de vie, on force la couleur rouge
                if p.get('life_loss'):
                    color = (255, 0, 0)
                else:
                    color_factor = p['life'] / PARTICLE_LIFETIME
                    color = (
                        int(PARTICLE_START_COLOR[0] + (PARTICLE_END_COLOR[0] - PARTICLE_START_COLOR[0]) * color_factor),
                        int(PARTICLE_START_COLOR[1] + (PARTICLE_END_COLOR[1] - PARTICLE_START_COLOR[1]) * color_factor),
                        int(PARTICLE_START_COLOR[2] + (PARTICLE_END_COLOR[2] - PARTICLE_START_COLOR[2]) * color_factor)
                    )
                pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), int(p['size'] * (p['life']/PARTICLE_LIFETIME)))
            for pu in powerups:
                pu.draw(screen)
            for ft in floating_texts:
                ft.draw(screen)

            # Affichage des vies, du score et du niveau
            font = pygame.font.Font(None, 36)
            text = font.render(f"Vies: {player.lives}", True, (255, 255, 255))
            screen.blit(text, (10, 10))
            text = font.render(f"Score: {player.score}", True, (255, 255, 0))
            screen.blit(text, (10, 50))
            text = font.render(f"Niveau: {level}", True, (255, 180, 0))
            screen.blit(text, (10, 90))

            # --- Affichage des chronos de bonus actifs (toujours au-dessus) ---
            bonus_y = 140  # Décalé sous le texte du niveau
            for ptype, end in player.powerup_timers.items():
                left = max(0, (end-now)//1000)
                txt = {'triple_shot': 'Tir triple', 'invincible': 'Bouclier', 'slowmo': 'Ralenti', 'laser': 'Laser'}[ptype]
                color = POWERUP_COLORS[ptype]
                font = pygame.font.Font(None, 32)
                timer_str = f'{txt}: {left}s'
                text = font.render(timer_str, True, color)
                bg_rect = text.get_rect(topleft=(10, bonus_y))
                pygame.draw.rect(screen, (10,10,10), bg_rect.inflate(8,4))
                screen.blit(text, (14, bonus_y+2))
                bonus_y += 36

            # --- Affichage du laser au-dessus de tout ---
            laser_params = None
            if player.laser:
                # Prépare les paramètres pour dessiner le rayon après tous les éléments
                laser_length = 900
                laser_width = 12  # plus large et très visible
                lx = player.x + math.cos(player.angle) * 20
                ly = player.y + math.sin(player.angle) * 20
                lx2 = lx + math.cos(player.angle) * laser_length
                ly2 = ly + math.sin(player.angle) * laser_length
                laser_params = (lx, ly, lx2, ly2, laser_width)
                # Détection de collision avec les astéroïdes
                for asteroid in list(asteroids):
                    ax, ay = asteroid.x, asteroid.y
                    px, py = lx, ly
                    dx, dy = lx2 - lx, ly2 - ly
                    if dx == dy == 0:
                        dist = math.hypot(ax-px, ay-py)
                    else:
                        t = max(0, min(1, ((ax-px)*dx + (ay-py)*dy) / (dx*dx + dy*dy)))
                        closest_x = px + t*dx
                        closest_y = py + t*dy
                        dist = math.hypot(ax-closest_x, ay-closest_y)
                    if dist < asteroid.radius+laser_width//2:
                        asteroids.remove(asteroid)
                        # Score réduit pour le laser
                        player.score += 10
                        particles.extend(create_explosion(ax, ay, color=(255, 0, 200)))

            # --- Affichage du laser (rose, très visible, halo/glow accentués) ---
            if laser_params:
                lx, ly, lx2, ly2, laser_width = laser_params
                laser_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                # Trait principal rose vif
                pygame.draw.line(laser_surf, (255,60,220,255), (lx,ly), (lx2,ly2), laser_width)
                # Halo magenta clair très large
                pygame.draw.line(laser_surf, (255,120,255,100), (lx,ly), (lx2,ly2), laser_width+18)
                # Glow violet/blanc plus diffus
                pygame.draw.line(laser_surf, (180,80,255,60), (lx,ly), (lx2,ly2), laser_width+36)
                # Un petit contour blanc pour l'éclat
                pygame.draw.line(laser_surf, (255,255,255,70), (lx,ly), (lx2,ly2), laser_width+6)
                screen.blit(laser_surf, (0,0))

            # --- Affichage de la bombe (cercle animé) ---
            if bomb_active:
                bomb_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                # Cercle extérieur lumineux (halo)
                pygame.draw.circle(bomb_surf, (255,200,60,110), bomb_center, bomb_radius, 5)
                # Optionnel : un second cercle plus diffus
                pygame.draw.circle(bomb_surf, (255,140,0,50), bomb_center, bomb_radius+12, 2)
                screen.blit(bomb_surf, (0,0))

            pygame.display.flip()
            clock.tick(60)

        # --- Affiche l'écran de Game Over et attend une action ---
        if show_game_over(screen):
            continue
        else:
            running = False

    pygame.quit()

if __name__ == "__main__":
    main()
