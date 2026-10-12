# meeting

Records an online meeting on your own Mac and turns it into a transcript with speaker labels,
without the audio or the words going to any server. OBS records your microphone and the call's
audio on separate tracks, whisper.cpp writes the words, and pyannote works out who on the other
side said what.

    meeting start "Project call" --attendees "Ana Silva, Ben Okoro" --vocab "Mori-Zwanzig, projection operator"
    meeting stop
    meeting status
    meeting name "~/Recordings/Meetings/2026-10-07 14-00-00.mkv" SPEAKER_00="Ana Silva"

The `record-meeting` skill in this repository's `meetings` plugin teaches Claude these commands,
and its `transcribe-audio` skill covers any other recording through the `transcribe` script in
this folder. The NextUp menu bar app (`apps/nextup`) puts Record and Join-and-record buttons
beside your next calendar event.

## Consent

Tell everyone on the call that it is being recorded and transcribed, and get their agreement
before you start. Their screens show no recording indicator. Research interviews need the
consent specified by your ethics protocol. Local law and your institution may set further rules.
`meeting start` prints a reminder before recording starts, but does not check consent or those
requirements. Claude is told never to start a recording unless you ask, and to remind you before
it does.

## What stays on this machine

- Recording is OBS, controlled over its WebSocket on `localhost`. Recordings go to
  `~/Recordings/Meetings/` (configurable); keep that folder outside any cloud-synced folder.
- Transcription is whisper.cpp running locally with a model file on disk.
- Speaker labels come from pyannote running locally. Its model is downloaded once from Hugging
  Face, after you accept its terms with a free account; from then on `meeting` runs it with
  `HF_HUB_OFFLINE=1` and without your token. pyannote 4 also sends anonymous usage metrics to
  `otel.pyannote.ai` by default (the pipeline name, the recording's length, the speaker-count
  settings and a random session ID); `meeting` switches that off with
  `PYANNOTE_METRICS_ENABLED=false`.
- Nothing goes to Anthropic unless you ask Claude to read a transcript, and then that transcript
  does, as part of the conversation. `--private` marks a transcript `private: true`, and Claude is
  told never to read one so marked.
- Audio is moved to the Bin 30 days (`retain_days`) after its transcript was made, provided the
  transcript has at least one line and passed its checks. This is because the audio contains
  everyone's voices, and the transcript is what you need afterwards. The checks look for a silent call track or too
  few words for the speech on it, a recording that was not read to the end, repeated lines, stock
  phrases whisper invents (such as "thanks for watching"), and text in an unexpected script.
  Audio whose transcript failed a check is kept until you deal with it. The tool applies the
  30-day rule each time a transcription finishes. Run `meeting prune` to apply it on demand.

## Setup

Work in `tools/meeting` in a clone of this repository. Keep the clone, as the commands run from
it. Needs macOS 15 or later. Tested on Apple silicon with macOS 26, OBS 32.2.2, Python 3.11 and
pyannote.audio 4.0.7.

1. Install the tools:

        brew install --cask obs
        brew install whisper-cpp ffmpeg uv

2. Put the whisper models in `~/models/whisper/` (or set `whisper_model` and `vad_model` in the
   config file). The first is 3.1 GB:

        mkdir -p ~/models/whisper && cd ~/models/whisper
        curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
        curl -LO https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin

3. Create the Python environment in this folder:

        uv sync

4. Download the speaker model once. Make a free Hugging Face account, accept the terms of
   `pyannote/speaker-diarization-community-1`, log in with `uv run hf auth login`, then:

        HF_HUB_OFFLINE=0 PYANNOTE_METRICS_ENABLED=false uv run python -c \
          "from pyannote.audio import Pipeline; Pipeline.from_pretrained('pyannote/speaker-diarization-community-1')"

   After this the token is needed only to fetch model updates.

5. In OBS, turn on the WebSocket server (Tools, WebSocket Server Settings). `meeting` reads the
   password from OBS's own settings and never prints it. Give OBS Microphone and Screen Recording
   permission in System Settings, then run `uv run python obs_setup.py` once. It creates a
   `Meetings` profile and a `Meeting` scene with the microphone on track 1, the call's audio on
   track 2 and both mixed on track 3 for listening back. It records MKV to the recordings folder
   and keeps the (empty) video at 320 by 180 pixels and 10 frames a second. It is safe to re-run.
   If OBS offers Safe Mode after a crash, start it normally instead: Safe Mode turns the WebSocket
   off.

6. Put the commands on your PATH:

        mkdir -p ~/.local/bin
        ln -s "$PWD/meeting" ~/.local/bin/meeting
        ln -s "$PWD/transcribe" ~/.local/bin/transcribe

## Settings

`~/.config/meeting/config.json`, or the file named by `MEETING_CONFIG`. Every key is optional.

| Key | Default | Meaning |
|---|---|---|
| `your_name` | `""` | Label for your microphone track ("Me" when empty) |
| `recordings_dir` | `~/Recordings/Meetings` | Where recordings, sidecars, transcripts and logs go |
| `whisper_model` | `~/models/whisper/ggml-large-v3.bin` | whisper.cpp model |
| `vad_model` | `~/models/whisper/ggml-silero-v6.2.0.bin` | whisper's voice-activity filter |
| `remote_app` | `null` | Audio OBS records from the call: `null` records all system audio; a bundle identifier such as `"com.apple.Safari"` or `"us.zoom.xos"` records that application only. Re-run `obs_setup.py` after changing it |
| `focus_app` | `""` | App brought back to the front after `meeting start` opens OBS, such as `"Safari"` or `"zoom.us"`; empty leaves OBS in front |
| `retain_days` | `30` | Days after a passed transcript before its audio goes to the Bin; `0` turns this off |

By default, OBS records all system audio: the call in any browser or app, notification sounds,
and anything else playing. Mute other sounds for calls that matter. With `remote_app` set, OBS
records only that application. A call in any other application records as silence.

## How the transcript is made

- Each track is transcribed separately, so your words and the other side's never get mixed up.
  With one remote attendee that person is named directly; with more, pyannote's speakers stay
  `SPEAKER_00`, `SPEAKER_01` until you name them with `meeting name`.
- `--vocab` passes names and jargon to whisper as a prompt, which fixes most misspelt technical
  terms. It is capped at about 700 characters.
- The voice-activity filter keeps silence away from whisper, start and end times come from the
  audio level, and any line with under 0.3 s of sound above -55 dB is dropped and listed in the
  sidecar.
- Speakers are assigned one whisper segment at a time, by overlap with pyannote's turns, and a
  segment is split only when a second speaker holds at least 1 s and 30 % of it.
- `--speakers` is for calls on laptop speakers rather than headphones: microphone lines that repeat
  what the other side said at that moment are removed as echo.
- `meeting stop` waits until OBS has finished writing the file.
- If the call's track is silent for a whole recording, the transcript says so in capitals and the
  audio is kept. Check OBS's Screen Recording permission and re-run `obs_setup.py`.
