#!/usr/bin/env python3
"""meeting: record, transcribe and speaker-label online meetings, entirely on this Mac.

  meeting start "Title" [--attendees "Name One, Name Two"] [--vocab "terms"] [--speakers] [--private]
  meeting stop
  meeting status
  meeting process FILE.mkv [--title T] [--attendees A] [--vocab V] [--lang en] [--speakers] [--private] [--force]
  meeting name FILE.mkv SPEAKER_00="Full Name" [SPEAKER_01="Other Name"]
  meeting prune [--dry-run] [--days 30]

Recording is OBS over its WebSocket: microphone on track 1, the call's audio on track 2.
Words come from whisper.cpp large-v3 on each track, remote speakers from pyannote on
track 2, run offline. Settings: ~/.config/meeting/config.json (see meeting_config.py).
Design and reasons: README.md.
"""
import argparse
import datetime as dt
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import wave

import meeting_config

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = meeting_config.load()
REC_DIR = CFG["recordings_dir"]
LOG_DIR = os.path.join(REC_DIR, "logs")
PENDING = os.path.join(REC_DIR, ".pending.json")
RETAIN_DAYS = CFG["retain_days"]  # default 30; 0 turns the automatic removal off
TRASH = "/usr/bin/trash"  # the system Bin; nothing is deleted outright
MODEL = CFG["whisper_model"]
VAD_MODEL = CFG["vad_model"]
YOUR_NAME = CFG["your_name"]
ME = YOUR_NAME or "Me"  # label for the microphone track
FOCUS_APP = CFG["focus_app"]
PROMPT_BUDGET = 700  # characters: whisper large-v3 caps the prompt at 224 tokens
FRAME = 0.1          # seconds per loudness frame
SPEECH_DB = -55.0    # measured on test recordings: speech -15 to -34 dB, room -72 to -86 dB, silence below -95

os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")
os.environ["HF_HUB_OFFLINE"] = "1"  # models are cached; never touch the network
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
# pyannote.audio 4.x sends anonymous usage metrics to otel.pyannote.ai unless told not to:
# the pipeline name, the audio's duration, the speaker-count arguments, a random session id.
# HF_HUB_OFFLINE does not stop that, so it is switched off here.
os.environ["PYANNOTE_METRICS_ENABLED"] = "false"

CONSENT = ("Tell everyone on the call that you are recording and transcribing it. "
           "Nothing on their screen shows that you are.")
STOCK = re.compile(r"thank(s| you) for watching|like and subscribe|please subscribe|"
                   r"subtitles by|amara\.org|see you in the next video", re.I)


# ---------- small helpers ----------
def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def split_names(s):
    return [n.strip() for n in (s or "").split(",") if n.strip()]


def safe(name):
    return re.sub(r'[\\/:*?"<>|]+', "-", name).strip()


def sidecar_path(path):
    return os.path.splitext(path)[0] + ".json"


SIDECAR_KEYS = {"recording", "started", "stopped", "processed", "transcript"}


def load_sidecar(path):
    """The tool's notes on a recording, kept in <name>.json beside it. A JSON of that name
    that the tool did not write is left alone: the run stops rather than rewrite it."""
    p = sidecar_path(path)
    if not os.path.exists(p):
        return {}
    try:
        meta = json.load(open(p))
    except ValueError:
        meta = None
    if not isinstance(meta, dict) or not SIDECAR_KEYS & meta.keys():
        sys.exit(f"{p} exists and was not written by meeting. Move or rename it, then run again.")
    return meta


def to_bin(f):
    """Move f to the Bin. Returns an error message, or None when it worked."""
    if not os.path.exists(TRASH):
        return f"{TRASH} not found (it comes with macOS 15 and later); the file was kept"
    r = subprocess.run([TRASH, f], capture_output=True, text=True)
    return r.stderr.strip() or f"trash exited {r.returncode}" if r.returncode else None


TOOLS = ("ffmpeg", "ffprobe", "whisper-cli")
SPEAKER_MODEL = "pyannote/speaker-diarization-community-1"


def missing_requirements():
    """What transcription needs that this Mac lacks, checked before anything is recorded."""
    out = [f"{t} (not on PATH)" for t in TOOLS if not shutil.which(t)]
    if not os.path.exists(MODEL):
        out.append(f"the whisper model ({MODEL})")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(SPEAKER_MODEL, local_files_only=True)
    except Exception:
        out.append(f"the speaker model {SPEAKER_MODEL} (setup step 4 in the README downloads it)")
    return out


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}): {r.stderr[-800:]}")
    return r.stdout


def ts(sec):
    sec = int(sec)
    return f"[{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}]"


def words(t):
    return re.sub(r"[^\w\s]", "", t.lower()).split()


# ---------- OBS ----------
def obs_client(launch=False):
    """Connect to OBS. With launch=True, open it first if it isn't running
    (OBS is started on demand, not at login)."""
    import logging
    sys.path.insert(0, HERE)
    import obsws_python as obs
    from obs_probe import load_password
    logging.getLogger("obsws_python").setLevel(logging.CRITICAL)

    def connect():
        return obs.ReqClient(host="localhost", port=4455, password=load_password(), timeout=10)

    try:
        return connect()
    except Exception:
        if not launch:
            raise
    print("OBS isn't running; opening it (it comes to the front for a moment).")
    # Foreground, never `open -g`: OBS launched in the background can record the call's audio
    # as silence.
    subprocess.run(["open", "-a", "OBS"])
    end = time.time() + 45
    while time.time() < end:
        time.sleep(1.5)
        try:
            cl = connect()
        except Exception:
            continue
        if FOCUS_APP:
            subprocess.run(["open", "-a", FOCUS_APP])  # hand focus back to the call
        return cl
    sys.exit("OBS did not come up within 45 s. If it is offering Safe Mode after a crash, "
             "choose to run it normally: Safe Mode turns the WebSocket off.")


def req(cl, name, data=None):
    return cl.send(name, data or {}, raw=True)


def recording_seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return None


def wait_until_written(cl, path, timeout=60):
    """StopRecord returns before OBS has finished the file, so wait until OBS reports the
    output inactive, the file has stopped growing, and its header has a length."""
    end, last = time.time() + timeout, -1
    while time.time() < end:
        size = os.path.getsize(path) if os.path.exists(path) else -1
        if size > 0 and size == last and not req(cl, "GetRecordStatus").get("outputActive") \
                and recording_seconds(path):
            return True
        last = size
        time.sleep(1)
    return False


def cmd_start(a):
    missing = missing_requirements()
    if missing:
        sys.exit("Not recording: transcription would fail. Missing: " + "; ".join(missing))
    cl = obs_client(launch=True)
    if req(cl, "GetRecordStatus").get("outputActive"):
        sys.exit("OBS is already recording. Run `meeting stop` first.")
    prof = req(cl, "GetProfileList")["currentProfileName"]
    if prof != "Meetings":
        sys.exit(f"OBS is on profile {prof!r}, not 'Meetings'. Run obs_setup.py first.")
    meta = {"title": a.title, "attendees": split_names(a.attendees), "vocab": a.vocab or "",
            "speakers_mode": a.speakers, "private": a.private, "lang": a.lang or "en",
            "started": dt.datetime.now().isoformat(timespec="seconds")}
    os.makedirs(REC_DIR, exist_ok=True)
    json.dump(meta, open(PENDING, "w"), indent=2)
    print(CONSENT)
    req(cl, "StartRecord")
    print(f"Recording: {a.title}")
    if a.speakers:
        print("Speakers mode: your mic track will be checked for echoes of the other side.")


def cmd_stop(a):
    cl = obs_client()
    if not req(cl, "GetRecordStatus").get("outputActive"):
        sys.exit("OBS is not recording.")
    path = req(cl, "StopRecord")["outputPath"]
    meta = json.load(open(PENDING)) if os.path.exists(PENDING) else {}
    meta.update(stopped=dt.datetime.now().isoformat(timespec="seconds"), recording=path)
    json.dump(meta, open(sidecar_path(path), "w"), indent=2)
    if os.path.exists(PENDING):
        os.remove(PENDING)
    if a.discard:
        # a no-show or unusable audio: nothing is transcribed, and the recording and its
        # sidecar go straight to the Bin (recoverable there until it is emptied)
        if not wait_until_written(cl, path):
            print("OBS had not finished writing the file after 60 s; binning it anyway")
        failed = False
        for f in (path, sidecar_path(path)):
            err = to_bin(f)
            if err:
                failed = True
                print(f"could not move {f} to the Bin: {err}")
        print(f"Stopped, not transcribed: {path}" + ("" if failed else " moved to the Bin"))
        return
    if not wait_until_written(cl, path):
        print("OBS had not finished writing the file after 60 s; transcribing it anyway")
    os.makedirs(LOG_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    log = open(os.path.join(LOG_DIR, base + ".log"), "w")
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "process", path],
                     stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     start_new_session=True)
    print(f"Stopped: {path}")
    print(f"Transcribing in the background. Progress: meeting status")


def cmd_status(a):
    try:
        s = req(obs_client(), "GetRecordStatus")
        print("OBS recording:", f"yes, {s.get('outputTimecode', '')}" if s.get("outputActive") else "no")
    except SystemExit as e:
        print("OBS:", e)
    except Exception as e:
        print("OBS: not reachable,", type(e).__name__)
    if os.path.isdir(LOG_DIR):
        for f in sorted(x for x in os.listdir(LOG_DIR) if x.endswith(".status"))[-8:]:
            last = open(os.path.join(LOG_DIR, f)).read().strip().splitlines()[-1]
            print(f"  {f[:-7]}: {last}")


# ---------- processing ----------
def audio_streams(path):
    return run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                "stream=index", "-of", "csv=p=0", path]).split()


def extract(path, i, wav):
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", path, "-map", f"0:a:{i}",
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav])


def wav_seconds(wav):
    with wave.open(wav) as w:
        return w.getnframes() / w.getframerate()


def build_prompt(attendees, vocab):
    """Names and terms that genuinely occur, attendees first, inside whisper's prompt cap."""
    terms, seen, out = [], set(), ""
    for t in ([YOUR_NAME] if YOUR_NAME else []) + attendees + split_names(vocab):
        if t.lower() not in seen:
            seen.add(t.lower())
            terms.append(t)
    for t in terms:
        nxt = f"{out}, {t}" if out else t
        if len(nxt) > PROMPT_BUDGET:
            break
        out = nxt
    return out


def whisper(wav, base, lang, prompt):
    threads = run(["sysctl", "-n", "hw.perflevel0.logicalcpu"]).strip() or "8"
    cmd = ["whisper-cli", "-m", MODEL, "-f", wav, "-l", lang, "-t", threads, "-ojf", "-of", base, "-np"]
    if prompt:
        cmd += ["--prompt", prompt, "--carry-initial-prompt"]
    if os.path.exists(VAD_MODEL):  # skips silence, so whisper has nothing to invent over
        cmd += ["--vad", "-vm", VAD_MODEL]
    else:
        print(f"no VAD model at {VAD_MODEL}; transcribing without it")
    run(cmd)
    return json.load(open(base + ".json"))


def segments(wj):
    for s in wj.get("transcription", []):
        t = s["text"].strip()
        if t:
            yield s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, t


def diarise(wav):
    import numpy as np
    import torch
    from pyannote.audio import Pipeline
    with wave.open(wav) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    audio = {"waveform": torch.from_numpy(x).unsqueeze(0), "sample_rate": sr}
    try:
        pipe = Pipeline.from_pretrained(SPEAKER_MODEL)
    except Exception as e:
        raise RuntimeError(f"the speaker model {SPEAKER_MODEL} is not on this Mac "
                           f"(setup step 4 in the README downloads it): {type(e).__name__}") from e
    if pipe is None:
        raise RuntimeError(f"the speaker model {SPEAKER_MODEL} is not on this Mac "
                           "(setup step 4 in the README downloads it)")
    for device in ("mps", "cpu"):
        try:
            pipe.to(torch.device(device))
            out = pipe(audio)
            ann = getattr(out, "exclusive_speaker_diarization", None)
            if ann is None:
                ann = getattr(out, "speaker_diarization", out)
            return [(s.start, s.end, spk) for s, _, spk in ann.itertracks(yield_label=True)], device
        except Exception as e:
            print(f"diarisation on {device} failed: {type(e).__name__}: {e}")
    raise RuntimeError("diarisation failed on both mps and cpu")


def loudness(wav):
    """RMS level in dB for each FRAME of the file."""
    import numpy as np
    with wave.open(wav) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(sr * FRAME)
    n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-9)


def speech_span(db, s, e, min_frames=3):
    """Where sound actually is inside whisper's [s, e]. None means the text sits over silence,
    which whisper invents (its "Thank you." habit). Whisper's own start times drift across
    long silences, so the audio level decides them instead."""
    i0, i1 = int(s / FRAME), min(len(db), int(e / FRAME) + 1)
    loud = [i for i in range(i0, i1) if db[i] > SPEECH_DB]
    if len(loud) < min_frames:
        return None
    return loud[0] * FRAME, (loud[-1] + 1) * FRAME


def gate(segs, db, speaker):
    out, dropped = [], []
    for s, e, t in segs:
        span = speech_span(db, s, e)
        if span is None:
            dropped.append(t)
        else:
            out.append((span[0], span[1], speaker, t))
    return out, dropped


def overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def speaker_at(t, turns):
    best, bestd = None, float("inf")
    for s, e, spk in turns:
        if s <= t <= e:
            return spk
        d = min(abs(t - s), abs(t - e))
        if d < bestd:
            best, bestd = spk, d
    return best or "SPEAKER_00"


def split_segment(seg, turns, s, e):
    """Split one whisper segment at the turn change inside it, snapped to the nearest
    punctuation so a sentence is not cut mid-phrase."""
    toks = [tk for tk in seg.get("tokens", []) if not tk["text"].startswith(("[_", "<|"))]
    if len(toks) < 2:
        return None
    inside = sorted(t for t in turns if overlap(s, e, t[0], t[1]) > 0)
    cut = next((inside[k + 1][0] for k in range(len(inside) - 1) if inside[k][2] != inside[k + 1][2]), None)
    if cut is None:
        return None
    k = min(range(1, len(toks)), key=lambda i: abs(toks[i]["offsets"]["from"] / 1000 - cut))
    ends = [i for i in range(max(1, k - 5), min(len(toks), k + 6)) if toks[i - 1]["text"].strip()[-1:] in ".?!,"]
    if ends:
        k = min(ends, key=lambda i: abs(i - k))
    parts = []
    for a, b in ((0, k), (k, len(toks))):
        text = "".join(tk["text"] for tk in toks[a:b]).strip()
        if text:
            ps, pe = toks[a]["offsets"]["from"] / 1000, toks[b - 1]["offsets"]["to"] / 1000
            spk = max(turns, key=lambda t: overlap(ps, pe, t[0], t[1]))[2]
            parts.append((ps, pe, spk, text))
    return parts


def assign_speakers(wj, turns, db, min_share=0.3, min_secs=1.0):
    """One speaker per whisper segment, by overlap with pyannote's turns. Whisper already
    breaks segments at turn changes almost every time, so a segment is split only when a
    second speaker holds at least min_secs and min_share of it."""
    out, dropped = [], []
    for seg in wj.get("transcription", []):
        text = seg["text"].strip()
        if not text:
            continue
        span = speech_span(db, seg["offsets"]["from"] / 1000, seg["offsets"]["to"] / 1000)
        if span is None:
            dropped.append(text)
            continue
        s, e = span
        share = {}
        for t0, t1, spk in turns:
            share[spk] = share.get(spk, 0.0) + overlap(s, e, t0, t1)
        ranked = sorted(((v, k) for k, v in share.items() if v > 0), reverse=True)
        if not ranked:
            out.append((s, e, speaker_at((s + e) / 2, turns), text))
            continue
        if len(ranked) > 1 and ranked[1][0] >= max(min_secs, min_share * (e - s)):
            parts = split_segment(seg, turns, s, e)
            if parts:
                out.extend(parts)
                continue
        out.append((s, e, ranked[0][1], text))
    return out, dropped


PIECE_SPLIT = re.compile(r"(?<=[.?!])\s+|\s+-\s+|^\s*-\s+")


def mic_pieces(segs):
    """Speakers mode: cut each mic segment at sentence ends and at the '-' whisper inserts when
    it hears a change of speaker, so an echo of the other side and the local speaker's reply
    that share a segment are judged separately, as in "...the end of the other side's sentence.
    - Okay, and my reply". Times are shared out by character position inside the segment,
    which relies only on the segment's own (correct) start and end."""
    out = []
    for s, e, text in segs:
        parts = [re.sub(r"^-\s+", "", p.strip()) for p in PIECE_SPLIT.split(text) if p and p.strip()]
        parts = [p for p in parts if p]
        total, pos = sum(len(p) for p in parts) or 1, 0
        for part in parts:
            ps = s + (e - s) * pos / total
            pos += len(part)
            out.append((ps, s + (e - s) * pos / total, part))
    return out


def drop_echoes(lines, window=1.5, threshold=0.6):
    """Speakers mode: a mic line mostly made of words the remote side said at the same
    moment is the room, not the local speaker, so it goes."""
    mine = [l for l in lines if l[2] == ME]
    theirs = [l for l in lines if l[2] != ME]
    keep, removed = [], []
    for s, e, spk, t in mine:
        near = [w for ss, ee, _, tt in theirs if ss < e + window and ee > s - window for w in words(tt)]
        a = words(t)
        if a and near:
            sm = difflib.SequenceMatcher(None, a, near, autojunk=False)
            if sum(b.size for b in sm.get_matching_blocks()) / len(a) >= threshold:
                removed.append((s, t))
                continue
        keep.append((s, e, spk, t))
    return keep + theirs, removed


def merge_runs(lines, gap=1.0, maxlen=240):
    out = []
    for s, e, spk, t in lines:
        if out and out[-1][2] == spk and s - out[-1][1] <= gap and len(out[-1][3]) + len(t) < maxlen:
            ps, pe, _, pt = out[-1]
            out[-1] = (ps, max(pe, e), spk, f"{pt} {t}")
        else:
            out.append((s, e, spk, t))
    return out


def checks(mic, rem, turns):
    """The hallucination checks from the transcribe-audio skill, Step 5."""
    w = []
    for name, wj in (("mic", mic), ("remote", rem)):
        prev, run_len = None, 0
        for _, _, t in segments(wj):
            k = t.lower().strip(" .!?,")
            run_len = run_len + 1 if k == prev else 1
            prev = k
            if run_len == 3:
                w.append(f"{name} track: the same line three or more times in a row: {t[:60]!r}")
            if STOCK.search(t):
                w.append(f"{name} track: stock phrase nobody is likely to have said: {t[:60]!r}")
            letters = [c for c in t if c.isalpha()]
            if letters and sum(ord(c) > 0x24F for c in letters) / len(letters) > 0.5:
                w.append(f"{name} track: non-Latin text, possibly the wrong language: {t[:60]!r}")
    speech = sum(e - s for s, e, _ in turns)
    remote_words = sum(len(t.split()) for _, _, t in segments(rem))
    if speech > 30 and remote_words < 0.3 * 2.2 * speech:
        w.append(f"remote transcript looks short: {remote_words} words for {speech:.0f} s of speech")
    return list(dict.fromkeys(w))[:15]


def write_transcript(out_md, date, title, attendees, recording, private, lines):
    people = [ME] + [n for n in attendees if n != ME]
    fm = ["---", f"date: {date}", 'title: "{}"'.format(title.replace('"', '\\"')),
          "attendees:"] + [f'  - "{p}"' for p in people]
    fm += [f'recording: "{recording}"', "source: local-whisper", f"private: {'true' if private else 'false'}", "---", ""]
    open(out_md, "w", encoding="utf-8").write("\n".join(fm + [f"{ts(s)} {spk}: {t}" for s, _, spk, t in lines]) + "\n")


def process(path, a):
    meta = load_sidecar(path)
    title = a.title or meta.get("title") or os.path.splitext(os.path.basename(path))[0]
    attendees = split_names(a.attendees) if a.attendees else meta.get("attendees", [])
    vocab = a.vocab if a.vocab is not None else meta.get("vocab", "")
    speakers_mode = a.speakers or meta.get("speakers_mode", False)
    private = a.private or meta.get("private", False)
    lang = a.lang or meta.get("lang") or "en"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", meta.get("started", "") or os.path.basename(path))
    date = m.group(1) if m else dt.date.today().isoformat()
    name = safe(f"{date} {title}")
    outdir = os.path.join(REC_DIR, name)
    out_md = os.path.join(outdir, f"{name}.md")
    if os.path.exists(out_md) and not a.force:
        print(f"Exists, not overwriting (use --force): {out_md}")
        return 3
    streams = audio_streams(path)
    if len(streams) < 2:
        print(f"Expected mic and remote tracks, found {len(streams)} audio stream(s).")
        return 2
    work = os.path.join(outdir, ".work")
    os.makedirs(work, exist_ok=True)
    try:
        mic_wav, rem_wav = os.path.join(work, "mic.wav"), os.path.join(work, "remote.wav")
        extract(path, 0, mic_wav)
        extract(path, 1, rem_wav)
        prompt = build_prompt(attendees, vocab)
        got, full = wav_seconds(rem_wav), recording_seconds(path)
        short = f"extracted {got:.1f} s of a {full:.1f} s recording; the file may not have been finished" \
            if full and got < full - 2 else None
        t0 = time.time()
        print(f"[{now()}] {got:.0f} s of audio; prompt: {prompt!r}")
        mic = whisper(mic_wav, os.path.join(work, "mic"), lang, prompt)
        t1 = time.time()
        rem = whisper(rem_wav, os.path.join(work, "remote"), lang, prompt)
        t2 = time.time()
        turns, device = diarise(rem_wav)
        t3 = time.time()
        print(f"[{now()}] whisper mic {t1 - t0:.1f} s, remote {t2 - t1:.1f} s; pyannote {t3 - t2:.1f} s on {device}")

        mic_db, rem_db = loudness(mic_wav), loudness(rem_wav)
        mic_segs = list(segments(mic))
        if speakers_mode:
            mic_segs = mic_pieces(mic_segs)
        mine, mic_dropped = gate(mic_segs, mic_db, ME)
        theirs, rem_dropped = assign_speakers(rem, turns, rem_db)
        lines = mine + theirs
        removed = []
        if speakers_mode:
            lines, removed = drop_echoes(lines)
        lines = [(s0, e0, spk, re.sub(r"^\s*-\s+", "", t)) for s0, e0, spk, t in lines]  # whisper's turn dash
        lines = merge_runs(sorted(lines, key=lambda x: x[0]))

        remote_names = [n for n in attendees if n != ME]
        labels = sorted({l[2] for l in lines if l[2] != ME})
        speaker_map = meta.get("speaker_map") or {}
        if not speaker_map and len(remote_names) == 1 and labels:
            dominant = max(labels, key=lambda lab: sum(e - s for s, e, spk, _ in lines if spk == lab))
            speaker_map = {dominant: remote_names[0]}
        lines = [(s, e, speaker_map.get(spk, spk), t) for s, e, spk, t in lines]

        warnings = checks(mic, rem, turns)
        if len(rem_db) == 0 or float(rem_db.max()) < -120:  # never above -120 dB: nothing reached OBS
            warnings.insert(0, "THE REMOTE TRACK IS SILENT FOR THE WHOLE RECORDING: no call audio reached OBS, so "
                               f"every line is attributed to {ME}. Check the Remote audio source and OBS's "
                               "screen-recording permission (a source that captures one application records silence "
                               "when the call is in another application)")
        if short:
            warnings.insert(0, short)
        if not lines:
            warnings.insert(0, "the transcript has no lines")
        dropped = [f"{t!r} (mic)" for t in mic_dropped] + [f"{t!r} (remote)" for t in rem_dropped]
        unnamed = sorted({l[2] for l in lines if l[2].startswith("SPEAKER_")})
        if unnamed:
            warnings.append(f"unnamed remote speakers {', '.join(unnamed)}: "
                            f'meeting name "{path}" SPEAKER_00="Full Name"')

        write_transcript(out_md, date, title, attendees, path, private, lines)
        meta.update(title=title, attendees=attendees, transcript=out_md, private=private,
                    speaker_map=speaker_map, diarisation_device=device, warnings=warnings, dropped=dropped,
                    echoes_removed=[f"{ts(s)} {t}" for s, t in removed], processed=now(),
                    checks_passed=not check_warnings(warnings),
                    status="needs-review" if warnings else "ok")
        json.dump(meta, open(sidecar_path(path), "w"), indent=2)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"[{now()}] wrote {out_md}")
    if dropped:
        print(f"removed {len(dropped)} line(s) of text sitting over silence: {', '.join(dropped)[:300]}")
    if removed:  # normal in speakers mode, not a failed check, so not a warning
        print(f"speakers mode removed {len(removed)} mic line(s) that repeated the other side:")
        for s0, t in removed:
            print(f"    {ts(s0)} {t}")
    for w in warnings:
        print("WARNING:", w)
    try:
        for m in (prune() if RETAIN_DAYS else []):
            print(f"retention: moved to the Bin after {RETAIN_DAYS} days: {m}")
    except Exception as e:  # retention must never fail a transcription
        print(f"retention step skipped: {type(e).__name__}: {e}")
    return 0


def transcript_lines(md):
    """Number of spoken lines ([hh:mm:ss] Speaker: text) in a transcript."""
    return len(re.findall(r"^\[\d\d:\d\d:\d\d\] ", open(md, encoding="utf-8").read(), flags=re.M))


def check_warnings(warnings):
    """Warnings that mean a check failed. Unnamed speakers are a naming task, not a failure."""
    return [w for w in warnings if not w.startswith("unnamed remote speakers")]


def prune(days=RETAIN_DAYS or 30, dry_run=False):
    """Move a recording to the Bin `days` after its transcript passed its checks. Audio whose
    transcript failed a check stays. Only the audio goes: sidecar and transcript remain."""
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    moved = []
    if not os.path.isdir(REC_DIR):
        return moved
    for f in sorted(os.listdir(REC_DIR)):
        if not f.endswith(".json") or f.startswith("."):
            continue
        side = os.path.join(REC_DIR, f)
        try:
            meta = json.load(open(side))
        except Exception:
            continue
        audio = meta.get("recording") or os.path.splitext(side)[0] + ".mkv"
        done = meta.get("processed")
        if not (os.path.exists(audio) and done and meta.get("checks_passed")
                and meta.get("transcript") and os.path.exists(meta["transcript"])):
            continue
        if not transcript_lines(meta["transcript"]):
            continue
        if dt.datetime.strptime(done, "%Y-%m-%d %H:%M:%S") > cutoff:
            continue
        if dry_run:
            moved.append(audio)
            continue
        err = to_bin(audio)
        if err:
            print(f"could not move {audio} to the Bin: {err}")
        else:
            meta["audio_removed"] = now()
            json.dump(meta, open(side, "w"), indent=2)
            moved.append(audio)
    return moved


def cmd_prune(a):
    moved = prune(a.days, a.dry_run)
    verb = "would move" if a.dry_run else "moved"
    print(f"{verb} {len(moved)} recording(s) older than {a.days} days to the Bin" + "".join(f"\n  {m}" for m in moved))


def cmd_process(a):
    path = os.path.abspath(os.path.expanduser(a.file))
    base = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(LOG_DIR, exist_ok=True)
    status = os.path.join(LOG_DIR, base + ".status")
    open(status, "w").write(f"STARTED {os.getpid()} {now()}\n")
    rc = 1
    try:
        rc = process(path, a)
    except Exception:
        traceback.print_exc()
    finally:
        with open(status, "a") as f:
            f.write(f"ENDED rc={rc} {now()}\n")
    sys.exit(rc)


def cmd_name(a):
    path = os.path.abspath(os.path.expanduser(a.file))
    meta = load_sidecar(path)
    out_md = meta.get("transcript")
    if not out_md or not os.path.exists(out_md):
        sys.exit("No transcript recorded for that file yet.")
    bad = [kv for kv in a.pairs if "=" not in kv]
    if bad:
        sys.exit(f'Give each speaker as LABEL="Name", for example SPEAKER_00="Ana Silva". Not understood: {" ".join(bad)}')
    mapping = dict(kv.split("=", 1) for kv in a.pairs)
    text = open(out_md, encoding="utf-8").read()
    for lab, name in mapping.items():
        text = re.sub(rf"^(\[\d\d:\d\d:\d\d\]) {re.escape(lab)}:", lambda m, n=name: f"{m.group(1)} {n}:", text, flags=re.M)
        entry = f'  - "{name}"'
        if entry not in text:
            text = text.replace("attendees:\n", f"attendees:\n{entry}\n", 1)
    open(out_md, "w", encoding="utf-8").write(text)
    meta.setdefault("speaker_map", {}).update(mapping)
    meta["warnings"] = [w for w in meta.get("warnings", []) if not w.startswith("unnamed remote speakers")]
    json.dump(meta, open(sidecar_path(path), "w"), indent=2)
    print("renamed:", mapping)


def main():
    ap = argparse.ArgumentParser(prog="meeting", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--attendees", help="comma-separated names, as they should be spelled")
        p.add_argument("--vocab", help="comma-separated terms whisper should expect")
        p.add_argument("--speakers", action="store_true", help="laptop speakers, not headphones: remove echoes")
        p.add_argument("--private", action="store_true", help="mark so the transcript never goes to Claude")
        p.add_argument("--lang", help="language code, default en")

    p = sub.add_parser("start", help="start recording")
    p.add_argument("title")
    common(p)
    p.set_defaults(fn=cmd_start)
    p = sub.add_parser("stop", help="stop and transcribe in the background")
    p.add_argument("--discard", action="store_true",
                   help="no-show or unusable audio: skip transcription, move the recording to the Bin")
    p.set_defaults(fn=cmd_stop)
    sub.add_parser("status", help="recording state and recent jobs").set_defaults(fn=cmd_status)
    p = sub.add_parser("process", help="transcribe a recording")
    p.add_argument("file")
    p.add_argument("--title")
    p.add_argument("--force", action="store_true")
    common(p)
    p.set_defaults(fn=cmd_process)
    p = sub.add_parser("prune", help=f"move recordings older than {RETAIN_DAYS or 30} days to the Bin")
    p.add_argument("--days", type=int, default=RETAIN_DAYS or 30)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_prune)
    p = sub.add_parser("name", help="replace SPEAKER_nn labels with names")
    p.add_argument("file")
    p.add_argument("pairs", nargs="+", metavar='SPEAKER_00="Name"')
    p.set_defaults(fn=cmd_name)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
