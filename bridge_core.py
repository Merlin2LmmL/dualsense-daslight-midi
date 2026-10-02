"""Pure mapping logic: pygame joystick events -> MIDI messages. No I/O, so it is testable."""
import mido
import pygame

NOTE_BASE = 36                                          # button i -> note 36+i
AXIS_CC = {0: 20, 1: 21, 2: 22, 3: 23, 4: 24, 5: 25}    # LX LY RX RY L2 R2
HAT_NOTES = {"up": 60, "down": 61, "left": 62, "right": 63}
DEADZONE = 0.08
CH = 0


def to_midi(v):
    if abs(v) < DEADZONE:
        v = 0.0
    return max(0, min(127, int((v + 1) * 63.5)))


class Translator:
    def __init__(self):
        self.last_axis = {}
        self.last_hat = {}

    def translate(self, e):
        """Return a list of (mido.Message, description)."""
        out = []
        if e.type == pygame.JOYBUTTONDOWN:
            out.append((mido.Message("note_on", channel=CH, note=NOTE_BASE + e.button, velocity=127),
                        f"Button {e.button} down"))
        elif e.type == pygame.JOYBUTTONUP:
            out.append((mido.Message("note_off", channel=CH, note=NOTE_BASE + e.button, velocity=0),
                        f"Button {e.button} up"))
        elif e.type == pygame.JOYAXISMOTION and e.axis in AXIS_CC:
            v = to_midi(e.value)
            if self.last_axis.get(e.axis) != v:
                self.last_axis[e.axis] = v
                out.append((mido.Message("control_change", channel=CH, control=AXIS_CC[e.axis], value=v),
                            f"Axis {e.axis} -> CC{AXIS_CC[e.axis]} = {v}"))
        elif e.type == pygame.JOYHATMOTION:
            x, y = e.value
            state = {"up": y == 1, "down": y == -1, "left": x == -1, "right": x == 1}
            for name, on in state.items():
                if self.last_hat.get(name, False) == on:
                    continue
                self.last_hat[name] = on
                n = HAT_NOTES[name]
                out.append((mido.Message("note_on" if on else "note_off", channel=CH, note=n,
                                         velocity=127 if on else 0), f"D-pad {name} {'down' if on else 'up'}"))
        return out
