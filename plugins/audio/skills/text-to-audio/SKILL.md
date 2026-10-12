---
name: text-to-audio
description: "Turn short text into a speech audio file locally with the `tts` command (Kokoro-82M on MLX, Apache-2.0, so the audio can ship in apps). Use whenever speech audio is needed from text: voice prompts or narration for an app or game, a sound for a button or notification, onboarding or tutorial voice-over, sample lines to compare voices, placeholder dialogue, or any 'say this out loud as a file'. Triggers include: 'make an audio file saying', 'generate a voice line', 'TTS for my app', 'add spoken feedback', 'record this sentence', 'text to speech', 'voice prompt', 'narrate this paragraph', and requests while building an app that imply spoken audio even if they don't say TTS. Prefer it to cloud TTS APIs and to macOS say. Boundaries: a whole paper or PDF read aloud is paper-to-audio; turning audio into text is transcribe-audio."
---

# Text to audio

Use `tts` to make speech from text on the user's Mac with Kokoro-82M on MLX. Each command takes
a few seconds, mostly to load the model, so run a set of prompts as one batch. Kokoro's weights
and text front end (misaki) are Apache-2.0, and the runtime (mlx-audio, MLX) is MIT. The user can
ship the audio inside an app. `tts` itself is part of pdf2audio, which is AGPL-3.0, so its code
does not go into a closed app. No text or audio leaves the machine, and nothing costs money.
Prefer it to a cloud TTS API unless the user wants a particular hosted voice. Also prefer it to
macOS `say`, which sounds dated. Each run asks Hugging Face whether the model has changed,
sending the model's name and the machine's IP address.

## What it needs

`tts` comes from the pdf2audio repository (https://github.com/jonstraveladventures/pdf2audio)
and is installed separately from this plugin:

    brew install uv ffmpeg
    uv tool install --python 3.12 git+https://github.com/jonstraveladventures/pdf2audio

This installs `tts` and `pdf2audio` into `~/.local/bin`. If that folder is not on PATH, `uv tool update-shell` adds it. ffmpeg writes MP3, M4A and OGG. On an Apple Silicon Mac, Kokoro runs
on MLX. Other platforms use the PyTorch build. The first run downloads Kokoro's weights and
voices (under 400 MB).

If `command -v tts` finds nothing, tell the user the tools are not installed and give them the
steps above. Do not install packages yourself.

## Use

    tts "Welcome back." -o assets/audio/welcome.wav
    tts -f script.txt -o intro.mp3 --voice bm_george
    echo "Timer finished." | tts -o done.m4a
    tts --batch prompts.json --out-dir assets/audio --format wav
    tts --list-voices

- **Format** follows the output extension: `wav`, `flac`, `mp3`, `m4a` (AAC), `ogg`
  (Opus). Choose for the target: WAV or M4A for iOS and macOS assets, WAV or OGG for
  Android and games, MP3 or M4A for the web. Default to WAV when nothing says otherwise.
- **Sample rate** is Kokoro's native 24 kHz mono, except `.ogg`, which is Opus at 48 kHz.
  Pass `--rate 44100` or `--rate 48000` when the project's audio pipeline expects it.
- **Silence** at the start and end is trimmed to 30 ms by default, so UI sounds play
  promptly; `--no-trim` keeps Kokoro's padding.
- **Voice**: default `af_heart` (American female). Use the English voices: British `bf_*` and
  `bm_*`, American `af_*` and `am_*`. The other voices shown by `--list-voices` are for other
  languages, and pdf2audio installs only the English text front end. Ask only if the voice
  matters to the task. Otherwise, use the default and report which voice you used.
- **Batch**: for a set of prompts, write a JSON list of `{"id", "text"}` (optionally `"voice"`
  per line) or a CSV with `id,text[,voice]` columns, and pass `--batch`. Files are named
  `<id>.<format>`. Any character other than a letter, digit, dot, underscore or hyphen is changed
  to `_` (`two words` gives `two_words.wav`). Choose ids the app code can reference.

Write straight into the project's assets folder when you know it, and wire the files in
if that is part of the task.

## Check before saying it is done

Check the path and duration printed for each file. At the default speed, trimmed speech runs
at about 2.5 to 3.5 words per second. A duration far from that means something went wrong.
Confirm words that matter, including names, numbers, jargon and anything Kokoro might
mispronounce. If the `transcribe` command from the co-scientist-toolkit's `tools/meeting` is
installed, use `transcribe -l en <file>` to transcribe locally. It writes `.txt`, `.srt` and
`.vtt` files beside the audio, so run it on a copy outside the project's assets folder.
Offer `--play` or `afplay <file>` if the user wants to hear it.

Kokoro reads what it is given literally: spell out symbols, units and abbreviations
the way they should be said ("5 km" as "five kilometres", "v2.1" as "version two point
one") before passing text in.
