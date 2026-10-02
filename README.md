# DualSense to Daslight MIDI

Use a PS5 DualSense controller as a MIDI controller for Daslight 5 on Windows. Plug the controller in over USB, run the exe, and its buttons, sticks, triggers and D-pad are sent as MIDI notes and CCs that Daslight can learn.

## Download

**[Download dualsense-daslight-midi.exe (latest)](https://github.com/merlin2lmml/dualsense-daslight-midi/releases/latest/download/dualsense-daslight-midi.exe)**

All versions: [Releases page](https://github.com/merlin2lmml/dualsense-daslight-midi/releases)

Windows SmartScreen may warn about an unrecognized app because the exe is not code-signed. Click "More info", then "Run anyway".

## One-time setup (about 2 minutes)

Windows has no built-in virtual MIDI cable, so install a free one:

1. Install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) and start it.
2. In loopMIDI, click the `+` button to create a port. Any name containing "loopMIDI" works; the default `loopMIDI Port` is fine.
3. Set loopMIDI to start with Windows so the port exists after reboots.

## Daily use

1. Start loopMIDI (if not already running).
2. Plug in the DualSense with a USB cable.
3. Run `dualsense-daslight-midi.exe`. The window should show the MIDI port name and the controller name. Pressing buttons shows messages in the log.
4. In Daslight 5, enable the loopMIDI port as a MIDI input in the MIDI settings.
5. Use Daslight's MIDI learn on a button or fader, then press or move the matching control on the DualSense.

The app waits for loopMIDI and for the controller, so start order does not matter, and unplugging and replugging the controller is handled automatically.

## MIDI mapping

All messages are on MIDI channel 1.

| Input | MIDI message |
|---|---|
| Face and shoulder buttons (button index i) | Note 36 + i, velocity 127 on press, note off on release |
| D-pad up / down / left / right | Notes 60 / 61 / 62 / 63 |
| Left stick X / Y | CC 20 / CC 21 |
| Right stick X / Y | CC 22 / CC 23 |
| L2 / R2 triggers | CC 24 / CC 25 |

Sticks have an 8 percent deadzone. Triggers go from 0 at rest to 127 fully pressed.

Button and axis numbering comes from the operating system and can differ between USB and Bluetooth, and between driver versions. The log window prints what it receives (for example `Button 0 down`), so check the log to see which index a physical button has. Use USB for the documented layout.

## Troubleshooting

- **"MIDI: searching for loopMIDI port"**: loopMIDI is not running or has no port. Open it and create one.
- **"Controller: none"**: check the USB cable (some cables are charge only) and try another port. Close Steam or DS4Windows if running, since they can grab the controller exclusively.
- **Daslight does not see the port**: restart Daslight after the port exists, and confirm the port is enabled in its MIDI settings.
- **Stick jitter**: raise `DEADZONE` in `bridge_core.py` and rebuild.

## Build from source

Requires Python 3.12 on Windows.

```
pip install -r requirements.txt
python test_core.py
python app.py
```

To build the exe locally, run `build_windows.bat`. The output is `dist\dualsense-daslight-midi.exe`.

Every push to `main` runs the GitHub Actions workflow in `.github/workflows/build.yml`, which tests the mapping logic, builds the exe on a Windows runner, and publishes it as a new release. The "latest" download link above always points at the newest build.

## Customizing the mapping

Edit `NOTE_BASE`, `AXIS_CC`, `HAT_NOTES` and `DEADZONE` in `bridge_core.py`. `test_core.py` checks the mapping logic.

## License

MIT
