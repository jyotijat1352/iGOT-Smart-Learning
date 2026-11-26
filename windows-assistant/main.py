import os, sys, time, threading, hashlib, re
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import mss

APP_NAME = "iGOT Smart Learning Assistant"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:1.5b"


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


bundled_tesseract = resource_path(os.path.join("tesseract", "tesseract.exe"))
if os.path.exists(bundled_tesseract):
    pytesseract.pytesseract.tesseract_cmd = bundled_tesseract


def clean_ocr_text(raw):
    """Remove browser chrome, URLs and OCR noise without inventing missing words."""
    kept = []
    seen = set()
    for raw_line in raw.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" |•\t")
        if len(line) < 2:
            continue
        low = line.lower()
        if re.search(r"https?://|www\.|\.gov\.in|\.com/|portal\.", low):
            continue
        if low in {"home", "login", "logout", "dashboard", "menu", "search"}:
            continue
        # Ignore obvious OCR fragments, but preserve short option labels like A.
        if len(re.sub(r"[^A-Za-z0-9\u0900-\u097F]", "", line)) < 2:
            continue
        key = low
        if key not in seen:
            seen.add(key)
            kept.append(line)
    return "\n".join(kept)


def read_screen_with_ocr(image):
    """Upscale and sharpen text, then compare two Tesseract page layouts."""
    gray = ImageOps.grayscale(image)
    if gray.width < 1800:
        scale = 2
        gray = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
    gray = ImageEnhance.Contrast(gray).enhance(1.7)
    gray = gray.filter(ImageFilter.SHARPEN)
    candidates = []
    for psm in (6, 11):
        data = pytesseract.image_to_data(
            gray, lang="eng+hin", config=f"--oem 3 --psm {psm}",
            output_type=Output.DICT
        )
        # Rebuild text by Tesseract's block/paragraph/line coordinates.
        # Joining every word into one sentence destroys question/option structure.
        line_words = {}
        confs = []
        for i, word in enumerate(data["text"]):
            word = word.strip()
            try:
                score = float(data["conf"][i])
            except (TypeError, ValueError):
                score = -1
            if not word or score < 5:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            line_words.setdefault(key, []).append((data["left"][i], word, score))
            confs.append(score)
        lines = []
        for key in sorted(line_words):
            items = sorted(line_words[key], key=lambda item: item[0])
            line = " ".join(item[1] for item in items)
            if line.strip():
                lines.append(line)
        raw = "\\n".join(lines)
        cleaned = clean_ocr_text(raw)
        # Favor readable, multi-line OCR with useful confidence.
        quality = (sum(confs) / max(1, len(confs))) + min(len(cleaned), 1200) / 100
        if len(lines) >= 2:
            quality += 8
        candidates.append((quality, cleaned))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1] if candidates else ""


class Assistant:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("540x780+850+60")
        self.root.minsize(440, 600)
        self.root.attributes("-topmost", True)
        self.running = False
        self.last_hash = ""
        self.last_call = 0
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="iGOT Smart Learning Assistant", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Practice & learning companion • Hindi explanations", foreground="#536273").pack(anchor="w", pady=(2, 10))
        warning = tk.Label(outer, text="केवल अभ्यास और पढ़ाई के लिए। आधिकारिक परीक्षा/graded test में उपयोग न करें।\nProtected screen को यह ऐप bypass नहीं करता।", bg="#fff2d6", fg="#684500", justify="left", padx=10, pady=8, wraplength=480)
        warning.pack(fill="x", pady=(0, 10))
        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 8))
        self.start_btn = ttk.Button(controls, text="Start reading", command=self.start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(controls, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(controls, text="Ollama setup help", command=self.setup_help).pack(side="right")
        self.status = tk.StringVar(value="तैयार — अभ्यास प्रश्न स्क्रीन के बाएँ हिस्से में स्पष्ट रखें")
        ttk.Label(outer, textvariable=self.status, wraplength=480).pack(anchor="w", pady=(0, 8))
        ttk.Label(outer, text="पहचाना गया स्क्रीन टेक्स्ट", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.question = tk.Text(outer, height=9, wrap="word", font=("Segoe UI", 10))
        self.question.pack(fill="x", pady=(4, 10))
        ttk.Label(outer, text="हिंदी में समझ और अध्ययन सहायता", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.answer = tk.Text(outer, wrap="word", font=("Segoe UI", 10))
        self.answer.pack(fill="both", expand=True, pady=(4, 0))
        self.answer.insert("1.0", "Ollama और qwen2.5:1.5b तैयार होने के बाद Start reading दबाएँ।\n\nबेहतर परिणाम के लिए अभ्यास प्रश्न और सभी विकल्प स्क्रीन पर साफ दिखाएँ।")
        self.answer.configure(state="disabled")

    def setup_help(self):
        messagebox.showinfo(
            "Ollama setup",
            "1. https://ollama.com/download/windows से Ollama install करें।\n"
            "2. PowerShell में चलाएँ: ollama pull qwen2.5:1.5b\n"
            "3. Ollama चालू रखकर यह ऐप खोलें।\nAPI key की जरूरत नहीं है।"
        )

    def start(self):
        if self.running:
            return
        try:
            check = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
            check.raise_for_status()
            models = [m.get("name", "") for m in check.json().get("models", [])]
            if not any(name == MODEL or name.startswith(MODEL + ":") for name in models):
                messagebox.showwarning("Model not installed", f"{MODEL} मॉडल नहीं मिला। PowerShell में चलाएँ: ollama pull {MODEL}")
                return
        except Exception:
            messagebox.showerror("Ollama not running", "पहले Ollama चालू करें। फिर PowerShell में चलाएँ: ollama pull qwen2.5:1.5b")
            return
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status.set("स्थानीय AI चालू — स्क्रीन का अभ्यास टेक्स्ट पढ़ रहा है…")
        threading.Thread(target=self.loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status.set("पढ़ना बंद किया गया")

    def loop(self):
        while self.running:
            try:
                with mss.mss() as sct:
                    mon = sct.monitors[1]
                    region = {"left": mon["left"], "top": mon["top"],
                              "width": int(mon["width"] * 0.68), "height": mon["height"]}
                    shot = sct.grab(region)
                    img = Image.frombytes("RGB", shot.size, shot.rgb)
                text = read_screen_with_ocr(img)
                if len(text) >= 25:
                    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    if digest != self.last_hash and time.time() - self.last_call > 5:
                        self.last_hash = digest
                        self.last_call = time.time()
                        self.root.after(0, self.show_question, text)
                        threading.Thread(target=self.ask_ollama, args=(text,), daemon=True).start()
                else:
                    self.root.after(0, self.status.set, "साफ प्रश्न नहीं मिला — प्रश्न/विकल्प बड़ा करके दिखाएँ")
            except Exception as e:
                self.root.after(0, self.status.set, "OCR error: " + str(e)[:160])
            time.sleep(3)

    def show_question(self, text):
        self.question.delete("1.0", "end")
        self.question.insert("1.0", text[:6000])
        self.status.set("टेक्स्ट पढ़ लिया — अध्ययन सहायता तैयार हो रही है…")

    def ask_ollama(self, screen_text):
        prompt = (
            "आप हिंदी में पढ़ाने वाले धैर्यवान शिक्षक हैं। नीचे केवल OCR से मिला स्क्रीन टेक्स्ट है। "
            "सबसे पहले जाँचें कि इसमें वास्तव में कोई प्रश्न और उसके विकल्प मौजूद हैं या नहीं। "
            "केवल OCR में साफ दिख रहे शब्दों के आधार पर प्रश्न और विकल्प लिखें; कोई विकल्प स्वयं न बनाएँ। "
            "वेबसाइट का पता, मेनू, ब्राउज़र टेक्स्ट या PowerShell कमांड को प्रश्न न मानें। "
            "यदि प्रश्न अधूरा है, विकल्प नहीं दिख रहे, या टेक्स्ट किसी प्रश्न की पुष्टि नहीं करता, तो साफ लिखें: "
            "'प्रश्न स्पष्ट रूप से पढ़ा नहीं जा सका। कृपया प्रश्न और विकल्प स्क्रीन पर बड़ा करके दिखाएँ।' "
            "ऐसी स्थिति में सही उत्तर का अनुमान बिल्कुल न लगाएँ। "
            "यदि अभ्यास प्रश्न स्पष्ट है, तो इस क्रम में उत्तर दें: "
            "1. पहचाना गया प्रश्न 2. OCR में दिखे विकल्प 3. संबंधित विषय की आसान हिंदी में व्याख्या "
            "4. अवधारणा समझने का तरीका 5. यदि पर्याप्त जानकारी हो तभी संभावित सही विकल्प और कारण। "
            "यह केवल अभ्यास/सीखने के लिए है; किसी live graded test या आधिकारिक परीक्षा का उत्तर न दें। "
            "स्रोत ऐप में क्लिक, चयन या सबमिट न करें।\n\nOCR TEXT:\n" + screen_text[:4500]
        )
        try:
            response = requests.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.1, "num_ctx": 3072}},
                timeout=180
            )
            response.raise_for_status()
            answer = response.json().get("response", "").strip()
            if not answer:
                answer = "AI से खाली उत्तर मिला। कृपया दोबारा कोशिश करें।"
            self.root.after(0, self.show_answer, answer)
        except requests.exceptions.Timeout:
            self.root.after(0, self.show_answer, "स्थानीय AI को अधिक समय लग रहा है। कुछ देर बाद फिर कोशिश करें।")
        except Exception as e:
            self.root.after(0, self.show_answer, "Ollama से उत्तर प्राप्त नहीं हुआ।\n" + str(e)[:300])

    def show_answer(self, text):
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", text)
        self.answer.configure(state="disabled")
        self.status.set("अध्ययन सहायता अपडेट हो गई")

    def close(self):
        self.running = False
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    Assistant(root)
    root.mainloop()
