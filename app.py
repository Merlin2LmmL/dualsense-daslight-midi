import os, sys, time, traceback, tkinter as tk
from collections import deque
from tkinter import ttk
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"   # keep working when window is unfocused
import pygame, mido
from bridge_core import Translator

PORT_HINT = "loopmidi"

# ---- tuning ---------------------------------------------------------------
POLL_MS = 5               # how often pygame events are drained
FLUSH_MS = 20             # how often MIDI is sent
MAX_PER_TICK = 6          # hard cap per flush -> max ~300 msgs/s overall
CC_MIN_INTERVAL = 0.030   # min seconds between sends of the SAME control (~33 Hz)
MAX_NOTE_QUEUE = 64       # button events waiting to be sent (oldest dropped)
LOG_FLUSH_MS = 100        # GUI log is updated in batches
LOG_LINES_PER_FLUSH = 15
MAX_LOG_LINES = 200

CONTINUOUS = ("control_change", "pitchwheel")      # coalesced: only latest value matters
DISCRETE = ("note_on", "note_off", "program_change")  # queued in order: never merged


def clamp(v, lo, hi):
    try:
        v = int(v)
    except Exception:
        return lo
    return max(lo, min(hi, v))


def sanitize(msg):
    """Return a safe, range-clamped copy of msg, or None if unsupported."""
    t = msg.type
    ch = clamp(getattr(msg, "channel", 0), 0, 15)
    if t in ("note_on", "note_off"):
        return mido.Message(t, channel=ch,
                            note=clamp(msg.note, 0, 127),
                            velocity=clamp(msg.velocity, 0, 127))
    if t == "control_change":
        return mido.Message(t, channel=ch,
                            control=clamp(msg.control, 0, 127),
                            value=clamp(msg.value, 0, 127))
    if t == "pitchwheel":
        return mido.Message(t, channel=ch, pitch=clamp(msg.pitch, -8192, 8191))
    if t == "program_change":
        return mido.Message(t, channel=ch, program=clamp(msg.program, 0, 127))
    return None


def key_and_value(msg):
    if msg.type == "control_change":
        return ("cc", msg.channel, msg.control), msg.value
    return ("pw", msg.channel), msg.pitch


class App:
    def __init__(self, root):
        self.root = root
        root.title("DualSense to Daslight MIDI")
        root.geometry("420x300")
        self.midi_var = tk.StringVar(value="MIDI: searching for loopMIDI port...")
        self.pad_var = tk.StringVar(value="Controller: none (plug in via USB)")
        ttk.Label(root, textvariable=self.midi_var).pack(anchor="w", padx=8, pady=(8, 0))
        ttk.Label(root, textvariable=self.pad_var).pack(anchor="w", padx=8)
        self.log = tk.Listbox(root, height=12)
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        pygame.display.init()
        pygame.joystick.init()
        self.pads = {}
        self.tr = Translator()
        self.out = None
        self.next_port_try = 0

        self.pending = {}          # key -> (msg, value): latest value per continuous control
        self.last_sent = {}        # key -> last value actually sent
        self.last_time = {}        # key -> monotonic time of last send
        self.notes = deque(maxlen=MAX_NOTE_QUEUE)   # (msg, desc) in order
        self.log_buf = deque(maxlen=500)
        self.seen_errors = set()

        for i in range(pygame.joystick.get_count()):
            self.add_pad(i)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll()
        self.flush()
        self.flush_log()

    # ---- logging (batched, never blocks the loop) -------------------------
    def say(self, s):
        self.log_buf.append(s)

    def say_error_once(self, where, ex):
        k = (where, repr(ex))
        if k not in self.seen_errors and len(self.seen_errors) < 50:
            self.seen_errors.add(k)
            self.say("ERROR in %s: %s" % (where, ex))
            traceback.print_exc()

    def flush_log(self):
        try:
            n = 0
            while self.log_buf and n < LOG_LINES_PER_FLUSH:
                self.log.insert(tk.END, self.log_buf.popleft())
                n += 1
            if n:
                while self.log.size() > MAX_LOG_LINES:
                    self.log.delete(0)
                self.log.see(tk.END)
        except Exception as ex:
            self.say_error_once("flush_log", ex)
        finally:
            self.root.after(LOG_FLUSH_MS, self.flush_log)

    # ---- controllers / port -----------------------------------------------
    def add_pad(self, idx):
        try:
            j = pygame.joystick.Joystick(idx)
            self.pads[j.get_instance_id()] = j
            self.pad_var.set("Controller: " + j.get_name())
            self.say("Connected: " + j.get_name())
        except Exception as ex:
            self.say_error_once("add_pad", ex)

    def close_port(self):
        if self.out is not None:
            try:
                self.out.close()
            except Exception:
                pass
        self.out = None

    def try_port(self):
        if time.time() < self.next_port_try:
            return
        self.next_port_try = time.time() + 2
        try:
            for n in mido.get_output_names():
                if PORT_HINT in n.lower():
                    self.out = mido.open_output(n)
                    # fresh start: drop anything stale so there is no burst on connect
                    self.pending.clear()
                    self.notes.clear()
                    self.last_sent.clear()
                    self.last_time.clear()
                    self.midi_var.set("MIDI: " + n)
                    self.say("MIDI port opened: " + n)
                    return
        except Exception as ex:
            self.say("MIDI error: %s" % ex)

    def port_lost(self):
        self.close_port()
        self.midi_var.set("MIDI: port lost, searching...")
        self.say("MIDI port lost")
        self.next_port_try = time.time() + 1

    def send(self, msg):
        try:
            self.out.send(msg)
            return True
        except Exception:
            self.port_lost()
            return False

    # ---- input: drain pygame, never send here -----------------------------
    def poll(self):
        try:
            if self.out is None:
                self.try_port()
            for e in pygame.event.get():
                try:
                    if e.type == pygame.JOYDEVICEADDED:
                        self.add_pad(e.device_index)
                    elif e.type == pygame.JOYDEVICEREMOVED:
                        self.pads.pop(e.instance_id, None)
                        self.pad_var.set("Controller: none (plug in via USB)")
                        self.say("Controller removed")
                    else:
                        self.handle_event(e)
                except Exception as ex:
                    self.say_error_once("event", ex)
        except Exception as ex:
            self.say_error_once("poll", ex)
        finally:
            self.root.after(POLL_MS, self.poll)

    def handle_event(self, e):
        for msg, desc in self.tr.translate(e):
            if self.out is None:
                continue                       # nothing to send to; don't pile up
            msg = sanitize(msg)
            if msg is None:
                continue
            if msg.type in CONTINUOUS:
                key, val = key_and_value(msg)
                self.pending[key] = (msg, val)   # newer overwrites older
            else:
                self.notes.append((msg, desc))   # in order, bounded

    # ---- output: fixed-rate, budgeted, no sleeping -------------------------
    def flush(self):
        try:
            if self.out is not None:
                budget = MAX_PER_TICK

                # 1) buttons first, in order
                while budget > 0 and self.notes and self.out is not None:
                    msg, desc = self.notes.popleft()
                    if self.send(msg):
                        self.say(desc)
                        budget -= 1

                # 2) latest value of each moved axis, rate-limited per control
                now = time.monotonic()
                for key in list(self.pending):
                    if budget <= 0 or self.out is None:
                        break
                    msg, val = self.pending[key]
                    if now - self.last_time.get(key, 0.0) < CC_MIN_INTERVAL:
                        continue                 # keep it pending; sent on a later tick
                    del self.pending[key]
                    if self.last_sent.get(key) == val:
                        continue                 # unchanged -> skip
                    if self.send(msg):
                        self.last_sent[key] = val
                        self.last_time[key] = now
                        budget -= 1
        except Exception as ex:
            self.say_error_once("flush", ex)
        finally:
            self.root.after(FLUSH_MS, self.flush)

    def on_close(self):
        try:
            self.close_port()
            pygame.quit()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
