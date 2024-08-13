import pygame

pygame.init()

screen = pygame.display.set_mode((600, 400))

background = pygame.Surface(screen.get_size())
background.fill((0, 0, 0))

pacman = pygame.Surface((20, 20))
pacman.fill((255, 0, 0))

ghost = pygame.Surface((20, 20))
ghost.fill((0, 0, 255))

ghost_positions = [(200, 200), (400, 200), (200, 400), (400, 400)]

pacman_position = (100, 100)

direction = "up"

running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                direction = "up"
            elif event.key == pygame.K_DOWN:
                direction = "down"
            elif event.key == pygame.K_LEFT:
                direction = "left"
            elif event.key == pygame.K_RIGHT:
                direction = "right"

    pacman_position = (pacman_position[0] + direction[0], pacman_position[1] + direction[1])

    if pacman_position[0] < 0 or pacman_position[0] >= screen.get_width() or pacman_position[1] < 0 or pacman_position[1] >= screen.get_height():
        pacman_position = (100, 100)

    if pacman_position in ghost_positions:
        ghost_positions.remove(pacman_position)
        ghost_positions.append((200, 200))

    screen.blit(background, (0, 0))
    screen.blit(pacman, pacman_position)
    for ghost_position in ghost_positions:
        screen.blit(ghost, ghost_position)

    pygame.display.update()

pygame.quit()