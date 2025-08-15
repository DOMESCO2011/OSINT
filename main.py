import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time
from algorithms.exif import exif_reading

class OSINTApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OSINT Tool v1.0")
        self.geometry("1400x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        OSINTApp.exif_reading = exif_reading

        # Változók
        self.image = None
        self.image_path = ""
        self.is_running = False

        # Grid layout
        self.grid_columnconfigure(0, weight=1)  # Képtér
        self.grid_columnconfigure(1, weight=0)  # Log (fix szélesség)
        self.grid_rowconfigure(0, weight=1)

        # UI elemek
        self.create_menu()
        self.create_image_canvas()
        self.create_log_panel()

    # --- UI Létrehozása ---
    def create_menu(self):
        """Felső menüsor (File, OSINT, About)"""
        menubar = tk.Menu(self)

        # File menü
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Image", command=self.load_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # OSINT menü
        osint_menu = tk.Menu(menubar, tearoff=0)
        osint_menu.add_command(label="Start", command=self.start_osint)
        osint_menu.add_command(label="Stop", command=self.stop_osint)
        menubar.add_cascade(label="OSINT", menu=osint_menu)

        # About menü
        menubar.add_command(label="About", command=lambda: self.log("info", "APP", "OSINT Tool v1.0"))
        self.configure(menu=menubar)

    def create_image_canvas(self):
        """Középső képtér (TK Canvas rajzoláshoz)"""
        self.canvas = tk.Canvas(self, bg="gray12", bd=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.canvas.create_text(300, 200, text="Tölts be egy képet!", fill="gray50", font=("Arial", 20))

    def create_log_panel(self):
        """Jobb oldali színes log"""
        self.log_panel = ctk.CTkTextbox(self, width=300, corner_radius=0)
        self.log_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # Log színek beállítása
        self.log_panel.tag_config("error", foreground="#ff6b6b")
        self.log_panel.tag_config("warning", foreground="#feca57")
        self.log_panel.tag_config("success", foreground="#1dd1a1")
        self.log_panel.tag_config("info", foreground="#54a0ff")
        self.log_panel.insert("end", ">>> OSINT Tool v1.0 - Log\n", "info")
        self.log_panel.configure(state="disabled")

    # --- Segédfüggvények ---
    def log(self, type, sender, message):
        """Színes logolás
        :param type: error/warning/success/info
        :param sender: Küldő modul (pl. 'EXIF')
        :param message: Üzenet szövege
        """
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{sender}] {message}\n"
        
        self.log_panel.configure(state="normal")
        self.log_panel.insert("end", log_entry, type)
        self.log_panel.configure(state="disabled")
        self.log_panel.see("end")  # Autoscroll

    def clear_canvas(self):
        """Törli a canvas tartalmát"""
        self.canvas.delete("all")
        if self.image:
            img_tk = ImageTk.PhotoImage(self.image)
            self.canvas.image = img_tk
            self.canvas.create_image(0, 0, anchor="nw", image=img_tk)

    # --- Fő Funkciók ---
    def load_image(self):
        """Kép betöltése"""
        try:
            global file_path
            file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
            if file_path:
                self.image_path = file_path
                self.image = Image.open(file_path)
                self.clear_canvas()
                self.log("success", "UI", f"Kép betöltve: {file_path}")
        except Exception as e:
            self.log("error", "UI", f"Hiba a képbetöltésnél: {str(e)}")

    def start_osint(self):
        """OSINT folyamat indítása (threadben)"""
        if not self.image_path:
            self.log("error", "OSINT", "Nincs kép betöltve!")
            return

        if self.is_running:
            self.log("warning", "OSINT", "A folyamat már fut!")
            return

        self.is_running = True
        self.log("info", "OSINT", "Analízis elindítva...")
        
        # Algoritmusok futtatása külön szálon
        threading.Thread(target=self.run_osint, daemon=True).start()

    def stop_osint(self):
        """OSINT folyamat leállítása"""
        self.is_running = False
        self.log("warning", "OSINT", "Analízis leállítva!")

    def run_osint(self):
        """Algoritmusok futtatása"""
        try:
            # Modulok sorban
            modules = [
                lambda: self.exif_reading(self.image_path),
                self.face_detection,
                self.plate_recognition,
                self.shadow_analysis
]


            for module in modules:
                if not self.is_running:
                    break
                module()

        except Exception as e:
            self.log("error", "OSINT", f"Kritikus hiba: {str(e)}")
        finally:
            self.is_running = False

    # --- Algoritmus Modulok ---






    def face_detection(self):
        """Arcfelismerés"""
        try:
            self.log("info", "FACE", "Arcok keresése...")
            time.sleep(1.5)
            
            # Példa eredmények (x1, y1, x2, y2)
            fake_faces = [(100, 100, 200, 200), (400, 150, 500, 250)]
            for (x1, y1, x2, y2) in fake_faces:
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="#1dd1a1", width=2)
                self.log("success", "FACE", f"Arc észlelve: ({x1}, {y1})")
        except Exception as e:
            self.log("error", "FACE", f"Hiba: {str(e)}")

    def plate_recognition(self):
        """Rendszámfelismerés"""
        try:
            self.log("info", "PLATE", "Rendszámok keresése...")
            time.sleep(2)
            
            fake_plate = "ABC-123"
            self.canvas.create_text(400, 50, text=fake_plate, fill="#feca57", font=("Arial", 20))
            self.log("success", "PLATE", f"Rendszám: {fake_plate}")
        except Exception as e:
            self.log("error", "PLATE", f"Hiba: {str(e)}")

    def shadow_analysis(self):
        """Árnyék alapú helymeghatározás"""
        try:
            self.log("info", "SHADOW", "Árnyékok elemzése...")
            time.sleep(1)
            
            # Példa: zöld vonal az árnyék irányában
            self.canvas.create_line(200, 200, 300, 300, fill="#54a0ff", width=3)
            self.log("success", "SHADOW", "Becsült szélességi fok: ~47°N")
        except Exception as e:
            self.log("error", "SHADOW", f"Hiba: {str(e)}")

# --- Indítás ---
if __name__ == "__main__":
    app = OSINTApp()
    app.mainloop()