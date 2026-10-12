---
name: paper-to-audio
description: "Turn a PDF paper into an MP3 narration locally, with display equations explained in words, using the pdf2audio pipeline through the bundled `paper-audio` script. Use whenever the user wants to listen to a paper rather than read it. Triggers include: 'make audio of this paper', 'turn this paper into audio', 'I want to listen to this', 'narrate this PDF', 'read this paper to me', 'make an MP3 of this', 'paper to audio', any PDF handed over to be listened to. Runs end to end without Claude reading the paper, so review drafts and confidential manuscripts stay out of the conversation. Boundaries: audio that needs turning into text is transcribe-audio; reviewing or summarising a paper's content is paper-review or a direct read."
---

# Paper to audio

Use `paper-audio`, the script in this skill's folder, to run the whole pdf2audio pipeline. It
extracts and cleans the text, explains each display equation in words with a local vision model
(Ollama, `qwen3.5:35b-a3b`), and narrates with Kokoro on MLX. Nothing from the paper leaves the
machine, and you do not need to read it.

## What it needs

The pipeline comes from the pdf2audio repository
(https://github.com/jonstraveladventures/pdf2audio) and is installed separately from this
plugin. The plugin ships only the `paper-audio` script.

    brew install uv ffmpeg
    uv tool install --python 3.12 git+https://github.com/jonstraveladventures/pdf2audio

This installs `pdf2audio`, which `paper-audio` calls, and `tts` into `~/.local/bin`. If that
folder is not on PATH, `uv tool update-shell` adds it, or set `PDF2AUDIO` to the command's
full path when running `paper-audio`. The first run downloads Kokoro's weights and voices
(under 400 MB). Equation explanations are enabled by default and need Ollama with
`qwen3.5:35b-a3b` (`ollama pull qwen3.5:35b-a3b`, about 23 GB). Without it, run with
`--no-explain`.

If `paper-audio` reports that pdf2audio is not found, tell the user the pipeline is not
installed and give them the steps above. Do not install packages yourself.

## Reading the paper and the licence rule

Do not open the PDF or the narrated `.txt` unless the user asks for something that needs them.
The point of the skill is that the user's papers, including drafts under double-blind review,
stay out of the conversation. The command's summary is computed from the output alone and is
what you report.

The pipeline sends nothing from the paper off the machine. The only outside request found in
testing asks Hugging Face whether the voice model has changed, so none of the paper's text goes
to an AI service. Reading the PDF or the narrated `.txt` in Claude sends the paper's full text
to an AI service. Under this toolkit's papers plugin licence rule, a subscription paper's full
text goes to no AI service, Claude included. Read these files only for a paper with an open
licence. The papers plugin's licence-check hook may also refuse the `paper-audio` command on a
PDF it identifies as a subscription copy or a manuscript under review, as the hook cannot tell
that this pipeline runs locally. If it refuses, tell the user and leave lifting the refusal to
the user's own words in the chat. Do not bypass a refusal by building the path in a shell
variable or by any other route.

## Steps

1. **Check the file.** Confirm the path exists and is a PDF (`ls -l`, `pdfinfo | grep
   Pages`). A prompt that implies a file does not mean the file is there.

2. **Ask one question: include the appendices?** Default to asking every time; the user
   sometimes wants them and sometimes not. Explaining equations is the default and needs no
   question, and so is the checking pass that follows it; offer `--no-check` if the user wants
   speed, and `--no-explain` only if they want much more speed or Ollama is unavailable.

3. **Check Ollama** (explanations only): `ollama list | grep qwen3.5:35b-a3b`. If Ollama is
   not running, say so and offer `--no-explain` rather than starting services yourself.

4. **Give the time estimate, then run it in the background** (run_in_background, not `&`).
   Allow about one to several minutes per page with equations, depending on how long the
   model thinks, plus a few minutes of narration. Report the actual time when it finishes.

       "${CLAUDE_SKILL_DIR}/paper-audio" [--no-appendices] [--no-check] [--no-explain] [--voice ID] "<paper.pdf>"

   Several PDFs can go in one call. Output lands beside each PDF: `<paper>.mp3` and
   `<paper>.txt`; the log goes to `~/Library/Logs/paper-audio/`.

5. **Report from the summary** it prints: the MP3's location and length, the number of equations
   explained, and any `CHECK:` lines. A `FAILED:` line means no audio was made for that paper.
   It gives pdf2audio's error or says pdf2audio finished without writing a new file. Read the
   log it names. Explain a CHECK line in plain terms:
   - *equations not explained*: the model skipped or failed on a page. Those with a number
     are read as "Equation 3.6."; those without one are left out of the narration
     altogether. A rerun usually fills them.
   - *the MP3's length could not be read*: the audio file is damaged. Read the log before
     doing anything else.
   - *pages of equations were not checked*: the model ran out of room while checking;
     those explanations went out unchecked.
   - *leftover markers or tags*: an extraction bug in pdf2audio; worth fixing in the
     project, not something to fix by hand in the output.
   - *reference-like lines*: the reference list was not recognised and is being read.
   - *speaking rate outside 100–220 words/min* (normal is about 115–130 with pauses): long
     silences or garbled text; look at the log, and only then, with the user's agreement, at
     the text.

   Do not claim more than the checks show. They detect pipeline failures but cannot tell
   whether an equation's explanation is correct. The model samples its answers, so a first
   pass can get a sign or grouping wrong. In a test on two papers, the checking pass fixed
   all four errors it was shown and introduced none in about 60 correct explanations. It
   does not detect a wrong name unless the page itself contradicts it. Use the explanation
   as a guide to the equation, not a substitute for it.

## Also available without Claude

`paper-audio` is a plain command, so the user can run it from a terminal without Claude.
`--notify` posts a macOS notification when each paper is done. Mention it if the user seems to
want this routinely.

## Known limits

- Inline maths inside sentences is read symbol by symbol; only display equations are
  explained.
- Tables are replaced by "Table omitted." with the caption kept.
- Two-column pages where the layout analysis fails are not rebuilt; single-column review
  drafts are.
