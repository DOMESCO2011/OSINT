from imports import *



class OSINTApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OSINT Tool v1.0")
        self.geometry("1400x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        OSINTApp.exif_reading = exif_reading
        OSINTApp.haar_detection = haar_detection
        OSINTApp.shadow_analysis = self.shadow_analysis

        create_db()



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
        menubar.add_command(label="About", command=lambda: self.log("info", "APP", "OSINT Tool v1.0\n Made by Domesco"))
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
        """Algoritmusok futtatása modulárisan"""
        try:
            modules = [
                lambda: self.exif_reading(self.image_path),
                self.run_haar_detection,
                lambda: self.plate_recognition_module(self.image_path),  # ide
                lambda: self.shadow_analysis(self.image_path)
            ]


            for module in modules:
                if not self.is_running:
                    break
                module()

        except Exception as e:
            self.log("error", "OSINT", f"Kritikus hiba: {str(e)}")
        finally:
            self.is_running = False

    def run_haar_detection(self):
        """Haar detekció kiszervezve, de az osztályon belül"""
        try:
            
            
            self.log("info", "HAAR", "Arcok és szemek keresése...")
            haar_results = haar_detection(self.image_path)
            
            if not haar_results:
                self.log("warning", "HAAR", "Nem található arc.")
                return

            # Arcok és szemek kirajzolása
            for (x, y, w, h) in haar_results["faces"]:
                self.canvas.create_rectangle(x, y, x+w, y+h, outline="red", width=2)
                self.log("success", "HAAR", f"Arc észlelve: ({x}, {y}, {w}, {h})")

            for (x, y, w, h) in haar_results["eyes"]:
                self.canvas.create_rectangle(x, y, x+w, y+h, outline="green", width=2)
                self.log("success", "HAAR", f"Szem észlelve: ({x}, {y}, {w}, {h})")

        except Exception as e:
            self.log("error", "HAAR", f"Hiba: {str(e)}")

    # --- Algoritmus Modulok ---



    def plate_recognition_module(self):
        """Rendszám felismerés a már betöltött képen"""
        if not self.image_path:
            self.log("error", "PLATE", "Nincs kép betöltve!")
            return

        self.log("info", "PLATE", "Rendszám felismerés indítása...")
        
        # Rendszámok felismerése
        results = plate_recognition(self.image_path, use_online_db=False)
        
        if results:
            for result in results:
                plate = result["plate"]
                country_code = result["country_code"]
                x, y, w, h = result["position"]
                
                # Keret rajzolása a képre
                self.canvas.create_rectangle(x, y, x+w, y+h, outline="yellow", width=2)
                
                # Szöveg hozzáadása a képhez (országkóddal együtt)
                label = f"{country_code} {plate}" if country_code else plate
                self.canvas.create_text(x, y-15, text=label, fill="yellow", font=("Arial", 12))
                
                # Információk összeállítása
                info_text = f"Rendszám: {plate}"
                if country_code:
                    info_text += f"\nOrszágkód: {country_code}"
                
                # Lokális adatbázis információ
                if result["local_db_info"]:
                    db_info = result["local_db_info"]
                    info_text += f"\nTulajdonos: {db_info[1]}\nSzín: {db_info[2]}\nÉvjárat: {db_info[3]}"
                    if len(db_info) > 4 and db_info[4]:  # Márka
                        info_text += f"\nMárka: {db_info[4]}"
                    if len(db_info) > 5 and db_info[5]:  # Modell
                        info_text += f"\nModell: {db_info[5]}"
                    if len(db_info) > 6 and db_info[6]:  # Országkód
                        info_text += f"\nOrszág: {db_info[6]}"
                
                # Online információ
                if result["online_info"]:
                    online_info = result["online_info"]
                    info_text += f"\n--- Online információk ---"
                    if "owner" in online_info:
                        info_text += f"\nTulajdonos: {online_info['owner']}"
                    if "make" in online_info:
                        info_text += f"\nMárka: {online_info['make']}"
                    if "model" in online_info:
                        info_text += f"\nModell: {online_info['model']}"
                    if "country" in online_info:
                        info_text += f"\nOrszág: {online_info['country']}"
                
                self.log("success", "PLATE", info_text)
                
            self.log("success", "PLATE", f"{len(results)} rendszám felismerve.")
        else:
            self.log("warning", "PLATE", "Nem található rendszám a képen.")



    def shadow_analysis(self, image_path):
        """
        Árnyék elemzés végrehajtása a képen
        """
        try:
            result = detect_shadow(image_path)
            
            # Eredmények logolása
            if result.get("shadow_direction") is not None:
                self.log("success", "SHADOW", f"Árnyék irány: {result['shadow_direction']:.2f}°")
            else:
                self.log("warning", "SHADOW", "Nem sikerült árnyék irányt meghatározni")
                
            # Vonalak kirajzolása a képre
            if result.get("detected_lines"):
                for line in result["detected_lines"]:
                    x1, y1, x2, y2 = line[0]
                    self.canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)
            
            return result
            
        except ImportError:
            self.log("error", "SHADOW", "Árnyék analízis modul nem található")
            return {"error": "Shadow analysis module missing"}
        except Exception as e:
            self.log("error", "SHADOW", f"Árnyék analízis hiba: {e}")
            return {"error": str(e)}


# --- Indítás ---
if __name__ == "__main__":
    app = OSINTApp()
    app.mainloop()