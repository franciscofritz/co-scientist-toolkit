---
name: transcribe-audio
description: "Transcribe an audio or video file to text locally, on this machine, using whisper.cpp. Use whenever the user points at a recording and wants words out of it. Triggers include: 'transcribe this', 'transcribe this interview', 'what does this recording say', 'turn this audio into text', 'get the text out of this file', 'can you listen to this', 'here's a voice memo', 'transcribe the lecture', any mention of a .m4a/.mp3/.wav/.mov/.mp4 file to be read rather than played, or a request to caption or subtitle a video. Boundaries: a call being recorded, or a recording made by the `meeting` command, is `record-meeting`; this skill owns the audio-to-text step for any other file."
---

# Local audio transcription

Turn a recording into text without it leaving the machine. Everything here runs
locally, which matters for research interview audio that cannot go to a
third-party service under ethics approval.

If the recording is a call made with the `meeting` command, use `record-meeting`,
which already transcribes it and labels the speakers. This skill is only the
audio-to-text step.

## What it needs

These are installed separately from this plugin: setup is in `tools/meeting/README.md` in the
co-scientist-toolkit repository (https://github.com/shocklab/co-scientist-toolkit).

- `whisper-cli` from the `whisper-cpp` Homebrew formula, Metal-accelerated
- `ggml-large-v3.bin` in the model folder (`$WHISPER_MODEL_DIR`, default `~/models/whisper`),
  the default model: best on accents, overlapping speech, poor rooms, and 99 languages
- `ggml-large-v3-turbo.bin`, optional, roughly six times faster, a shade less accurate,
  noticeably weaker outside English
- `ggml-silero-v6.2.0.bin`, whisper's voice-activity filter. The wrapper passes it
  automatically, so silence is skipped rather than transcribed
- `transcribe`, the wrapper in the meeting tool's folder, which handles the ffmpeg conversion
  and writes three output formats

The examples below assume `transcribe` is on PATH; if it is not, call it by its full path.

## Step 1: Check the file before running anything

Confirm the path exists and is the file described. A prompt implying a recording
is present does not mean one is.

    ls -lh <file>
    ffprobe -v error -show_entries format=duration,format_name -of default=nw=1 <file>

Report the duration back before starting. A three-hour recording is not a
thirty-second job, and the user should know which they have handed over.

## Step 2: Choose the model

Default to large-v3. Reach for turbo (`-f`) only when the user asks for speed, the
audio is clean English, or a first rough pass is useful before the
careful one.

Force the language when it is known (`-l en`, `-l zh`): auto-detection reads only
the opening seconds, and recordings that start with cross-talk, music or a
greeting in another language get misidentified. Leave it on auto for
mixed-language material.

## Step 3: Bias the vocabulary. This is the single biggest accuracy win

Whisper mangles technical proper nouns, surnames, acronyms and project names, and
it does so confidently. `-p` feeds it an initial prompt that is carried into every
window, and it reliably fixes them. For example:

    no prompt     "The Maury-Zwanzig formalism gives an exact equation..."
    with prompt   "The Mori-Zwanzig formalism gives an exact equation..."

So before running, work out what the recording is about and hand over the words it
will not otherwise know: attendee surnames, the project name, field jargon, the
acronyms in play. Ask the user if it is not obvious from context; this costs one
question and saves a manual correction pass.

    transcribe -p "Mori-Zwanzig formalism, projection operator, Nakajima" <file>

The prompt steers the whole decode, not only the vocabulary, so it can shift
ordinary function words too ("with the memory kernel" for "with a memory kernel").
That is a fair trade for correct names, but do not use it to put words in a
speaker's mouth: list terms that occur in the recording, never a summary of what you
expect them to have said.

## Step 4: Run it

    transcribe [-f] [-g] [-o] [-l CODE] [-p "vocabulary hints"] <file>

The command writes `<name>.txt`, `<name>.srt` and `<name>.vtt` beside the source.
Pass multiple files in one call if needed. Files that already have a transcript
are skipped unless `-o` is given, so include `-o` when re-running with other options.
The command exits 1 when no file was transcribed.

Long jobs: run in the background rather than blocking, and report the duration
estimate first. On Apple silicon transcription runs faster than real time, but
a long interview still takes minutes.

## Step 5: Verify the output, do not assume it

The wrapper runs whisper's voice filter, which stops whisper seeing silence and so
prevents most of what follows. It can still let music or background
noise through, so the checks stay.

Whisper fails in a specific and recognisable way: on silence, music, or dead air
it hallucinates fluent text rather than producing nothing. Watch for

- a phrase repeated many times in a row, or every line written two or three times.
  This is not caused by silence. whisper gives each window the previous window's
  text and starts copying it. Group, far-mic or noisy-room audio can cause this.
  Re-run with `-g -o`. `-g` stops text being passed from one window to the next.
- stock closing lines the speaker never said ("thank you for watching",
  "subscribe to the channel"), which come from its training data
- a transcript far shorter than the duration implies
- passages in the wrong language after a silent stretch

Check the beginning and end of the `.txt` and compare its length with the audio
duration before giving the result to the user or another skill. If something
looks hallucinated, say so rather than passing it on. For language drift,
re-running with `-l` set explicitly and `-o` often fixes the problem.

## Step 6: Hand off

The transcript stays beside the recording. Reading or summarising it sends its text to
Anthropic as part of the conversation, so do that only when the user asks, and never for
material the user has said must stay local (interview data under an ethics protocol, for
example).

## Known limits

**No speaker labels from `transcribe`.** whisper.cpp does not diarise. The meeting tool
uses pyannote (model cached, runs offline) for calls it recorded (see `record-meeting`). For a single-track
file that needs "who said what", say so and offer to run pyannote on it. Never
present an unlabelled transcript as attributed.

**Timestamps stretch over silence, at any length.** Whisper can extend a word's timestamp
over silence after speech ends, even on a short clip, so the `.srt` is not a safe source of
cut points when trimming a recording. Take cut points from the audio: `ffmpeg -af ebur128`
for the speech envelope, or `silencedetect` for the gaps. Timestamp drift also accumulates on
long files. Beyond an hour, check the tail against the audio before using the subtitles.

**16 kHz mono is required.** The wrapper handles this. If calling `whisper-cli`
directly, convert first, or it will refuse the file:

    ffmpeg -nostdin -loglevel error -y -i <in> -ar 16000 -ac 1 -c:a pcm_s16le <out>.wav
