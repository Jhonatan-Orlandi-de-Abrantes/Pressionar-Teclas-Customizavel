import customtkinter as ctk, tkinter as tk, threading, time, keyboard, pickle, os
from tkinter import messagebox
from win10toast import ToastNotifier

KEYS_FILE = "keys.pkl"
HOTKEYS_FILE = "hotkeys.pkl"

class PressionadorDeTeclas:
    def __init__(self, root):
        self.root = root
        self.root.title("Pressionador de teclas - Customizado")
        self.root.geometry("550x520")
        self.root.resizable(False, False)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Estado
        self.running = False
        self.rows = []
        self.selected_row = None

        # Hotkeys padrão
        self.hotkeys = {
            "start_stop": "F8",
            "add_row": "F9",
            "remove_row": "F10"
        }

        self.notifier = ToastNotifier()

        self._registered_handlers = []

        self.load_hotkeys()
        self.build_ui()
        self.register_hotkeys()

    # ---------------- UI ----------------
    def build_ui(self):
        frame_main = ctk.CTkFrame(self.root)
        frame_main.pack(fill="both", expand=True, padx=10, pady=10)

        # Área rolável (Canvas + scroll)
        self.canvas = tk.Canvas(frame_main, bg="#242424", highlightthickness=0)
        self.scrollbar = ctk.CTkScrollbar(frame_main, orientation="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="n")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Botões de controle
        control_frame = ctk.CTkFrame(self.root)
        control_frame.pack(pady=(6, 10))

        buttons = [
            ("➕ Adicionar",   self.add_row),
            ("🗑️ Remover", self.remove_selected),
            ("💾 Salvar", self.save_keys),
            ("📂 Carregar", self.load_keys),
            ("▶ Iniciar", self.start),
            ("⏹️ Parar", self.stop)
        ]

        for i, (txt, cmd) in enumerate(buttons):
            fg = None
            if txt == "▶ Iniciar": fg = "#3c9c3c"
            if txt == "⏹️ Parar": fg = "#a33c3c"
            ctk.CTkButton(control_frame, text=txt, width=70, fg_color=fg, command=cmd).grid(row=0, column=i, padx=4)

        # ---------------- HOTKEYS ----------------
        hotkey_frame = ctk.CTkFrame(self.root)
        hotkey_frame.pack(pady=(10, 10))

        ctk.CTkLabel(hotkey_frame, text="Atalhos:", font=("Arial", 14, "bold")).pack(anchor="center", pady=(5, 10))

        self.hotkey_labels = {}
        hotkey_container = ctk.CTkFrame(hotkey_frame, corner_radius=10)
        hotkey_container.pack(pady=5)

        for i, (key, label) in enumerate({
            "start_stop": "Iniciar/Parar",
            "add_row": "Adicionar linha",
            "remove_row": "Remover linha"
        }.items()):
            fr = ctk.CTkFrame(hotkey_container, corner_radius=8, fg_color="#2e2e2e")
            fr.pack(pady=4)

            inner = ctk.CTkFrame(fr, corner_radius=8, fg_color="#242424")
            inner.pack(padx=15, pady=5)

            ctk.CTkLabel(inner, text=f"{label}:", width=120, anchor="e").pack(side="left", padx=5)

            # Label parecida com tecla + hover
            lbl = ctk.CTkLabel(inner, text=self.hotkeys[key], width=70, height=30, fg_color="#3b3b3b", corner_radius=6, text_color="white", font=("Consolas", 13, "bold"))
            lbl.pack(side="left", padx=10)
            self.hotkey_labels[key] = lbl

            def on_enter(e, l=lbl): l.configure(fg_color="#5a5a5a")
            def on_leave(e, l=lbl): l.configure(fg_color="#3b3b3b")
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)

            ctk.CTkButton(
                inner, text="Definir", width=70, height=28,
                command=lambda k=key: threading.Thread(target=self.define_hotkey, args=(k,), daemon=True).start()).pack(side="left", padx=6)

        # ---------------- Primeira linha ----------------
        self.add_row()

    # ---------------- Linhas ----------------
    def add_row(self):
    # Frame principal da linha (preenche horizontalmente)
        frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=8)
        frame.pack(fill="x", pady=4, padx=0)

        # Frame interno centralizado, agora expandindo horizontalmente
        inner_frame = ctk.CTkFrame(frame, fg_color="#2b2b2b", corner_radius=8)
        inner_frame.pack(fill="x", padx=10, pady=4)

        # Frame para centralizar os widgets
        content_frame = ctk.CTkFrame(inner_frame, fg_color=None, corner_radius=0)
        content_frame.pack(padx=0, pady=0)

        key_entry = ctk.CTkEntry(content_frame, width=170, placeholder_text="Tecla")
        key_entry.pack(side="left", padx=5, pady=4)

        interval_entry = ctk.CTkEntry(content_frame, width=100, placeholder_text="Intervalo (s)")
        interval_entry.insert(0, "1.0")
        interval_entry.pack(side="left", padx=5, pady=4)

        select_btn = ctk.CTkButton(content_frame, text="Selecionar", width=180, command=lambda: self.select_row(frame))
        select_btn.pack(side="left", padx=6, pady=4)

        # Guardar referência
        self.rows.append((frame, key_entry, interval_entry))

    def select_row(self, frame):
        if self.selected_row:
            try:
                self.selected_row.configure(fg_color="#2b2b2b")
            except Exception:
                pass
        self.selected_row = frame
        try:
            frame.configure(fg_color="#3a4c7a")
        except Exception:
            pass

    def remove_selected(self):
        if not self.selected_row:
            messagebox.showinfo("Aviso", "Nenhuma linha selecionada.")
            return
        for row in list(self.rows):
            if row[0] == self.selected_row:
                try:
                    row[0].destroy()
                except Exception:
                    pass
                self.rows.remove(row)
                self.selected_row = None
                break

    # ---------------- Hotkeys ----------------
    def define_hotkey(self, which):
        modal = ctk.CTkToplevel(self.root)
        modal.title("Definir atalho")
        modal.geometry("320x130")
        ctk.CTkLabel(modal, text=f"Pressione uma tecla para '{which}'").pack(pady=20)

        result = {"key": None}

        def capture():
            try:
                k = keyboard.read_key()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Não foi possível ler a tecla: {e}"))
                modal.destroy()
                return
            result["key"] = k.upper()
            self.hotkeys[which] = result["key"]
            self.hotkey_labels[which].configure(text=result["key"])
            self.save_hotkeys()
            self.register_hotkeys()
            modal.destroy()
            messagebox.showinfo("Ok", f"Atalho '{which}' definido para {result['key']}")

        threading.Thread(target=capture, daemon=True).start()
        self.root.wait_window(modal)

    def register_hotkeys(self):
        if hasattr(self, "_registered_handlers") and self._registered_handlers:
            for h in list(self._registered_handlers):
                try:
                    keyboard.remove_hotkey(h)
                except Exception:
                    try:
                        keyboard.remove_hotkey(str(h))
                    except Exception:
                        pass
            self._registered_handlers = []

        try:
            h1 = keyboard.add_hotkey(self.hotkeys.get("start_stop", "F8"), lambda: threading.Thread(target=self.toggle_run, daemon=True).start())
            self._registered_handlers.append(h1)
        except Exception as e:
            print("Erro ao registrar start_stop:", e)

        try:
            h2 = keyboard.add_hotkey(self.hotkeys.get("add_row", "F9"), lambda: self.root.after(0, self.add_row))
            self._registered_handlers.append(h2)
        except Exception as e:
            print("Erro ao registrar add_row:", e)

        try:
            h3 = keyboard.add_hotkey(self.hotkeys.get("remove_row", "F10"), lambda: self.root.after(0, self.remove_selected))
            self._registered_handlers.append(h3)
        except Exception as e:
            print("Erro ao registrar remove_row:", e)

    def toggle_run(self):
        if self.running:
            self.stop()
        else:
            self.start()

    # ---------------- Salvar/Carregar ----------------
    def save_keys(self):
        try:
            data = []
            for _, key_entry, interval_entry in self.rows:
                key = key_entry.get().strip()
                if not key:
                    continue
                try:
                    interval = float(interval_entry.get())
                except Exception:
                    interval = 1.0
                data.append({"key": key, "interval": interval})
            with open(KEYS_FILE, "wb") as f:
                pickle.dump(data, f)
            messagebox.showinfo("Sucesso", f"Salvo {len(data)} teclas em {KEYS_FILE}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")

    def load_keys(self):
        if not os.path.exists(KEYS_FILE):
            messagebox.showwarning("Aviso", "Nenhum arquivo salvo encontrado.")
            return
        try:
            with open(KEYS_FILE, "rb") as f:
                data = pickle.load(f)
            # limpar linhas atuais
            for row in list(self.rows):
                try:
                    row[0].destroy()
                except Exception:
                    pass
            self.rows.clear()
            for item in data:
                self.add_row()
                # inserir valores
                try:
                    self.rows[-1][1].insert(0, item.get("key", ""))
                    self.rows[-1][2].delete(0, tk.END)
                    self.rows[-1][2].insert(0, str(item.get("interval", 1.0)))
                except Exception:
                    pass
            messagebox.showinfo("Sucesso", "Teclas carregadas com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar: {e}")

    def save_hotkeys(self):
        try:
            with open(HOTKEYS_FILE, "wb") as f:
                pickle.dump(self.hotkeys, f)
        except Exception as e:
            print("Erro ao salvar atalhos:", e)

    def load_hotkeys(self):
        if os.path.exists(HOTKEYS_FILE):
            try:
                with open(HOTKEYS_FILE, "rb") as f:
                    data = pickle.load(f)
                    if isinstance(data, dict):
                        self.hotkeys.update(data)
            except Exception as e:
                print("Erro ao carregar atalhos:", e)

    # ---------------- Execução ----------------
    def start(self):
        if self.running:
            return

        # Verificar campos vazios
        for _, key_entry, _ in self.rows:
            key = key_entry.get().strip()
            if not key:
                messagebox.showwarning("Erro", "Há campos de tecla em branco. Preencha antes de iniciar.")
                return

        self.running = True
        threading.Thread(target=self.run_loop, daemon=True).start()
        
        # Notificação no Windows
        try:
            self.notifier.show_toast(f"{root.title()}", "Execução Iniciada!!! ", icon_path=None, duration=1, threaded=True)
        except Exception as e:
            print("Falha ao mostrar notificação:", e)

    def stop(self):
        if not self.running:
            return
        self.running = False
        
        # Notificação no Windows
        try:
            self.notifier.show_toast(f"{root.title()}", "Execução Parada!!!", icon_path=None, duration=1, threaded=True)
        except Exception as e:
            print("Falha ao mostrar notificação:", e)

    def run_loop(self):
        while self.running:
            for _, key_entry, interval_entry in list(self.rows):
                if not self.running:
                    break
                try:
                    key = key_entry.get().strip()
                except Exception:
                    key = ""
                if not key:
                    continue
                try:
                    interval = float(interval_entry.get())
                except Exception:
                    interval = 1.0
                try:
                    keyboard.press_and_release(key)
                except Exception:
                    try:
                        keyboard.press_and_release(str(key).lower())
                    except Exception:
                        pass
                # intervalo com checagem frequente para parar rápido
                waited = 0.0
                step = 0.05
                while waited < interval:
                    if not self.running:
                        break
                    time.sleep(min(step, interval - waited))
                    waited += step

if __name__ == "__main__":
    root = ctk.CTk()
    app = PressionadorDeTeclas(root)
    root.mainloop()