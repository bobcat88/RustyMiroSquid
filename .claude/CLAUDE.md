

<!-- TTS_VOICE_OUTPUT_START -->
## Voice Output (TTS)

When responding, wrap your natural language prose in `«tts»...«/tts»` markers for text-to-speech.

Rules:
- ONLY wrap conversational prose meant to be spoken aloud
- Do NOT wrap: code, file paths, commands, tool output, URLs, lists, errors
- Keep markers on same line as text (no line breaks inside)

Examples:
✓ «tts»I'll help you fix that bug.«/tts»
✓ «tts»The tests are passing.«/tts» Here's what changed:
✗ «tts»src/Header.tsx«/tts»  (file path - don't wrap)
✗ «tts»npm install«/tts»  (command - don't wrap)
<!-- TTS_VOICE_OUTPUT_END -->

<!-- BORG_KNOWLEDGE_WORKFLOW_START -->
## Borg Knowledge Vault & AI Workflow

- Shared memory lives in `/home/_johan/Documents/Borg`. Start with `300 Entities/Projects/Portfolio - Condensed Knowledge.md`, `400 Resources/Tech/AI Knowledge Map.md`, `000 OS / Meta/AI Collaboration Protocol.md`, and `300 Entities/People/Johan - Working Profile.md`.
- For this repo, also read `AGENTS.md`, `GEMINI.md`, `backend/GEMINI.md`, `frontend/GEMINI.md`, and the vault symlink `300 Entities/Projects/RustyMiroSquid`.
- Use Beads when present, kspec when present, GitNexus before symbol edits, and RTK for noisy output when useful.
- Mirror durable simulation, AI, and trading research back into the vault instead of leaving it only in chat.
<!-- BORG_KNOWLEDGE_WORKFLOW_END -->
