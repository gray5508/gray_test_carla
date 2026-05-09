import pygame

from .models import NAV_LEFT, NAV_NONE, NAV_RIGHT, NAV_STRAIGHT


def bgr_to_surface(bgr):
    rgb = bgr[:, :, ::-1]
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def set_nav_from_key(event, tracker):
    if event.key == pygame.K_1:
        tracker.set_nav_mode(NAV_STRAIGHT)
        print("Navigation intent: STRAIGHT")
        return True
    if event.key == pygame.K_2:
        tracker.set_nav_mode(NAV_LEFT)
        print("Navigation intent: LEFT")
        return True
    if event.key == pygame.K_3:
        tracker.set_nav_mode(NAV_RIGHT)
        print("Navigation intent: RIGHT")
        return True
    if event.key in (pygame.K_c, pygame.K_0):
        tracker.clear()
        print("Navigation intent cleared.")
        return True
    return False


class PygameWindow(object):
    """A tiny wrapper around pygame display code.

    This module intentionally has no CARLA dependency, so you can test the
    drawing path with a local image or synthetic background.
    """

    def __init__(self, width, height, title):
        pygame.init()
        pygame.font.init()
        self.width = int(width)
        self.height = int(height)
        self.display = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(title)
        self.font = pygame.font.SysFont("Arial", 18)
        self.clock = pygame.time.Clock()

    def tick(self, fps):
        return self.clock.tick(max(1, int(fps)))

    def blit_bgr(self, bgr):
        self.display.blit(bgr_to_surface(bgr), (0, 0))

    def fill(self, color=(10, 10, 10)):
        self.display.fill(color)

    def draw_text_lines(self, lines, x=18, y=16, line_height=23):
        for idx, text in enumerate(lines):
            surface = self.font.render(str(text), True, (255, 255, 255))
            shadow = self.font.render(str(text), True, (20, 20, 20))
            pos = (x, y + idx * line_height)
            self.display.blit(shadow, (pos[0] + 1, pos[1] + 1))
            self.display.blit(surface, pos)

    def flip(self):
        pygame.display.flip()

    def close(self):
        pygame.quit()

