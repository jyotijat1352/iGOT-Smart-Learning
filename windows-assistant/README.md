# iGOT Smart Learning Assistant — Windows 11 (Ollama Local AI)

A local desktop study companion for permitted practice and learning material. It uses Tesseract OCR to read visible screen text and a local Ollama model to explain concepts in Hindi. It is intended for practice and learning, not official examinations or graded assessments.

## One-time setup
1. Install Ollama for Windows from https://ollama.com/download/windows.
2. Open PowerShell and run: `ollama pull qwen2.5:1.5b`
3. Wait for the model download to finish. The model is about 1 GB; keep extra free disk space.
4. Start Ollama (it normally runs in the background), then open `iGOT-Smart-Learning.exe`.
5. No Gemini API key, account, or paid API is required.

## About the 8 GB RAM configuration
The app defaults to `qwen2.5:1.5b`, a small model chosen to be more practical on an 8 GB RAM Windows laptop. Response speed and quality depend on CPU, available memory, and other running apps. Close heavy apps if it is slow. A discrete GPU is not required; Ollama can run on CPU.

## Use
- Keep the permitted practice page on the left side of the display.
- Keep this assistant on the right.
- Press Start reading to recognize changed visible text and request a Hindi learning explanation.
- Press Stop when finished.

## Important limitations
- Ollama and the model are separate downloads; the Windows app ZIP does not bundle the Ollama runtime or model weights.
- The first model download requires internet. After download, inference runs locally and does not require an API key or send prompts to a cloud model.
- Some apps/websites protect screen contents. If Windows capture returns a blank/black image or OCR cannot read the content, this app cannot read it and does not bypass protection.
- OCR may misread text. If the question is unclear, verify it manually. The app does not click options or submit answers.
