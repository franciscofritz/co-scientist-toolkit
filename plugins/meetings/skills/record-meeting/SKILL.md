---
name: record-meeting
description: "Record, transcribe and speaker-label an online meeting entirely on this Mac with the `meeting` command: OBS records the user's microphone and the call's audio on separate tracks, whisper.cpp writes the words, pyannote works out who spoke, and nothing is uploaded. Use when the user wants a call recorded or wants to process one they recorded. Triggers include: 'record this meeting', 'start recording', 'I'm about to join a call, record it', 'stop recording', 'process my last recording', 'transcribe the meeting I just recorded', 'who said what in that call', 'name the speakers', 'is it still recording', 'meeting status'. Boundaries: an audio or video file not made by `meeting` is `transcribe-audio`."
---

# Recording and transcribing meetings locally

`meeting` records a call with the user's microphone and everyone else's audio on separate tracks,
transcribes both with whisper.cpp, labels the remote speakers with pyannote, and writes a
transcript as Markdown. Audio, transcript and speaker labels are made on this machine and stay
there. The command is installed separately from this plugin: setup and full notes are in
`tools/meeting/README.md` in the co-scientist-toolkit repository
(https://github.com/shocklab/co-scientist-toolkit). If `meeting` is not on PATH, point the user
there rather than improvising a recording another way.

## Consent

Run `meeting start` only when the user has asked for this meeting to be recorded, never on your
own initiative. It records other people. Before running it, remind the user that nothing on the
other participants' screens shows that recording is taking place. The user has to tell everyone
on the call that it is being recorded and transcribed and get their agreement. Then wait for
the user to confirm before starting. Research interviews need whatever consent the ethics
protocol specifies. Local law and the user's institution may set further rules. The tool does
not check them.

## Commands

    meeting start "Title" --attendees "Name One, Name Two" [--vocab "terms"] [--speakers] [--private]
    meeting stop [--discard]
    meeting status
    meeting name <recording.mkv> SPEAKER_00="Full Name" [SPEAKER_01="Other Name"]
    meeting process <recording.mkv> [--force] [--title T] [same flags as start]
    meeting prune [--days N] [--dry-run]

- `--attendees`: spelled exactly as they should appear. The microphone track is labelled with
  `your_name` from the config file (or "Me"). With one remote attendee that person is named
  directly; with two or more, speakers stay `SPEAKER_00`, `SPEAKER_01` and so on until named.
- `--vocab`: names and jargon whisper won't know, comma-separated. This is the biggest accuracy
  gain: a physics term such as "Mori-Zwanzig" comes out as "Moritz-Wanzig" without it. The prompt
  is capped at about 700 characters (whisper's 224-token limit) with attendees first, so list terms
  that will come up, never a summary of what will be said.
- `--speakers`: the user is on laptop speakers rather than headphones. Remote voices then leak into
  the microphone, and this flag removes microphone lines that repeat what the other side said at
  that moment.
- `--private`: marks the transcript `private: true`. A transcript marked private is never read by
  Claude: do not open it, summarise it or pass it to another tool, even if asked in passing; tell
  the user it is marked private and let them change the flag themselves.

`meeting start` first checks that ffmpeg, whisper-cli and both models are installed. If any is
missing, it records nothing. Pass its message on. It then opens OBS if it is not running.
OBS comes to the front, then focus returns to the app named by `focus_app` in the config file,
if one is set. `meeting stop` waits for OBS to finish writing the file, then transcribes in the
background.

`meeting stop --discard` is for a no-show or audio too poor to use: it skips transcription and moves
the recording and its sidecar to the Bin. Use it when the user says the other side never came or the
audio is unusable.

## After a meeting

1. `meeting status` until the job shows `ENDED rc=0`. Any other `rc` means read its log in the
   recordings folder's `logs/`.
2. Read the sidecar, `<recording>.json` beside the recording. `warnings` lists anything that needs
   a look; `dropped` lists text removed because it sat over silence, where whisper invents lines
   such as "Thank you.".
3. Unnamed speakers: ask the user who they were, or use clear self-introductions in the transcript
   and confirm them with the user. Never assign a name silently. Then run `meeting name`.
4. The transcript stays on disk. Read it, or summarise it, only when the user asks, and never one
   marked `private: true`. Reading it sends its text to Anthropic as part of the conversation, so
   say so if the user seems to expect otherwise.

Transcripts are written to `<recordings_dir>/<YYYY-MM-DD Title>/<YYYY-MM-DD Title>.md`, one line
per utterance as `[HH:MM:SS] Speaker: text`, with the date, title and attendees in front matter.

## Retention

Recordings move to the Bin `retain_days` days (30 by default) after their transcript was made,
provided the transcript has at least one line and passed its checks. This is because the audio contains everyone's voices, and the transcript is what is needed afterwards. Audio whose transcript
failed a check is never removed automatically. Set `retain_days` to 0 to turn automatic removal
off.

## If something is wrong

- OBS offers Safe Mode after a crash: run it normally. Safe Mode turns the WebSocket off.
- If the transcript warns in capitals that the remote track is silent, the other side was not
  captured. Re-run `obs_setup.py` with `uv run python obs_setup.py`, then check that OBS still
  has Screen Recording permission in System Settings. Find `obs_setup.py` in `tools/meeting`
  of the toolkit clone the user installed `meeting` from. `readlink "$(command -v meeting)"`
  shows where that is. If `remote_app` is set to one application, calls in any other
  application record as silence.
- Never ask OBS for its application list over the WebSocket: that request crashes OBS 32.2.2.
  `obs_setup.py` sets the capture directly. Re-run it if OBS's settings are ever lost.
