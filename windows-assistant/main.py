import os, sys, time, threading, hashlib, json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import keyring
import pytesseract
from PIL import Image
import mss

APP_NAME = "iGOT Smart Learning Assistant"
SERVICE = "igot-smart-learning-gemini"
MODEL = "gemini-3.8-flash"


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)

# Prefer the bundled Tesseract executable in packaged builds.
bundled_tesseract = resource_path(os.path.join("tesseract", "tesseract.exe"))
if os.path.exists(bundled_tesseract):
    pytesseract.pytesseract.tesseract_cmd = bundled_tesseract

class Assistant:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("510x760+900+80")
        self.root.minsize(420, 560)
        self.root.attributes("-topmost", True)
        self.running = False
        self.worker = None
        self.last_hash = ""
        self.last_call = 0
        self.api_key = keyring.get_password(SERVICE, "gemini_api_key") or ""
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="iGOT Smart Learning Assistant", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Practice & learning companion • Hindi explanations", foreground="#536273").pack(anchor="w", pady=(2, 10))
        warning = tk.Label(outer, text="केवल अभ्यास और पढ़ाई के लिए। आधिकारिक परीक्षा/graded test में उपयोग न करें।\nProtected screen को यह ऐप bypass नहीं करता।", bg="#fff2d6", fg="#684500", justify="left", padx=10, pady=8, wraplength=460)
        warning.pack(fill="x", pady=(0, 10))
        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 8))
        self.start_btn = ttk.Button(controls, text="Start reading", command=self.start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(controls, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(controls, text="Gemini API key", command=self.set_key).pack(side="right")
        self.status = tk.StringVar(value="Ready — iGOT को स्क्रीन के बाएँ हिस्से में रखें")
        ttk.Label(outer, textvariable=self.status, wraplength=460).pack(anchor="w", pady=(0, 8))
        ttk.Label(outer, text="पहचाना गया प्रश्न", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.question = tk.Text(outer, height=8, wrap="word", font=("Segoe UI", 10))
        self.question.pack(fill="x", pady=(4, 10))
        ttk.Label(outer, text="पूरा उत्तर और हिंदी में व्याख्या", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.answer = tk.Text(outer, wrap="word", font=("Segoe UI", 10))
        self.answer.pack(fill="both", expand=True, pady=(4, 0))
        self.answer.insert("1.0", "यहाँ उत्तर दिखाई देगा।\n\n1. Gemini API key जोड़ें।\n2. iGOT/browser को स्क्रीन के बाएँ भाग में रखें।\n3. Start reading दबाएँ।")
        self.answer.configure(state="disabled")

    def set_key(self):
        key = simpledialog.askstring("Gemini API key", "अपनी Gemini API key यहाँ डालें (यह आपके Windows Credential Manager में रखी जाएगी):", show="*")
        if key and key.strip():
            self.api_key = key.strip()
            keyring.set_password(SERVICE, "gemini_api_key", self.api_key)
            messagebox.showinfo("Saved", "API key इस Windows user account में सुरक्षित रख दी गई है।")

    def start(self):
        if not self.api_key:
            messagebox.showwarning("API key required", "पहले Gemini API key जोड़ें।")
            self.set_key()
            if not self.api_key:
                return
        if self.running:
            return
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status.set("Reading left side of screen…")
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def stop(self):
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status.set("Stopped")

    def loop(self):
        while self.running:
            try:
                with mss.mss() as sct:
                    mon = sct.monitors[1]
                    # Read the left 68% of the primary display; keep the assistant on the right.
                    region = {"left": mon["left"], "top": mon["top"], "width": int(mon["width"] * 0.68), "height": mon["height"]}
                    shot = sct.grab(region)
                    img = Image.frombytes("RGB", shot.size, shot.rgb)
                text = pytesseract.image_to_string(img, lang="eng+hin", config="--psm 6")
                text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
                if len(text) >= 35:
                    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    if digest != self.last_hash and time.time() - self.last_call > 3:
                        self.last_hash = digest
                        self.last_call = time.time()
                        self.root.after(0, self.show_question, text)
                        threading.Thread(target=self.ask_gemini, args=(text,), daemon=True).start()
                else:
                    self.root.after(0, self.status.set, "स्क्रीन पर पढ़ने योग्य प्रश्न नहीं मिला — स्क्रीन/अनुमति जाँचें")
            except Exception as e:
                self.root.after(0, self.status.set, "OCR error: " + str(e)[:180])
            time.sleep(3)

    def show_question(self, text):
        self.question.delete("1.0", "end")
        self.question.insert("1.0", text[:7000])
        self.status.set("नया स्क्रीन टेक्स्ट मिला — उत्तर तैयार हो रहा है…")

    def ask_gemini(self, screen_text):
        prompt = (
            "You are a patient Hindi study tutor. The following is OCR text from a learner's practice material. "
            "Identify the most likely question and its options. Give the correct option if it is a practice question, "
            "then the complete answer and a clear Hindi explanation. If the OCR is incomplete or ambiguous, say so "
            "and do not guess. Do not interact with the source app.\n\nSCREEN TEXT:\n" + screen_text[:7000]
        )
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
            response = None
            # Retry temporary provider overload/rate-limit/server errors with backoff.
            for attempt, wait_seconds in enumerate((0, 3, 8, 15), start=1):
                if wait_seconds:
                    self.root.after(0, self.status.set, f"Gemini server busy — retry {attempt - 1}/3…")
                    time.sleep(wait_seconds)
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code not in (429, 500, 502, 503, 504):
                    break
            if response is None or response.status_code != 200:
                code = response.status_code if response is not None else "unknown"
                detail = response.text[:500] if response is not None else "No response"
                raise RuntimeError(f"Gemini API {code} after retries: {detail}")
            data = response.json()
            answer = data["candidates"][0]["content"]["parts"][0]["text"]
            self.root.after(0, self.show_answer, answer)
        except Exception as e:
            self.root.after(0, self.show_answer, "उत्तर प्राप्त नहीं हुआ।\n\n" + str(e))

    def show_answer(self, text):
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", text)
        self.answer.configure(state="disabled")
        self.status.set("उत्तर अपडेट हो गया")

    def close(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        style = ttk.Style()
        style.theme_use("vista")
    except Exception:
        pass
    Assistant(root)
    root.mainloop()
