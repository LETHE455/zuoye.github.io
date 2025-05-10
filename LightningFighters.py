
import pygame
import random
import time
import cv2
import mediapipe as mp
import math

# 初始化pygame
pygame.init()

# 屏幕设置
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
GAME_WIDTH = 800
GAME_HEIGHT = 600

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# 初始化MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# 创建屏幕
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("雷霆战机 - 手势控制版")

# 初始化摄像头
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 400)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 300)

# 游戏区域划分
game_rect = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)
aux_rect = pygame.Rect(GAME_WIDTH, 0, SCREEN_WIDTH - GAME_WIDTH, SCREEN_HEIGHT)

# 游戏状态
class GameState:
    def __init__(self):
        self.player = {"x": GAME_WIDTH // 2, "y": GAME_HEIGHT - 100, "size": 30}
        self.bullets = []
        self.enemies = []
        self.last_shot_time = time.time()
        self.last_enemy_time = time.time()
        self.game_over = False
        self.score = 0
        self.lives = 3  # 初始生命值
        self.shoot_cooldown = 0.15  # 射击冷却时间
        self.enemy_spawn_rate = 0.8  # 敌人生成速率
        self.invincible = False  # 无敌状态
        self.invincible_time = 0  # 无敌时间
        
    def spawn_enemies(self):
        # 随机生成敌人
        if random.random() < 0.3:  # 30%几率生成敌人
            x = random.randint(50, GAME_WIDTH - 50)
            y = random.randint(-100, -20)
            speed = random.uniform(1.0, 3.0)
            self.enemies.append({"x": x, "y": y, "speed": speed, "size": 30})

# 创建游戏状态
game_state = GameState()

# 主游戏循环
clock = pygame.time.Clock()
running = True

while running:
    # 处理退出事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # 清屏
    screen.fill(BLACK)
    
    # 处理摄像头帧
    ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        
        direction_text = "No Hand"
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # 绘制手部骨架
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # 计算手掌中心位置
                palm_center_x = sum([lm.x for lm in hand_landmarks.landmark]) / len(hand_landmarks.landmark)
                palm_center_y = sum([lm.y for lm in hand_landmarks.landmark]) / len(hand_landmarks.landmark)
                direction_text = f"Palm Position: ({palm_center_x:.2f}, {1 - palm_center_y:.2f})"
        
        # 在右侧界面显示摄像头画面
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (400, 300))
        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(frame_surface, (GAME_WIDTH, 0))
        
        # 显示手掌和战机位置信息
        font = pygame.font.SysFont(None, 28)  # 使用稍小的字体
        # 手掌位置
        hand_text = f"Hand: {direction_text}"
        hand_surface = font.render(hand_text, True, WHITE)
        screen.blit(hand_surface, (GAME_WIDTH + 10, 320))
        
        # 战机位置
        fighter_text = f"Fighter: ({game_state.player['x']}, {GAME_HEIGHT - game_state.player['y']})"
        fighter_surface = font.render(fighter_text, True, WHITE)
        screen.blit(fighter_surface, (GAME_WIDTH + 10, 360))
        
        # 添加分隔线
        pygame.draw.line(screen, WHITE, (GAME_WIDTH + 10, 350), (SCREEN_WIDTH - 10, 350), 1)
    
    # 绘制游戏区域边界
    pygame.draw.rect(screen, WHITE, game_rect, 2)
    pygame.draw.rect(screen, WHITE, aux_rect, 2)
    
    # 敌人生成
    current_time = time.time()
    if current_time - game_state.last_enemy_time >= game_state.enemy_spawn_rate:
        game_state.spawn_enemies()
        game_state.last_enemy_time = current_time
    
    # 战机移动控制
    if results.multi_hand_landmarks and not game_state.game_over:
        # 根据手掌中心位置更新战机位置，并限制在边界内
        game_state.player["x"] = max(game_state.player["size"]//2, 
                                   min(int(palm_center_x * GAME_WIDTH), 
                                       GAME_WIDTH - game_state.player["size"]//2))
        game_state.player["y"] = max(game_state.player["size"]//2,
                                   min(int(palm_center_y * GAME_HEIGHT), 
                                       GAME_HEIGHT - game_state.player["size"]//2))
        
        # 射击控制
        if current_time - game_state.last_shot_time >= game_state.shoot_cooldown:
            game_state.bullets.append({
                "x": game_state.player["x"],
                "y": game_state.player["y"] - game_state.player["size"],
                "speed": 10
            })
            game_state.last_shot_time = current_time
    
    # 更新子弹位置
    for bullet in game_state.bullets[:]:
        bullet["y"] -= bullet["speed"]
        if bullet["y"] < 0:
            game_state.bullets.remove(bullet)
    
    # 更新敌人位置
    for enemy in game_state.enemies[:]:
        enemy["y"] += enemy["speed"]
        if enemy["y"] > GAME_HEIGHT:
            game_state.enemies.remove(enemy)
    
    # 碰撞检测
    for enemy in game_state.enemies[:]:
        # 子弹与敌人碰撞
        for bullet in game_state.bullets[:]:
            if (abs(bullet["x"] - enemy["x"]) < 20 and 
                abs(bullet["y"] - enemy["y"]) < 20):
                game_state.enemies.remove(enemy)
                game_state.bullets.remove(bullet)
                game_state.score += 20
                break
        
        # 玩家与敌人碰撞
        if (not game_state.invincible and 
            abs(game_state.player["x"] - enemy["x"]) < 30 and 
            abs(game_state.player["y"] - enemy["y"]) < 30):
            game_state.lives -= 1
            game_state.invincible = True
            game_state.invincible_time = time.time()
            if game_state.lives <= 0:
                game_state.game_over = True
    
    # 绘制战机
    pygame.draw.rect(screen, GREEN, 
        (game_state.player["x"] - game_state.player["size"]//2, 
         game_state.player["y"] - game_state.player["size"]//2, 
         game_state.player["size"], game_state.player["size"]))
    
    # 绘制子弹
    for bullet in game_state.bullets:
        pygame.draw.rect(screen, WHITE, (bullet["x"]-2, bullet["y"]-5, 4, 10))
    
    # 绘制敌人
    for enemy in game_state.enemies:
        pygame.draw.rect(screen, RED, 
            (enemy["x"] - enemy["size"]//2, 
             enemy["y"] - enemy["size"]//2, 
             enemy["size"], enemy["size"]))
    
    # 游戏结束处理
    if game_state.game_over:
        # 半透明背景
        s = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))
        screen.blit(s, (0, 0))
        
        # 游戏结束文字
        font = pygame.font.SysFont(None, 72)
        game_over_text = font.render("Game Over", True, WHITE)
        score_text = font.render(f"Final Score: {game_state.score}", True, WHITE)
        restart_text = font.render("Press R to Restart", True, WHITE)
        
        screen.blit(game_over_text, (GAME_WIDTH//2 - game_over_text.get_width()//2, GAME_HEIGHT//2 - 100))
        screen.blit(score_text, (GAME_WIDTH//2 - score_text.get_width()//2, GAME_HEIGHT//2))
        screen.blit(restart_text, (GAME_WIDTH//2 - restart_text.get_width()//2, GAME_HEIGHT//2 + 100))
        
        # 检查是否按下R键重启
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                game_state = GameState()
    
    # 显示分数和生命值
    font = pygame.font.SysFont(None, 36)
    score_text = font.render(f"Score: {game_state.score}", True, WHITE)
    lives_text = font.render(f"Lives: {game_state.lives}", True, WHITE)
    screen.blit(score_text, (10, 10))
    screen.blit(lives_text, (10, 50))
    
    # 处理无敌状态
    current_time = time.time()
    if game_state.invincible and current_time - game_state.invincible_time > 2.0:
        game_state.invincible = False
    
    # 更新显示
    pygame.display.flip()
    clock.tick(60)

cap.release()
pygame.quit()
