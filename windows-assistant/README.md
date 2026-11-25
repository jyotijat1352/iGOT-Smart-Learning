# iGOT Smart Learning Assistant — Windows 11

A desktop study companion that reads text visible in a selected screen area and displays an educational explanation in a side panel. It is intended for practice and learning, not for use during official examinations or graded assessments.

## Important limitation
Some apps and websites deliberately protect their screen contents. If Windows returns a blank/black image or OCR cannot read the protected content, this app cannot read it and does not bypass that protection. Use only where screen capture is permitted.

## Setup (developer/source)
1. Install Python 3.11 on Windows 11.
2. Install Tesseract OCR and its English and Hindi language data.
3. Open PowerShell in this folder and run `py -m pip install -r requirements.txt`.
4. Run `py main.py`.
5. Add your Gemini API key in Settings. The key is saved in Windows Credential Manager via `keyring`; never put it in source code or GitHub.

## Use
- Keep iGOT/browser on the left side of the screen.
- Keep this assistant on the right.
- Press Start reading. The app checks the selected left-side area periodically, recognizes changed text and asks Gemini for the correct option, full answer and Hindi explanation.
- Stop reading when finished.

The app does not click options, submit answers, or automate assessment actions. OCR accuracy depends on screen clarity, language data, scaling and whether the source permits capture.
