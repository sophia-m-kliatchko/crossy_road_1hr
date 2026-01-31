"""
Crossy Road Clone - A Python implementation using Pygame
Inspired by Crossy Road by Hipster Whale and the classic Frogger

Controls:
- UP ARROW or W: Move forward
- DOWN ARROW or S: Move backward  
- LEFT ARROW or A: Move left
- RIGHT ARROW or D: Move right
- SPACE: Restart after game over
- ESC: Quit game

Features:
- Procedurally generated infinite world
- Multiple terrain types: grass, roads, rivers, train tracks
- Obstacles: trees, cars, trucks, trains, water
- Logs and lily pads to cross rivers (variable speeds per lane)
- Cars move at variable speeds per lane
- Crossy Road style train signals
- Eagle catches you if idle too long
- Collectible coins
- High score tracking
"""

import pygame
import random
import math
import sys

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 50
FPS = 60

# Colors - Crossy Road inspired palette
COLORS = {
    'grass_light': (124, 185, 71),
    'grass_dark': (96, 163, 42),
    'road': (70, 70, 75),
    'road_lines': (255, 255, 255),
    'water': (64, 164, 223),
    'water_dark': (41, 128, 185),
    'log': (139, 90, 43),
    'log_dark': (101, 67, 33),
    'lily_pad': (34, 139, 34),
    'train_track': (80, 60, 40),
    'rail': (150, 150, 160),
    'chicken_body': (255, 255, 255),
    'chicken_beak': (255, 165, 0),
    'chicken_comb': (255, 0, 0),
    'car_red': (220, 50, 50),
    'car_blue': (50, 100, 200),
    'car_yellow': (255, 200, 50),
    'car_green': (50, 180, 80),
    'truck': (100, 100, 120),
    'train': (60, 60, 70),
    'train_front': (200, 50, 50),
    'tree_trunk': (101, 67, 33),
    'tree_leaves': (34, 120, 34),
    'tree_leaves_light': (50, 160, 50),
    'coin': (255, 215, 0),
    'coin_dark': (218, 165, 32),
    'eagle': (101, 67, 33),
    'eagle_wing': (139, 90, 43),
    'ui_bg': (0, 0, 0),
    'ui_text': (255, 255, 255),
}

# Lane types
LANE_GRASS = 0
LANE_ROAD = 1
LANE_WATER = 2
LANE_TRAIN = 3


class SoundManager:
    """Manages game sounds"""
    def __init__(self):
        self.enabled = True
        try:
            self.hop_sound = self._create_beep(600, 50)
            self.coin_sound = self._create_beep(880, 100)
            self.death_sound = self._create_beep(200, 200)
            self.splash_sound = self._create_beep(150, 150)
        except:
            self.enabled = False
    
    def _create_beep(self, frequency, duration_ms):
        sample_rate = 22050
        n_samples = int(sample_rate * duration_ms / 1000)
        buf = bytearray(n_samples * 2)
        for i in range(n_samples):
            val = int(16000 * math.sin(2 * math.pi * frequency * i / sample_rate))
            fade = 1 - (i / n_samples)
            val = int(val * fade)
            buf[i*2] = val & 0xff
            buf[i*2+1] = (val >> 8) & 0xff
        sound = pygame.mixer.Sound(buffer=bytes(buf))
        sound.set_volume(0.3)
        return sound
    
    def play_hop(self):
        if self.enabled: self.hop_sound.play()
    
    def play_coin(self):
        if self.enabled: self.coin_sound.play()
    
    def play_death(self):
        if self.enabled: self.death_sound.play()
    
    def play_splash(self):
        if self.enabled: self.splash_sound.play()


class Player:
    """The chicken player character"""
    def __init__(self, x, y):
        self.grid_x = x
        self.grid_y = y
        self.pixel_x = x * TILE_SIZE
        self.pixel_y = y * TILE_SIZE
        self.target_x = self.pixel_x
        self.target_y = self.pixel_y
        self.moving = False
        self.move_speed = 12
        self.direction = 0
        self.hop_height = 0
        self.hop_phase = 0
        self.alive = True
        self.on_log = None
        self.death_animation = 0
        self.death_type = None
        self.idle_time = 0
    
    def move(self, dx, dy, world, sound_manager):
        if self.moving or not self.alive:
            return False
        
        new_grid_x = self.grid_x + dx
        new_grid_y = self.grid_y + dy
        
        if new_grid_x < 0 or new_grid_x >= world.width:
            return False
        
        lane = world.get_lane(new_grid_y)
        if lane and lane.has_obstacle_at(new_grid_x):
            return False
        
        self.grid_x = new_grid_x
        self.grid_y = new_grid_y
        self.target_x = new_grid_x * TILE_SIZE
        self.target_y = new_grid_y * TILE_SIZE
        self.moving = True
        self.hop_phase = 0
        self.idle_time = 0
        
        if dy < 0: self.direction = 0
        elif dx > 0: self.direction = 1
        elif dy > 0: self.direction = 2
        elif dx < 0: self.direction = 3
        
        sound_manager.play_hop()
        return True
    
    def update(self, dt):
        if not self.alive:
            self.death_animation += dt
            return
        
        self.idle_time += dt
        
        if self.moving:
            dx = self.target_x - self.pixel_x
            dy = self.target_y - self.pixel_y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist < self.move_speed:
                self.pixel_x = self.target_x
                self.pixel_y = self.target_y
                self.moving = False
                self.hop_height = 0
            else:
                self.pixel_x += (dx / dist) * self.move_speed
                self.pixel_y += (dy / dist) * self.move_speed
                self.hop_phase += 0.2
                self.hop_height = abs(math.sin(self.hop_phase)) * 15
        
        if self.on_log:
            self.pixel_x += self.on_log.speed * dt * 60
            self.grid_x = int(self.pixel_x / TILE_SIZE)
            self.target_x = self.pixel_x
    
    def die(self, death_type, sound_manager):
        self.alive = False
        self.death_type = death_type
        self.death_animation = 0
        if death_type == 'splash':
            sound_manager.play_splash()
        else:
            sound_manager.play_death()
    
    def draw(self, screen, camera_y):
        screen_x = self.pixel_x
        screen_y = self.pixel_y - camera_y
        
        if not self.alive:
            self._draw_death(screen, screen_x, screen_y)
            return
        
        draw_y = screen_y - self.hop_height
        
        # Shadow
        shadow_surf = pygame.Surface((TILE_SIZE - 10, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 50), (0, 0, TILE_SIZE - 10, 10))
        screen.blit(shadow_surf, (screen_x + 5, screen_y + TILE_SIZE - 12))
        
        # Body
        body_rect = pygame.Rect(screen_x + 10, draw_y + 15, 30, 30)
        pygame.draw.rect(screen, COLORS['chicken_body'], body_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), body_rect, 2, border_radius=5)
        
        # Head
        head_rect = pygame.Rect(screen_x + 15, draw_y + 5, 20, 18)
        pygame.draw.rect(screen, COLORS['chicken_body'], head_rect, border_radius=3)
        
        # Comb
        comb_points = [(screen_x + 20, draw_y + 5), (screen_x + 25, draw_y),
                       (screen_x + 30, draw_y + 5), (screen_x + 35, draw_y),
                       (screen_x + 35, draw_y + 8), (screen_x + 20, draw_y + 8)]
        pygame.draw.polygon(screen, COLORS['chicken_comb'], comb_points)
        
        # Beak
        if self.direction == 0:
            beak_points = [(screen_x + 23, draw_y + 8), (screen_x + 27, draw_y + 8), (screen_x + 25, draw_y + 3)]
        elif self.direction == 1:
            beak_points = [(screen_x + 35, draw_y + 10), (screen_x + 35, draw_y + 14), (screen_x + 42, draw_y + 12)]
        elif self.direction == 2:
            beak_points = [(screen_x + 23, draw_y + 20), (screen_x + 27, draw_y + 20), (screen_x + 25, draw_y + 25)]
        else:
            beak_points = [(screen_x + 15, draw_y + 10), (screen_x + 15, draw_y + 14), (screen_x + 8, draw_y + 12)]
        pygame.draw.polygon(screen, COLORS['chicken_beak'], beak_points)
        
        # Eyes
        pygame.draw.circle(screen, (0, 0, 0), (screen_x + 18, draw_y + 12), 3)
        pygame.draw.circle(screen, (0, 0, 0), (screen_x + 32, draw_y + 12), 3)
        pygame.draw.circle(screen, (255, 255, 255), (screen_x + 19, draw_y + 11), 1)
        pygame.draw.circle(screen, (255, 255, 255), (screen_x + 33, draw_y + 11), 1)
    
    def _draw_death(self, screen, screen_x, screen_y):
        if self.death_type == 'squash':
            progress = min(self.death_animation * 3, 1)
            height = int(30 * (1 - progress * 0.8))
            width = int(30 + 20 * progress)
            body_rect = pygame.Rect(screen_x + 10 - int(10 * progress), screen_y + 35 - height, width, height)
            pygame.draw.rect(screen, COLORS['chicken_body'], body_rect)
        elif self.death_type == 'splash':
            for i in range(3):
                radius = int(10 + self.death_animation * 50 + i * 10)
                alpha = max(0, 255 - int(self.death_animation * 300))
                if alpha > 0:
                    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (255, 255, 255, alpha), (radius, radius), radius, 3)
                    screen.blit(surf, (screen_x + 25 - radius, screen_y + 25 - radius))
        elif self.death_type == 'eagle':
            offset_y = -self.death_animation * 200
            body_rect = pygame.Rect(screen_x + 10, screen_y + offset_y + 15, 30, 30)
            pygame.draw.rect(screen, COLORS['chicken_body'], body_rect, border_radius=5)


class Vehicle:
    """Cars, trucks, and trains"""
    def __init__(self, x, y, speed, vehicle_type, length=1):
        self.x = x
        self.y = y
        self.speed = speed
        self.type = vehicle_type
        self.length = length
        self.color = random.choice([COLORS['car_red'], COLORS['car_blue'], 
                                    COLORS['car_yellow'], COLORS['car_green']])
        if vehicle_type == 'truck':
            self.color = COLORS['truck']
            self.length = 2
        elif vehicle_type == 'train':
            self.color = COLORS['train']
            self.length = 6
    
    def update(self, dt, world_width):
        self.x += self.speed * dt * 60
        if self.speed > 0 and self.x > world_width * TILE_SIZE + TILE_SIZE * self.length:
            self.x = -TILE_SIZE * self.length
        elif self.speed < 0 and self.x < -TILE_SIZE * self.length:
            self.x = world_width * TILE_SIZE + TILE_SIZE * self.length
    
    def collides_with(self, player_x, player_y):
        player_rect = pygame.Rect(player_x + 10, player_y + 10, 30, 30)
        vehicle_rect = pygame.Rect(self.x + 5, self.y * TILE_SIZE + 5, 
                                   TILE_SIZE * self.length - 10, TILE_SIZE - 10)
        return player_rect.colliderect(vehicle_rect)
    
    def draw(self, screen, camera_y):
        screen_y = self.y * TILE_SIZE - camera_y
        if self.type == 'car':
            self._draw_car(screen, self.x, screen_y)
        elif self.type == 'truck':
            self._draw_truck(screen, self.x, screen_y)
        elif self.type == 'train':
            self._draw_train(screen, self.x, screen_y)
    
    def _draw_car(self, screen, x, y):
        shadow = pygame.Surface((TILE_SIZE - 10, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 40), (0, 0, TILE_SIZE - 10, 10))
        screen.blit(shadow, (x + 5, y + TILE_SIZE - 8))
        body_rect = pygame.Rect(x + 5, y + 12, TILE_SIZE - 10, TILE_SIZE - 20)
        pygame.draw.rect(screen, self.color, body_rect, border_radius=5)
        roof_rect = pygame.Rect(x + 12, y + 8, TILE_SIZE - 24, 15)
        darker_color = tuple(max(0, c - 40) for c in self.color)
        pygame.draw.rect(screen, darker_color, roof_rect, border_radius=3)
        pygame.draw.rect(screen, (150, 200, 255), (x + 14, y + 10, TILE_SIZE - 28, 10), border_radius=2)
        pygame.draw.circle(screen, (30, 30, 30), (int(x + 12), int(y + TILE_SIZE - 8)), 6)
        pygame.draw.circle(screen, (30, 30, 30), (int(x + TILE_SIZE - 12), int(y + TILE_SIZE - 8)), 6)
    
    def _draw_truck(self, screen, x, y):
        shadow = pygame.Surface((TILE_SIZE * 2 - 10, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 40), (0, 0, TILE_SIZE * 2 - 10, 10))
        screen.blit(shadow, (x + 5, y + TILE_SIZE - 8))
        cargo_rect = pygame.Rect(x + 5, y + 8, TILE_SIZE + 20, TILE_SIZE - 15)
        pygame.draw.rect(screen, self.color, cargo_rect, border_radius=3)
        cab_rect = pygame.Rect(x + TILE_SIZE + 25, y + 12, 25, TILE_SIZE - 20)
        pygame.draw.rect(screen, (80, 80, 90), cab_rect, border_radius=3)
        pygame.draw.rect(screen, (150, 200, 255), (x + TILE_SIZE + 28, y + 14, 19, 12), border_radius=2)
        for wx in [15, 45, TILE_SIZE + 35]:
            pygame.draw.circle(screen, (30, 30, 30), (int(x + wx), int(y + TILE_SIZE - 8)), 6)
    
    def _draw_train(self, screen, x, y):
        for i in range(self.length):
            segment_x = x + i * TILE_SIZE
            color = COLORS['train_front'] if i == 0 else COLORS['train']
            body_rect = pygame.Rect(segment_x + 2, y + 5, TILE_SIZE - 4, TILE_SIZE - 10)
            pygame.draw.rect(screen, color, body_rect, border_radius=3)
            if i > 0:
                for wx in range(2):
                    pygame.draw.rect(screen, (200, 220, 255), (segment_x + 8 + wx * 18, y + 10, 14, 15), border_radius=2)
            else:
                pygame.draw.rect(screen, (50, 50, 60), (segment_x + 5, y + 15, TILE_SIZE - 10, 20))
                pygame.draw.circle(screen, (255, 255, 100), (int(segment_x + 15), int(y + 25)), 5)
            pygame.draw.circle(screen, (40, 40, 40), (int(segment_x + 12), int(y + TILE_SIZE - 5)), 5)
            pygame.draw.circle(screen, (40, 40, 40), (int(segment_x + TILE_SIZE - 12), int(y + TILE_SIZE - 5)), 5)
            if i < self.length - 1:
                pygame.draw.rect(screen, (60, 60, 60), (segment_x + TILE_SIZE - 3, y + 22, 6, 6))


class Log:
    """Floating logs and lily pads"""
    def __init__(self, x, y, speed, length=2, is_lily=False):
        self.x = x
        self.y = y
        self.speed = speed
        self.length = length
        self.is_lily = is_lily
    
    def update(self, dt, world_width):
        self.x += self.speed * dt * 60
        if self.speed > 0 and self.x > world_width * TILE_SIZE + TILE_SIZE * self.length:
            self.x = -TILE_SIZE * self.length
        elif self.speed < 0 and self.x < -TILE_SIZE * self.length:
            self.x = world_width * TILE_SIZE + TILE_SIZE * self.length
    
    def player_on_log(self, player_x, player_y):
        player_center_x = player_x + TILE_SIZE // 2
        log_left = self.x
        log_right = self.x + TILE_SIZE * self.length
        return log_left - 10 < player_center_x < log_right + 10
    
    def draw(self, screen, camera_y):
        screen_y = self.y * TILE_SIZE - camera_y
        if self.is_lily:
            center_x = self.x + TILE_SIZE // 2
            center_y = screen_y + TILE_SIZE // 2
            pygame.draw.circle(screen, COLORS['lily_pad'], (int(center_x), int(center_y)), 20)
            pygame.draw.circle(screen, (20, 100, 20), (int(center_x), int(center_y)), 20, 2)
            pygame.draw.polygon(screen, COLORS['water'], [(center_x, center_y), (center_x + 20, center_y - 5), (center_x + 20, center_y + 5)])
        else:
            log_rect = pygame.Rect(self.x + 3, screen_y + 12, TILE_SIZE * self.length - 6, TILE_SIZE - 24)
            pygame.draw.rect(screen, COLORS['log'], log_rect, border_radius=8)
            pygame.draw.rect(screen, COLORS['log_dark'], (self.x + 3, screen_y + 12, TILE_SIZE * self.length - 6, 8), border_top_left_radius=8, border_top_right_radius=8)
            for i in range(self.length):
                ring_x = self.x + i * TILE_SIZE + 25
                pygame.draw.ellipse(screen, COLORS['log_dark'], (ring_x - 8, screen_y + 15, 16, TILE_SIZE - 30), 2)


class Lane:
    """A single lane/row in the game world"""
    def __init__(self, y, lane_type, world_width):
        self.y = y
        self.type = lane_type
        self.world_width = world_width
        self.obstacles = []
        self.vehicles = []
        self.logs = []
        self.coins = []
        self.grass_variant = random.choice([True, False])
        self.warning_active = False
        self.train_timer = 0
        self.warning_time = 1.5
        self.train = None
        self._generate_content()
    
    def _generate_content(self):
        if self.type == LANE_GRASS:
            num_trees = random.randint(0, 4)
            positions = random.sample(range(self.world_width), min(num_trees, self.world_width))
            self.obstacles = positions
            if random.random() < 0.1:
                available = [i for i in range(self.world_width) if i not in self.obstacles]
                if available:
                    self.coins.append(random.choice(available))
        
        elif self.type == LANE_ROAD:
            # Variable speeds per lane, consistent direction within lane
            speed = random.uniform(0.8, 4.5) * random.choice([-1, 1])
            num_vehicles = random.randint(1, 3)
            vehicle_type = random.choice(['car', 'car', 'car', 'truck'])
            for i in range(num_vehicles):
                start_x = random.randint(0, self.world_width) * TILE_SIZE + i * TILE_SIZE * 4
                self.vehicles.append(Vehicle(start_x, self.y, speed, vehicle_type))
        
        elif self.type == LANE_WATER:
            # Variable speeds per lane, consistent direction within lane
            speed = random.uniform(0.4, 3.2) * random.choice([-1, 1])
            num_logs = random.randint(2, 4)
            for i in range(num_logs):
                start_x = i * TILE_SIZE * 4 + random.randint(0, 2) * TILE_SIZE
                is_lily = random.random() < 0.3
                length = 1 if is_lily else random.randint(2, 4)
                self.logs.append(Log(start_x, self.y, speed, length, is_lily))
        
        elif self.type == LANE_TRAIN:
            self.train_timer = random.uniform(2, 5)
    
    def has_obstacle_at(self, x):
        return x in self.obstacles
    
    def collect_coin(self, x):
        if x in self.coins:
            self.coins.remove(x)
            return True
        return False
    
    def update(self, dt):
        for vehicle in self.vehicles:
            vehicle.update(dt, self.world_width)
        for log in self.logs:
            log.update(dt, self.world_width)
        
        if self.type == LANE_TRAIN:
            if self.train is None:
                self.train_timer -= dt
                if self.train_timer < self.warning_time:
                    self.warning_active = True
                if self.train_timer <= 0:
                    speed = 8 * random.choice([-1, 1])
                    start_x = -TILE_SIZE * 7 if speed > 0 else self.world_width * TILE_SIZE + TILE_SIZE
                    self.train = Vehicle(start_x, self.y, speed, 'train')
                    self.warning_active = False
            else:
                self.train.update(dt, self.world_width)
                if self.train.speed > 0 and self.train.x > self.world_width * TILE_SIZE + TILE_SIZE * 7:
                    self.train = None
                    self.train_timer = random.uniform(3, 8)
                elif self.train.speed < 0 and self.train.x < -TILE_SIZE * 7:
                    self.train = None
                    self.train_timer = random.uniform(3, 8)
    
    def check_collision(self, player):
        if not player.alive:
            return None
        player_grid_y = int(player.pixel_y / TILE_SIZE)
        if player_grid_y != self.y:
            return None
        
        for vehicle in self.vehicles:
            if vehicle.collides_with(player.pixel_x, player.pixel_y):
                return 'squash'
        
        if self.type == LANE_TRAIN and self.train:
            if self.train.collides_with(player.pixel_x, player.pixel_y):
                return 'squash'
        
        if self.type == LANE_WATER:
            on_log = False
            for log in self.logs:
                if log.player_on_log(player.pixel_x, player.pixel_y):
                    on_log = True
                    player.on_log = log
                    break
            if not on_log:
                player.on_log = None
                return 'splash'
        else:
            player.on_log = None
        return None
    
    def draw(self, screen, camera_y):
        screen_y = self.y * TILE_SIZE - camera_y
        
        if self.type == LANE_GRASS:
            color = COLORS['grass_light'] if self.grass_variant else COLORS['grass_dark']
            pygame.draw.rect(screen, color, (0, screen_y, SCREEN_WIDTH, TILE_SIZE))
        
        elif self.type == LANE_ROAD:
            pygame.draw.rect(screen, COLORS['road'], (0, screen_y, SCREEN_WIDTH, TILE_SIZE))
            for i in range(0, SCREEN_WIDTH, 40):
                pygame.draw.rect(screen, COLORS['road_lines'], (i, screen_y + TILE_SIZE//2 - 2, 20, 4))
        
        elif self.type == LANE_WATER:
            pygame.draw.rect(screen, COLORS['water'], (0, screen_y, SCREEN_WIDTH, TILE_SIZE))
            wave_offset = (pygame.time.get_ticks() / 500) % 1
            for i in range(0, SCREEN_WIDTH, 30):
                wave_y = screen_y + TILE_SIZE // 2 + math.sin((i + wave_offset * 30) * 0.1) * 3
                pygame.draw.circle(screen, COLORS['water_dark'], (i, int(wave_y)), 8, 1)
        
        elif self.type == LANE_TRAIN:
            pygame.draw.rect(screen, COLORS['train_track'], (0, screen_y, SCREEN_WIDTH, TILE_SIZE))
            pygame.draw.rect(screen, COLORS['rail'], (0, screen_y + 15, SCREEN_WIDTH, 5))
            pygame.draw.rect(screen, COLORS['rail'], (0, screen_y + TILE_SIZE - 20, SCREEN_WIDTH, 5))
            for i in range(0, SCREEN_WIDTH, 25):
                pygame.draw.rect(screen, (60, 45, 30), (i, screen_y + 10, 10, TILE_SIZE - 20))
            self._draw_train_signal(screen, 8, screen_y)
            self._draw_train_signal(screen, SCREEN_WIDTH - 48, screen_y)
        
        for log in self.logs:
            log.draw(screen, camera_y)
        for obstacle_x in self.obstacles:
            self._draw_tree(screen, obstacle_x * TILE_SIZE, screen_y)
        for coin_x in self.coins:
            self._draw_coin(screen, coin_x * TILE_SIZE, screen_y)
        for vehicle in self.vehicles:
            vehicle.draw(screen, camera_y)
        if self.type == LANE_TRAIN and self.train:
            self.train.draw(screen, camera_y)
    
    def _draw_train_signal(self, screen, x, y):
        """Crossy Road style signal - simple pole with blinking light"""
        post_x = x + 18
        post_top = y - 30
        post_bottom = y + TILE_SIZE - 8
        pygame.draw.rect(screen, (45, 45, 50), (post_x, post_top, 5, post_bottom - post_top))
        
        light_x = post_x + 2
        light_y = post_top - 4
        blink = (pygame.time.get_ticks() // 300) % 2
        
        if self.warning_active:
            if blink:
                glow_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 0, 0, 100), (10, 10), 10)
                screen.blit(glow_surf, (light_x - 9, light_y - 9))
                pygame.draw.circle(screen, (255, 20, 20), (int(light_x), int(light_y)), 6)
                pygame.draw.circle(screen, (255, 150, 150), (int(light_x - 1), int(light_y - 1)), 2)
            else:
                pygame.draw.circle(screen, (120, 30, 30), (int(light_x), int(light_y)), 6)
        else:
            pygame.draw.circle(screen, (50, 25, 25), (int(light_x), int(light_y)), 6)
    
    def _draw_tree(self, screen, x, y):
        trunk_rect = pygame.Rect(x + 18, y + 25, 14, 25)
        pygame.draw.rect(screen, COLORS['tree_trunk'], trunk_rect)
        pygame.draw.circle(screen, COLORS['tree_leaves'], (int(x + 25), int(y + 15)), 18)
        pygame.draw.circle(screen, COLORS['tree_leaves_light'], (int(x + 25), int(y + 10)), 14)
        pygame.draw.circle(screen, COLORS['tree_leaves'], (int(x + 18), int(y + 20)), 12)
        pygame.draw.circle(screen, COLORS['tree_leaves'], (int(x + 32), int(y + 20)), 12)
    
    def _draw_coin(self, screen, x, y):
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2
        bob = math.sin(pygame.time.get_ticks() * 0.005) * 3
        center_y += bob
        pygame.draw.circle(screen, COLORS['coin'], (int(center_x), int(center_y)), 12)
        pygame.draw.circle(screen, COLORS['coin_dark'], (int(center_x), int(center_y)), 12, 2)
        font = pygame.font.Font(None, 18)
        text = font.render("C", True, COLORS['coin_dark'])
        screen.blit(text, (center_x - 5, center_y - 7))


class Eagle:
    """The eagle that catches idle players"""
    def __init__(self):
        self.active = False
        self.x = 0
        self.y = -100
        self.target_x = 0
        self.target_y = 0
        self.phase = 0
        self.wing_phase = 0
    
    def activate(self, player_x, player_y):
        self.active = True
        self.x = player_x - 200
        self.y = player_y - 300
        self.target_x = player_x
        self.target_y = player_y
        self.phase = 0
    
    def update(self, dt, player):
        if not self.active:
            return False
        self.wing_phase += dt * 10
        if self.phase == 0:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 20:
                self.phase = 1
                return True
            else:
                speed = 5
                self.x += (dx / dist) * speed
                self.y += (dy / dist) * speed
        elif self.phase == 2:
            self.y -= 5
            if self.y < -200:
                self.active = False
        return False
    
    def draw(self, screen, camera_y):
        if not self.active:
            return
        screen_x = self.x
        screen_y = self.y - camera_y
        wing_offset = math.sin(self.wing_phase) * 20
        pygame.draw.ellipse(screen, COLORS['eagle'], (screen_x - 15, screen_y - 10, 80, 40))
        pygame.draw.ellipse(screen, COLORS['eagle_wing'], (screen_x - 40, screen_y - 20 - wing_offset, 60, 25))
        pygame.draw.ellipse(screen, COLORS['eagle_wing'], (screen_x + 30, screen_y - 20 + wing_offset, 60, 25))
        pygame.draw.circle(screen, COLORS['eagle'], (int(screen_x + 55), int(screen_y)), 15)
        pygame.draw.polygon(screen, (255, 180, 0), [(screen_x + 65, screen_y - 5), (screen_x + 65, screen_y + 5), (screen_x + 80, screen_y)])
        pygame.draw.circle(screen, (255, 255, 0), (int(screen_x + 58), int(screen_y - 3)), 4)
        pygame.draw.circle(screen, (0, 0, 0), (int(screen_x + 59), int(screen_y - 3)), 2)


class World:
    """The game world with procedurally generated lanes"""
    def __init__(self):
        self.width = 16
        self.lanes = {}
        self._generate_lanes(-5, 20)
    
    def _generate_lanes(self, start_y, end_y):
        for y in range(start_y, end_y):
            if y not in self.lanes:
                self.lanes[y] = self._create_lane(y)
    
    def _create_lane(self, y):
        if y >= 0:
            return Lane(y, LANE_GRASS, self.width)
        roll = random.random()
        if roll < 0.3:
            return Lane(y, LANE_GRASS, self.width)
        elif roll < 0.6:
            return Lane(y, LANE_ROAD, self.width)
        elif roll < 0.85:
            return Lane(y, LANE_WATER, self.width)
        else:
            return Lane(y, LANE_TRAIN, self.width)
    
    def get_lane(self, y):
        if y not in self.lanes:
            self._generate_lanes(y - 10, y + 10)
        return self.lanes.get(y)
    
    def update(self, dt, player_y):
        current_grid_y = int(player_y / TILE_SIZE)
        self._generate_lanes(current_grid_y - 30, current_grid_y + 10)
        for y in range(current_grid_y - 15, current_grid_y + 15):
            if y in self.lanes:
                self.lanes[y].update(dt)
    
    def check_collisions(self, player):
        current_grid_y = int(player.pixel_y / TILE_SIZE)
        for y in range(current_grid_y - 1, current_grid_y + 2):
            if y in self.lanes:
                result = self.lanes[y].check_collision(player)
                if result:
                    return result
        return None
    
    def check_coin_collection(self, player):
        grid_y = int(player.pixel_y / TILE_SIZE)
        grid_x = int(player.pixel_x / TILE_SIZE)
        if grid_y in self.lanes:
            return self.lanes[grid_y].collect_coin(grid_x)
        return False
    
    def draw(self, screen, camera_y):
        start_y = int(camera_y / TILE_SIZE) - 2
        end_y = start_y + int(SCREEN_HEIGHT / TILE_SIZE) + 4
        for y in range(end_y, start_y - 1, -1):
            if y in self.lanes:
                self.lanes[y].draw(screen, camera_y)


class Game:
    """Main game class"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Crossy Road Clone")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 32)
        self.sound_manager = SoundManager()
        self.high_score = 0
        self.reset_game()
    
    def reset_game(self):
        self.world = World()
        self.player = Player(8, 2)
        self.eagle = Eagle()
        self.camera_y = 0
        self.target_camera_y = 0
        self.score = 0
        self.max_y_reached = 0
        self.coins_collected = 0
        self.game_over = False
        self.game_over_timer = 0
    
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if self.game_over:
                    if event.key == pygame.K_SPACE:
                        self.high_score = max(self.high_score, self.score)
                        self.reset_game()
                else:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.player.move(0, -1, self.world, self.sound_manager)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.player.move(0, 1, self.world, self.sound_manager)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.player.move(-1, 0, self.world, self.sound_manager)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.player.move(1, 0, self.world, self.sound_manager)
        return True
    
    def update(self, dt):
        if self.game_over:
            self.game_over_timer += dt
            self.eagle.update(dt, self.player)
            return
        
        self.player.update(dt)
        self.world.update(dt, self.player.pixel_y)
        
        if self.player.alive:
            collision = self.world.check_collisions(self.player)
            if collision:
                self.player.die(collision, self.sound_manager)
                self.game_over = True
        
        if self.world.check_coin_collection(self.player):
            self.coins_collected += 1
            self.sound_manager.play_coin()
        
        if self.player.alive and self.player.on_log:
            if self.player.pixel_x < -TILE_SIZE or self.player.pixel_x > self.world.width * TILE_SIZE:
                self.player.die('splash', self.sound_manager)
                self.game_over = True
        
        if self.player.alive and self.player.idle_time > 5:
            self.eagle.activate(self.player.pixel_x, self.player.pixel_y)
        
        if self.eagle.active:
            caught = self.eagle.update(dt, self.player)
            if caught:
                self.player.die('eagle', self.sound_manager)
                self.eagle.phase = 2
                self.game_over = True
        
        current_y = -self.player.grid_y
        if current_y > self.max_y_reached:
            self.score += current_y - self.max_y_reached
            self.max_y_reached = current_y
        
        self.target_camera_y = self.player.pixel_y - SCREEN_HEIGHT * 0.6
        self.camera_y += (self.target_camera_y - self.camera_y) * 0.1
    
    def draw(self):
        self.screen.fill((135, 206, 235))
        self.world.draw(self.screen, self.camera_y)
        self.player.draw(self.screen, self.camera_y)
        self.eagle.draw(self.screen, self.camera_y)
        self._draw_ui()
        if self.game_over:
            self._draw_game_over()
        pygame.display.flip()
    
    def _draw_ui(self):
        score_text = self.font.render(str(self.score), True, COLORS['ui_text'])
        score_shadow = self.font.render(str(self.score), True, (0, 0, 0))
        self.screen.blit(score_shadow, (SCREEN_WIDTH // 2 - score_text.get_width() // 2 + 2, 22))
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 20))
        coin_text = self.small_font.render(f"Coins: {self.coins_collected}", True, COLORS['ui_text'])
        self.screen.blit(coin_text, (20, 20))
        if self.high_score > 0:
            hs_text = self.small_font.render(f"Best: {self.high_score}", True, COLORS['ui_text'])
            self.screen.blit(hs_text, (SCREEN_WIDTH - hs_text.get_width() - 20, 20))
    
    def _draw_game_over(self):
        if self.game_over_timer < 1:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        go_text = self.font.render("GAME OVER", True, COLORS['ui_text'])
        self.screen.blit(go_text, (SCREEN_WIDTH // 2 - go_text.get_width() // 2, 200))
        score_text = self.font.render(f"Score: {self.score}", True, COLORS['ui_text'])
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 270))
        coins_text = self.small_font.render(f"Coins: {self.coins_collected}", True, COLORS['coin'])
        self.screen.blit(coins_text, (SCREEN_WIDTH // 2 - coins_text.get_width() // 2, 330))
        restart_text = self.small_font.render("Press SPACE to play again", True, COLORS['ui_text'])
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 400))
    
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            running = self.handle_input()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


def main():
    print("=" * 50)
    print("CROSSY ROAD CLONE")
    print("=" * 50)
    print("\nControls:")
    print("  Arrow Keys or WASD - Move")
    print("  SPACE - Restart after game over")
    print("  ESC - Quit")
    print("\nObjective:")
    print("  Cross roads, rivers, and train tracks!")
    print("  Collect coins along the way.")
    print("  Don't stay idle too long or the eagle will get you!")
    print("=" * 50)
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
