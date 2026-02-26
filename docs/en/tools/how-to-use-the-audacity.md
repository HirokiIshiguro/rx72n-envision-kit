# <a name="purpose"></a>Purpose
* Give an outline of how to use the open software for voice editing, [Audacity](https://www.audacityteam.org/) for voice editing
  * As Audacity is used for checking operation of [1+SSI+Audio playback and recording](../bare-metal/ssi-audio.md)

# <a name="summary"></a>The Outline of Audacity
## What is Audacity
* Audacity is an open source software specialized in voice playback/edit/record and writing/reading voice file
* Seems to run not only on Windows but also on Mac and Linux.

## <a name="merit"></a>Point to utilize
* Can be utilized to check simple operation of audio processor, [D2 Audio](https://www.renesas.com/products/audio-video/audio/digital-sound-processors/device/D2-41051.html) mounted in RX72N Envision Kit.
  * Create voice file for test
  * Check if the sound (sine wave and so on) outputted from D2 Audio is as intended or not, by comparing the sound outputted from Audacity.

# <a name="how_to_use"></a>How to use
## Things to prepare
*  PC which installs Audacity
  * Omit how to install Audacity

## <a name="sound_creation"></a>How to create sound
* Create the sound which is equivalent to the sine wave for testing which is used in [1+SSI+Audio playback and recording](../bare-metal/ssi-audio.md)
  * Sine wave of 3.0kHz on the left, 1.5kHz on the right
  * Sampling frequency is 48kHz
  * Quantifying bit number is 24bit

1. Boot Audacity
   1. If an empty soundtrack is created in the initial screen, delete it briefly.
2. Set the default sampling frequency. 
   1. Select `Edit` - `Set environment` from menu bar and open the setting screen.
   2. Press "quality" in the pain in the left.
   3. Select "48000 Hz" with `Sampling frequency（default）`
      * Can change from `Sampling frequency of project（Hz）` on the bottom left of the screen
3. Set the default quantifying bit number
   1. Select `Edit` -  `Set environment` from menu bar and open the setting screen.    
   2. Press `quality`on the left pane
   3. Select "24bit" by `Sample format （default）`
   4. When the settings mentioned above are completed, press `OK` and close the setting screen. 
4. Create empty soundtrack
   1. Select `Track` - `Add newly` - `Monaural track` from menu bar and create empty soundtrack.
   2. Check that "Monaural, 48000Hz, 24bit PCM" is displayed on the left-most column of the soundtrack.
        * If it is not displayed, recreate the above mentioned default setting and empty track creation, or change by performing the individual setting mentioned below
        * The settings of name, sampling frequency and quantifying bit number can be changed by each track from `Soundtrack▼` on the left-most column of the soundtrack
          * Set the name for convenience
5. Generate sine wave（For the sound on the left）
   1. Select the empty soundtrack created above（The left-most column of the sound track is highlighted blue）
   2. Select `Generator―` - `Tone` from menu bar to display the sound creation screen.
   3. Select "Sine wave" with `Waveform`
   4. Enter "3000" with `Frequency (Hz)`
   5. Enter "1" with `Amplitude (0-1)`
      * As this is the setting of relative sound level, set the value as you like.
   6. Enter "30 seconds" with `Duration time`
      * As this is the setting of voice time, set the value as you like
        * Please note that if time is set to too long, file size will be large when it is written in audio file.
      * You can choose units of time (hour, minute, second) and sample number.
    7. Press `OK`
    8. Check that sine wave is generated in the soundtrack which you chose.
       * A period of time displayed on the screen can be scaled up and down by Ctrl and mouse wheel rolling.
6. Generate sine wave（For the sound on the right）
   1. Repeat the step of 4. and 5. to generate sine wave on another soundtrack
       * Enter "1500" in `Frequency (Hz)`
   2. Check that the frequency of the sine waves created in 5. and 6 is different.
7. Separate into the left side sound and right side sound.
   1. Select the soundtrack created for the left side.
   2. Change `pan` " to the left side 100%" on the left-most column of the soundtrack.
   3. Select the soundtrack created for the right side.
   4. Change `pan` " to the right side 100%" on the left-most column of the soundtrack.
8. Playback the generated sound
   * When the above mentioned steps are completed, sound is ready.
   1. Press `Playback` button on the screen
   2. Check that the sound is reproduced with the intended pitch.

## <a name="sound_mix"></a>How to synthesize the sound for the left side and the right side
* Synthesize the sound for the left side and the right side created in [How to create sound](#sound_creation).
1. Select the soundtrack for the left side.
2. Select `mute` on the left-most column of the soundtrack.
3. Select the soundtrack for the right side.
4. Select `mute` on the left-most column of the soundtrack.
5. Select the both soundtracks for the left side and the right side with Ctrl + Click.
  * Whether the left-most column of the soundtrack for the left side and the right side is highlighted blue enables judgment.
6. Select `Track` - `Mix` - `Create by mixing to new track` from menu bar.
7. Since the new soundtrack is created, check that the left-most column of the soundtrack is displayed as "48000Hz、24bit PCM".
   * Note that it is not monaural but stereo.
   * Since each soundtrack for the left side and right side is `pan` and put it to one side, clear sine wave is maintained in each channel of the stereo.
8. Reproduce the created sound
   1. For the soundtrack for the left and right side, select `mute` on the left-most column of the soundtrack.
   2. Check that the synthesized soundtrack is `solo`.
   3. Press `Playback` button on the screen.
   4. Check that the sound is reproduced with the intended pitch. ( it should be the same as the sound reproduced in （[How to create sound](#sound_creation).

## <a name="sound_file_creation"></a>How to generate sound file
* Write the sound created in[How to synthesize the sound for the left and right side](#sound_mix) to WAV file.
1. Check that all the soundtracks except the synthesized track are `mute`（Check that the synthesized soundtrack is `solo`）
2. Select `File` - `Write` - `Write to WAV` from menu bar.
3. Specify the location to save WAV file and file name.
4. Specify`Encoding` as an option and press `Save`
5. Enter a value of meta data tag as an option on the edit screen (not necessary to enter anything) and press `OK`. 
6. Check that WAV file is created

