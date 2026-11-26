import os, sys, time, threading, hashlib, json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import pytesseract
from PIL import Image
import mss

APP_NAME = "iGOT Smart Learning Assistant"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:1.5b"


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
        ttk.Button(controls, text="Ollama setup help", command=self.setup_help).pack(side="right")
        self.status = tk.StringVar(value="Ready — iGOT को स्क्रीन के बाएँ हिस्से में रखें")
        ttk.Label(outer, textvariable=self.status, wraplength=460).pack(anchor="w", pady=(0, 8))
        ttk.Label(outer, text="पहचाना गया प्रश्न", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.question = tk.Text(outer, height=8, wrap="word", font=("Segoe UI", 10))
        self.question.pack(fill="x", pady=(4, 10))
        ttk.Label(outer, text="पूरा उत्तर और हिंदी में व्याख्या", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.answer = tk.Text(outer, wrap="word", font=("Segoe UI", 10))
        self.answer.pack(fill="both", expand=True, pady=(4, 0))
        self.answer.insert("1.0", "यहाँ उत्तर दिखाई देगा।\n\n1. Ollama install करें।\n2. PowerShell में: ollama pull qwen2.5:1.5b\n3. iGOT/browser को बाएँ रखें और Start reading दबाएँ।")
        self.answer.configure(state="disabled")

    def setup_help(self):
        messagebox.showinfo(
            "Ollama setup",
            "1. https://ollama.com/download/windows से Ollama install करें।\\n"
            "2. PowerShell खोलकर यह चलाएँ: ollama pull qwen2.5:1.5b\\n"
            "3. डाउनलोड पूरा होने पर यह ऐप दोबारा खोलें।\\n"
            "API key या Gemini account की जरूरत नहीं है।"
        )

    def start(self):
        if self.running:
            return
        try:
            check = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
            check.raise_for_status()
            models = [m.get("name", "") for m in check.json().get("models", [])]
            if not any(name == MODEL or name.startswith(MODEL + ":") for name in models):
                messagebox.showwarning(
                    "Model not installed",
                    f"Ollama चल रहा है, लेकिन {MODEL} मॉडल नहीं मिला।\\n"
                    "PowerShell में चलाएँ: ollama pull qwen2.5:1.5b"
                )
                return
        except Exception:
            messagebox.showerror(
                "Ollama not running",
                "पहले Ollama install और start करें।\\n"
                "https://ollama.com/download/windows\\n"
                "फिर PowerShell में चलाएँ: ollama pull qwen2.5:1.5b"
            )
            return
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status.set("Ollama local AI से कनेक्ट — स्क्रीन पढ़ रहा है…")
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
                        threading.Thread(target=self.ask_ollama, args=(text,), daemon=True).start()
                else:
                    self.root.after(0, self.status.set, "स्क्रीन पर पढ़ने योग्य प्रश्न नहीं मिला — स्क्रीन/अनुमति जाँचें")
            except Exception as e:
                self.root.after(0, self.status.set, "OCR error: " + str(e)[:180])
            time.sleep(3)

    def show_question(self, text):
        self.question.delete("1.0", "end")
        self.question.insert("1.0", text[:7000])
        self.status.set("नया स्क्रीन टेक्स्ट मिला — उत्तर तैयार हो रहा है…")

    def ask_ollama(self, screen_text):
        prompt = (
            "You are a patient Hindi study tutor. The following is OCR text from permitted practice and learning material. "
            "Identify the likely question and its options. Explain the concept and reasoning in simple Hindi. "
            "For practice questions, state the likely correct option and why. If OCR is incomplete or ambiguous, "
            "say so and do not guess. This tool is for learning, not for answering live graded tests or official exams. "
            "Do not interact with the source app.\\n\\nSCREEN TEXT:\\n" + screen_text[:5000]
        )
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_ctx": 2048}
                },
                timeout=180
            )
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:400]}")
            answer = response.json().get("response", "").strip()
            if not answer:
                answer = "मॉडल से खाली उत्तर मिला। कृपया फिर कोशिश करें।"
            self.root.after(0, self.show_answer, answer)
        except requests.exceptions.Timeout:
            self.root.after(0, self.show_answer, "स्थानीय AI को उत्तर बनाने में अधिक समय लग रहा है। कुछ देर बाद फिर कोशिश करें।")
        except Exception as e:
            self.root.after(0, self.show_answer, "Ollama से उत्तर प्राप्त नहीं हुआ।\\n\\n" + str(e))

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
