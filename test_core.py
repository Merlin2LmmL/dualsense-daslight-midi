import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from bridge_core import Translator
E = pygame.event.Event
t = Translator()
def one(ev): return [m for m, _ in t.translate(ev)]
m = one(E(pygame.JOYBUTTONDOWN, button=0))[0]; assert (m.type, m.note, m.velocity) == ("note_on", 36, 127)
m = one(E(pygame.JOYBUTTONUP, button=2))[0]; assert (m.type, m.note) == ("note_off", 38)
assert one(E(pygame.JOYAXISMOTION, axis=0, value=0.03))[0].value == 63   # deadzone -> center
assert one(E(pygame.JOYAXISMOTION, axis=0, value=0.03)) == []            # dedupe
assert one(E(pygame.JOYAXISMOTION, axis=5, value=-1.0))[0].value == 0    # trigger rest
assert one(E(pygame.JOYAXISMOTION, axis=5, value=1.0))[0].value == 127
assert one(E(pygame.JOYAXISMOTION, axis=9, value=1.0)) == []             # unmapped axis ignored
ms = one(E(pygame.JOYHATMOTION, value=(1, 1)))
assert {(m.note, m.type) for m in ms} == {(60, "note_on"), (63, "note_on")}
ms = one(E(pygame.JOYHATMOTION, value=(0, 0)))
assert {(m.note, m.type) for m in ms} == {(60, "note_off"), (63, "note_off")}
print("core OK")
