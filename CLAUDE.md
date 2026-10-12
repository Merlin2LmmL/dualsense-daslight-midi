# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Use a PS5 DualSense controller as a MIDI controller for Daslight 5 on Windows. `bridge_core.py` translates pygame joystick events to MIDI messages (`note_on`/`note_off` for buttons/D-pad, `control_change` for axes); `app.py` opens a `loopMIDI` output port via `mido` and runs a `tkinter` poll loop (`poll()` every 3ms). No server or build pipeline beyond a Windows `.exe` release.

## Commands

- Run: `python app.py` (requires Windows loopMIDI port named `loopMIDI Port`, controller plugged in via USB)
- Test mapping logic: `python test_core.py`
- Build Windows exe: `build_windows.bat` (produces release binary; signed unnecessarily — SmartScreen may warn)
- Install deps: `pip install -r requirements.txt` (`mido`, `pygame`)
- Setup before first run: install `loopMIDI`, create a port (see README.md)

## Key files to read together

- `app.py` — `App.poll()` loop (3ms via `root.after`), MIDI output (`mido.open_output` + `out.send`), controller plug/remove (`JOYDEVICEADDED/REMOVED`), cooldown (`time.sleep(0.03)` after send to avoid flooding Daslight)
- `bridge_core.py` — `Translator.translate()` (pygame event → `mido.Message`), `NOTE_BASE` + `AXIS_CC` mapping, `DEADZONE`, axis throttling via `last_axis`/`last_hat`
- `test_core.py` — mapping logic tests (no GUI/I/O)
- `README.md` — loopMIDI setup, SmartScreen note, download links

## Architecture notes

- No build/test/lint pipeline; static Python + Windows release workflow (`build_windows.bat`).
- The 0.03s sleep at `app.py:72` is intentional: Daslight can't handle high-rate MIDI floods. `bridge_core.py` already skips duplicate axis CC values (`last_axis` check at line 34) and hat repeats (`last_hat`).
- Controller events come from `pygame`; MIDI goes out via `mido`. If the port is lost, `app.py` resets `self.out = None` and retries every poll cycle.
