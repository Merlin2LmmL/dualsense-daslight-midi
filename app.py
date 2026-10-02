import os, sys, time, tkinter as tk
from tkinter import ttk
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"   # keep working when window is unfocused
import pygame, mido
from bridge_core import Translator

PORT_HINT = "loopmidi"


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
        for i in range(pygame.joystick.get_count()):
            self.add_pad(i)
        self.poll()

    def say(self, s):
        self.log.insert(tk.END, s)
        if self.log.size() > 200:
            self.log.delete(0)
        self.log.see(tk.END)

    def add_pad(self, idx):
        j = pygame.joystick.Joystick(idx)
        self.pads[j.get_instance_id()] = j
        self.pad_var.set("Controller: " + j.get_name())
        self.say("Connected: " + j.get_name())

    def try_port(self):
        if time.time() < self.next_port_try:
            return
        self.next_port_try = time.time() + 2
        try:
            for n in mido.get_output_names():
                if PORT_HINT in n.lower():
                    self.out = mido.open_output(n)
                    self.midi_var.set("MIDI: " + n)
                    self.say("MIDI port opened: " + n)
                    return
        except Exception as ex:
            self.say("MIDI error: %s" % ex)

    def poll(self):
        if self.out is None:
            self.try_port()
        for e in pygame.event.get():
            if e.type == pygame.JOYDEVICEADDED:
                self.add_pad(e.device_index)
            elif e.type == pygame.JOYDEVICEREMOVED:
                self.pads.pop(e.instance_id, None)
                self.pad_var.set("Controller: none (plug in via USB)")
                self.say("Controller removed")
            else:
                for msg, desc in self.tr.translate(e):
                    if self.out is not None:
                        try:
                            self.out.send(msg)
                        except Exception:
                            self.out = None
                            self.midi_var.set("MIDI: port lost, searching...")
                    self.say(desc)
        self.root.after(3, self.poll)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
