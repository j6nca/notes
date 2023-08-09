# j6n47 (WIP)
## Background
This document will outline the process I went through in building my very own keyboard from scratch.
## Goals
- Smaller form-factor (<60%)
- Hotswap
- OLED Screen?
- Volume Knob?
- QMK/VIA support
- Ortholinear
## Parts & Cost
| Part                   | Cost (CAD) |
|------------------------|------------|
| RPi Pico               | 12.95      |
| Copper Wiring          | 11.99      |
| Diodes                 | 14.68      |
| Soldering Kit          | 19.99      |
| Switches (KTT Kang V3) | 25.87      |
| Kaihl Hotswap Sockets  | 17.29      |
| Keycaps                |            |
| 3D Printing            |            |
| Total Cost (WIP)       | 56.11      |
## Layout
I initially found [keyboard-layout-editor](http://www.keyboard-layout-editor.com/), where I viewed existing layouts and played around with creating my own layouts. For this project, my goal was to create a smaller form factor keyboard than my current 60%.
![j6n58 keyboard layout](https://github.com/j6nca/keyboard/blob/main/qmk/j6n47/diagrams/layout.png)
## Working with QMK
### Setup
Setup of qmk was fairly straight-forward, following the available [documentation](https://docs.qmk.fm/#/newbs_getting_started).
```
pip3 install --user qmk
echo 'PATH="$HOME/.local/bin:$PATH"' >> $HOME/.zshrc && source $HOME/.zshrc
qmk setup
qmk compile -kb clueboard/66/rev3 -km default
```
### QMK Configuration
I realized I would not be able to reuse the raw data I created earlier in `keyboard-layout-editor`, so I looked to port over my layout to qmk configuration.

I forked the `qmk_firmware` repo to include my new layout & created a keyboard profile for myself, adding respective pins based on the rpi pico's pinout diagram.
<br>
![rpi pico pinout diagram](https://github.com/j6nca/keyboard/blob/main/qmk/j6n55/diagrams/rpi_pico_pinout.webp)
```
qmk new-keyboard
...
qmk compile -kb handwired/j6n47 -km default
```
The changes I made can be viewed [here](https://github.com/qmk/qmk_firmware/compare/master...j6nca:qmk_firmware:j6n47).



Update: 23/06/30
Went to the library to print the pcb plate! Had to tinker with the fill (make it much less dense than before) to get the print to fit the timeslot I had booked.
![plate](https://github.com/j6nca/keyboard/blob/main/qmk/j6n55/diagrams/plate.png)
Additionally did a test fitting with some spare switches I had lying around.
![fitting](https://github.com/j6nca/keyboard/blob/main/qmk/j6n55/diagrams/fitting.jpg)![pre-handwiring](https://github.com/j6nca/keyboard/blob/main/qmk/j6n55/diagrams/pre-handwiring.jpg)

Update: 23/07/04
After flashing the 
I wanted the keyboard to also support VIA configuration (that way I won't need to reflash the mcu everytime I want to make changes), enabling support for VIA was surprisingly simple following a [guide from youtuber Joe Scotto](https://www.youtube.com/watch?v=7d5yzBOup9U).
![via config](https://github.com/j6nca/keyboard/blob/main/qmk/j6n55/diagrams/via.png)


Update: 23/07/07
Completed the soldering for the keyboard matrix and microcontroller
![handwiring](https://github.com/j6nca/keyboard/blob/main/qmk/j6n55/diagrams/handwiring.jpg)![handwiring2](https://github.com/j6nca/keyboard/blob/main/qmk/j6n55/diagrams/handwiring2.jpg)

Update: 23/

## References
- OLED Display with QMK: https://www.youtube.com/watch?v=OJSOEStpPIo
- Intro to handwired keyboards: https://www.youtube.com/watch?v=hjml-K-pV4E
- QMK & VIA support: https://www.youtube.com/watch?v=7d5yzBOup9U
- CAD generator for plate: http://www.keyboardcad.com/
- another cad generator: http://builder.swillkb.com/