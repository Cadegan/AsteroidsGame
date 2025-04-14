import pygame
import math
import random
from collections import deque

# Configuration initiale
PLAYER_LIVES = 5  # Nombre de vies initiales
INVULNERABILITY_DURATION = 2000  # 2 secondes en ms
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SPEED = 0.5
BULLET_SPEED = 7
MAX_SPEED = 5  # Nouvelle constante de vitesse max
PARTICLE_LIFETIME = 40
PARTICLE_START_COLOR = (0, 0, 255)  # Bleu
PARTICLE_END_COLOR = (255, 160, 0)    # Jaune-orange
PARTICLE_MAX_SIZE = 5
ASTEROID_COLORS = [(180,180,180), (140,140,140), (100,100,100)]
ASTEROID_SPAWN_INTERVAL = (5000, 10000)  # 5-10s en ms

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
        
        # Limitation de la vitesse
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
        points = [
            (self.x + math.cos(self.angle) * 20, self.y + math.sin(self.angle) * 20),
            (self.x + math.cos(self.angle + 2.5) * 15, self.y + math.sin(self.angle + 2.5) * 15),
            (self.x + math.cos(self.angle - 2.5) * 15, self.y + math.sin(self.angle - 2.5) * 15)
        ]
        pygame.draw.polygon(screen, color, points, 2)
        
        # Ajout des particules de propulsion
        if keys[pygame.K_UP] or keys[pygame.K_DOWN]:
            for _ in range(3):
                angle_variation = random.uniform(-0.3, 0.3)
                particle = {
                    'x': self.x - math.cos(self.angle)*25,
                    'y': self.y - math.sin(self.angle)*25,
                    'vx': math.cos(self.angle + math.pi + angle_variation)*random.uniform(1,3),
                    'vy': math.sin(self.angle + math.pi + angle_variation)*random.uniform(1,3),
                    'life': PARTICLE_LIFETIME,
                    'size': random.randint(2, PARTICLE_MAX_SIZE)
                }
                particles.append(particle)

class Asteroid:
    def __init__(self, size=3, x=None, y=None):
        self.size = size
        self.radius = size * 10
        self.x = x if x else random.randint(0, SCREEN_WIDTH)
        self.y = y if y else random.randint(0, SCREEN_HEIGHT)
        speed_factor = 2 ** (3 - self.size)
        self.velocity_x = random.uniform(-2, 2) * speed_factor
        self.velocity_y = random.uniform(-2, 2) * speed_factor
        self.color = random.choice(ASTEROID_COLORS)
        self.rotation = 0
        self.num_points = 10
        self.points = self.generate_shape()
    
    def generate_shape(self):
        angle_step = math.pi * 2 / self.num_points
        points = []
        angles = [random.uniform(i*angle_step, (i+1)*angle_step) for i in range(self.num_points)]
        angles.sort()
        
        for angle in angles:
            radius = self.radius * random.uniform(0.7, 1.3)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            points.append((x, y))
        
        # Fermer le polygone
        points.append(points[0])
        return points
    
    def update(self):
        self.x = (self.x + self.velocity_x) % SCREEN_WIDTH
        self.y = (self.y + self.velocity_y) % SCREEN_HEIGHT
        self.rotation += 0.01
        
    def draw(self, screen):
        # Appliquer la rotation et la position
        rotated_points = [
            (
                self.x + math.cos(self.rotation) * x - math.sin(self.rotation) * y,
                self.y + math.sin(self.rotation) * x + math.cos(self.rotation) * y
            )
            for (x, y) in self.points
        ]
        # Remplissage
        pygame.draw.polygon(screen, self.color, rotated_points, 0)
        # Contour
        pygame.draw.polygon(screen, (200,200,200), rotated_points, 2)
        
    def split(self):
        if self.size > 1:
            return [Asteroid(self.size-1, self.x, self.y) for _ in range(2)]
        return []

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

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroids")
    clock = pygame.time.Clock()
    
    while True:
        player = Player()
        asteroids = [Asteroid() for _ in range(5)]
        bullets = []
        particles = deque(maxlen=100)
        last_spawn_time = pygame.time.get_ticks()
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Tirer un projectile
                        bullet = {
                            'x': player.x,
                            'y': player.y,
                            'dx': math.cos(player.angle) * BULLET_SPEED,
                            'dy': math.sin(player.angle) * BULLET_SPEED,
                            'life': 60,
                            'color': (0, 255, 0)  # Vert
                        }
                        bullets.append(bullet)
        
            current_time = pygame.time.get_ticks()
            # Génération aléatoire d'astéroïdes
            if current_time - last_spawn_time > random.randint(*ASTEROID_SPAWN_INTERVAL):
                asteroids.append(Asteroid())
                last_spawn_time = current_time
        
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
        
            if check_player_collision(player, asteroids):
                player.lives -= 1
                player.last_hit_time = current_time
                player.shield_active = True
                player.shield_end_time = current_time + 3000  # 3 secondes
                particles.extend(create_explosion(player.x, player.y, color=(255, 50, 50)))  # Rouge
                particles.extend(create_explosion(player.x, player.y, color=(255, 50, 50)))  # Rouge
                
                if player.lives <= 0:
                    running = False
        
            # Mise à jour des particules
            new_particles = []
            for p in particles:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['life'] -= 1
                if p['life'] > 0:
                    new_particles.append(p)
            particles = deque(new_particles, maxlen=100)
        
            # Dessin
            screen.fill((0,0,0))
            player.draw(screen, keys, particles)
            for asteroid in asteroids:
                asteroid.draw(screen)
            for bullet in bullets:
                pygame.draw.circle(screen, bullet['color'], (int(bullet['x']), int(bullet['y'])), 2)
            for p in particles:
                if 'color' in p:
                    color = p['color']
                else:
                    life_ratio = p['life'] / PARTICLE_LIFETIME
                    color_factor = (1 - life_ratio) ** 0.3
                    color = (
                        int(PARTICLE_START_COLOR[0] + (PARTICLE_END_COLOR[0] - PARTICLE_START_COLOR[0]) * color_factor),
                        int(PARTICLE_START_COLOR[1] + (PARTICLE_END_COLOR[1] - PARTICLE_START_COLOR[1]) * color_factor),
                        int(PARTICLE_START_COLOR[2] + (PARTICLE_END_COLOR[2] - PARTICLE_START_COLOR[2]) * color_factor)
                    )
                pygame.draw.circle(screen, color, (int(p['x']), int(p['y'])), int(p['size'] * (p['life']/PARTICLE_LIFETIME)))
        
            # Affichage des vies et du score
            font = pygame.font.Font(None, 36)
            lives_text = font.render(f'Vies: {player.lives}', True, (255,255,255))
            screen.blit(lives_text, (10, 10))
            score_text = font.render(f'Score: {player.score}', True, (255,255,255))
            screen.blit(score_text, (10, 50))
        
            pygame.display.flip()
            clock.tick(60)
    
        if not show_game_over(screen):
            break
    
    pygame.quit()

if __name__ == "__main__":
    main()
