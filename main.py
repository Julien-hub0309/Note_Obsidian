# main.py
import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
from datetime import datetime

# Importation des modules CORE
from core.lecteur import select_file, read_file_text
from core.analyser import analyze_and_structure_text
from core.export_markdown import export_markdown, sanitize_filename
from core.refiles import reformat_text, available_styles, DEFAULT_STYLE
from display import display_status, display_loading, display_analysis_summary


# ==========================================================================
# PALETTE — thème sombre unique, réutilisé partout dans l'application
# ==========================================================================
class Palette:
    BG = "#1e1e2e"          # Fond général (très sombre)
    SURFACE = "#262638"     # Fond des cadres / panneaux
    SURFACE_2 = "#313145"   # Fond des zones de saisie
    BORDER = "#3a3a52"

    TEXT = "#e4e4f1"        # Texte principal
    SUBTEXT = "#9a9ac0"     # Texte secondaire / labels
    TITLE = "#c9a4f5"       # Violet clair pour le titre

    ACCENT = "#3aa0ff"      # Bleu (action principale)
    ACCENT_HOVER = "#1e88e5"
    SUCCESS = "#16a085"
    SUCCESS_HOVER = "#128c7e"
    WARNING = "#e67e22"
    WARNING_HOVER = "#c76b1c"
    DANGER = "#e74c3c"
    DANGER_HOVER = "#c0392b"

    STATUS_OK = "#2ecc71"
    STATUS_ERR = "#e74c3c"
    STATUS_WAIT = "#f1c40f"
    STATUS_IDLE = "#9a9ac0"


class HoverButton(tk.Button):
    """Bouton flat qui change légèrement de couleur au survol pour
    donner un rendu plus moderne qu'un simple tk.Button statique."""

    def __init__(self, master, bg: str, hover_bg: str, **kwargs):
        super().__init__(
            master,
            bg=bg,
            activebackground=hover_bg,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            **kwargs,
        )
        self._bg = bg
        self._hover_bg = hover_bg
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event):
        if self["state"] != tk.DISABLED:
            self.config(bg=self._hover_bg)

    def _on_leave(self, _event):
        if self["state"] != tk.DISABLED:
            self.config(bg=self._bg)


class ObsidianTextProcessorApp:
    """Application de bureau principale, interface Dark Mode moderne."""

    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("Obsidian AI Processor 💡")
        master.geometry("1000x750")
        master.minsize(760, 560)
        master.configure(bg=Palette.BG)

        self.current_style_key = DEFAULT_STYLE

        self._setup_style()
        self._setup_menu()
        self._setup_ui()

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ------------------------------------------------------------------
    # CONFIGURATION GÉNÉRALE
    # ------------------------------------------------------------------
    def _setup_style(self):
        style = ttk.Style(self.master)
        # "clam" est le seul thème ttk intégré qui se laisse recolorer
        # correctement (scrollbars, combobox, etc.) en mode sombre.
        style.theme_use("clam")

        style.configure(
            "Dark.Vertical.TScrollbar",
            background=Palette.SURFACE_2,
            troughcolor=Palette.SURFACE,
            bordercolor=Palette.SURFACE,
            arrowcolor=Palette.TEXT,
            relief=tk.FLAT,
        )
        style.map("Dark.Vertical.TScrollbar", background=[("active", Palette.ACCENT)])

    def _setup_menu(self):
        menubar = tk.Menu(self.master)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="📂 Ouvrir un fichier...", command=self.load_file)
        file_menu.add_command(label="💾 Exporter en Markdown...", command=self.export_current_text)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.on_closing)
        menubar.add_cascade(label="Fichier", menu=file_menu)

        self.master.config(menu=menubar)

    def _setup_ui(self):
        """Initialise tous les widgets avec le style Dark Mode."""

        # --- Cadre principal ---
        self.main_frame = tk.Frame(self.master, padx=25, pady=20, bg=Palette.BG)
        self.main_frame.pack(expand=True, fill="both")

        # --- En-tête ---
        header = tk.Frame(self.main_frame, bg=Palette.BG)
        header.pack(fill="x", pady=(0, 15))

        tk.Label(
            header,
            text="🧠 Obsidian AI Processor",
            font=("Segoe UI", 22, "bold"),
            bg=Palette.BG,
            fg=Palette.TITLE,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Analyse, restructure et exporte tes notes en Markdown pour Obsidian.",
            font=("Segoe UI", 10),
            bg=Palette.BG,
            fg=Palette.SUBTEXT,
        ).pack(anchor="w", pady=(2, 0))

        # --- Zone de texte ---
        tk.Label(
            self.main_frame,
            text="📋 Contenu à traiter (Source de texte) :",
            font=("Segoe UI", 11, "bold"),
            bg=Palette.BG,
            fg=Palette.SUBTEXT,
        ).pack(pady=(5, 5), anchor="w")

        text_container = tk.Frame(self.main_frame, bg=Palette.SURFACE_2, bd=0, highlightthickness=1,
                                   highlightbackground=Palette.BORDER)
        text_container.pack(fill="both", expand=True, padx=2)

        self.text_area = scrolledtext.ScrolledText(
            text_container,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg=Palette.SURFACE_2,
            fg=Palette.TEXT,
            insertbackground=Palette.TEXT,
            selectbackground=Palette.ACCENT,
            selectforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=12,
            bd=0,
        )
        self.text_area.pack(fill="both", expand=True, padx=1, pady=1)

        # --- Barre d'outils (style + boutons) ---
        toolbar = tk.Frame(self.main_frame, bg=Palette.BG)
        toolbar.pack(fill="x", pady=(15, 5))

        style_frame = tk.Frame(toolbar, bg=Palette.BG)
        style_frame.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(
            style_frame, text="🎨 Style de réformatage :",
            font=("Segoe UI", 10), bg=Palette.BG, fg=Palette.SUBTEXT,
        ).pack(anchor="w")

        self.styles_map = available_styles()  # {clé: libellé}
        labels = list(self.styles_map.values())
        keys = list(self.styles_map.keys())
        self._style_key_by_label = dict(zip(labels, keys))

        self.style_combo = ttk.Combobox(
            style_frame, values=labels, state="readonly", width=26, font=("Segoe UI", 10),
        )
        default_label = self.styles_map.get(DEFAULT_STYLE, labels[0])
        self.style_combo.set(default_label)
        self.style_combo.pack(pady=(4, 0))

        button_frame = tk.Frame(toolbar, bg=Palette.BG)
        button_frame.pack(side=tk.LEFT, fill="x", expand=True)

        self.load_button = HoverButton(
            button_frame, text="📂 Charger un fichier", command=self.load_file,
            bg=Palette.SUCCESS, hover_bg=Palette.SUCCESS_HOVER, fg="white",
            font=("Segoe UI", 10, "bold"), padx=14, pady=9,
        )
        self.load_button.pack(side=tk.LEFT, padx=(0, 10))

        self.reformat_button = HoverButton(
            button_frame, text="📐 Reformater le texte", command=self.apply_reformat_style,
            bg=Palette.WARNING, hover_bg=Palette.WARNING_HOVER, fg="white",
            font=("Segoe UI", 10, "bold"), padx=14, pady=9,
        )
        self.reformat_button.pack(side=tk.LEFT, padx=(0, 10))

        self.analyze_button = HoverButton(
            button_frame, text="✨ Analyser & Exporter", command=self.run_full_workflow,
            bg=Palette.ACCENT, hover_bg=Palette.ACCENT_HOVER, fg="white",
            font=("Segoe UI", 10, "bold"), padx=14, pady=9,
        )
        self.analyze_button.pack(side=tk.LEFT, padx=(0, 10))

        self.export_button = HoverButton(
            button_frame, text="💾 Exporter en Markdown", command=self.export_current_text,
            bg=Palette.SURFACE_2, hover_bg=Palette.BORDER, fg=Palette.TEXT,
            font=("Segoe UI", 10, "bold"), padx=14, pady=9,
        )
        self.export_button.pack(side=tk.LEFT)

        # --- Barre de statut ---
        status_bar = tk.Frame(self.main_frame, bg=Palette.SURFACE, height=36)
        status_bar.pack(fill="x", pady=(15, 0))

        self.status_label = tk.Label(
            status_bar,
            text="Prêt. Lancez une action pour commencer.",
            fg=Palette.STATUS_IDLE, bg=Palette.SURFACE,
            font=("Segoe UI", 10), anchor="w", padx=12, pady=8,
        )
        self.status_label.pack(fill="x")

    # ------------------------------------------------------------------
    # UTILITAIRES
    # ------------------------------------------------------------------
    def _set_status(self, text: str, kind: str = "idle"):
        color_map = {
            "ok": Palette.STATUS_OK,
            "err": Palette.STATUS_ERR,
            "wait": Palette.STATUS_WAIT,
            "idle": Palette.STATUS_IDLE,
        }
        self.status_label.config(text=text, fg=color_map.get(kind, Palette.STATUS_IDLE))

    def set_processing_state(self, is_processing: bool):
        """Active ou désactive les boutons lors d'un traitement."""
        state = tk.DISABLED if is_processing else tk.NORMAL
        for btn in (self.analyze_button, self.load_button, self.reformat_button, self.export_button):
            btn.config(state=state)

    def on_closing(self):
        if messagebox.askokcancel("Quitter", "Êtes-vous sûr de vouloir quitter ?"):
            self.master.destroy()

    def _selected_style_key(self) -> str:
        label = self.style_combo.get()
        return self._style_key_by_label.get(label, DEFAULT_STYLE)

    # ------------------------------------------------------------------
    # ACTION : Charger un fichier
    # ------------------------------------------------------------------
    def load_file(self):
        """Sélectionne un fichier et charge son contenu dans la zone de texte."""
        self.set_processing_state(True)
        self._set_status("En attente de la sélection du fichier...", "wait")
        self.master.update()

        # On réutilise la fenêtre principale existante comme parent Tk
        # (évite de créer un second tk.Tk() concurrent, source de bugs).
        file_path = select_file("Choisissez le document à lire.", parent=self.master)

        if file_path:
            raw_text = read_file_text(file_path)
            if raw_text is not None:
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert(tk.END, raw_text)
                display_status(f"Fichier chargé avec succès : {os.path.basename(file_path)}", success=True)
                self._set_status(f"✅ Fichier chargé : {os.path.basename(file_path)}", "ok")
            else:
                display_status("Échec de la lecture du fichier.", success=False)
                self._set_status("❌ Échec de la lecture du fichier.", "err")
        else:
            display_status("Chargement annulé.", success=False)
            self._set_status("Chargement annulé.", "idle")

        self.set_processing_state(False)

    # ------------------------------------------------------------------
    # ACTION : Reformater le texte selon le style choisi
    # ------------------------------------------------------------------
    def apply_reformat_style(self):
        """Reformate le contenu de la zone de texte selon le style sélectionné
        dans la liste déroulante de la barre d'outils."""
        raw_text = self.text_area.get("1.0", tk.END).strip()
        if not raw_text:
            self._set_status("Le texte est vide, rien à reformater.", "err")
            return

        style_key = self._selected_style_key()
        self.set_processing_state(True)
        try:
            reformatted = reformat_text(raw_text, style_key)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, reformatted)
            label = self.styles_map.get(style_key, style_key)
            self._set_status(f"✅ Texte reformaté au style « {label} ».", "ok")
            display_status(f"Reformatage appliqué : {label}", success=True)
        except ValueError as e:
            self._set_status(f"❌ {e}", "err")
        finally:
            self.set_processing_state(False)

    # ------------------------------------------------------------------
    # ACTION : Exporter directement le texte de la zone en .md
    # ------------------------------------------------------------------
    def export_current_text(self):
        """Exporte tel quel le contenu actuel de la zone de texte en fichier
        Markdown, à l'emplacement choisi par l'utilisateur."""
        raw_text = self.text_area.get("1.0", tk.END).strip()
        if not raw_text:
            self._set_status("Le texte est vide, rien à exporter.", "err")
            return

        save_path = filedialog.asksaveasfilename(
            parent=self.master,
            title="Exporter la note en Markdown",
            defaultextension=".md",
            initialfile="note.md",
            filetypes=(("Fichier Markdown", "*.md"), ("Tous les fichiers", "*.*")),
        )
        if not save_path:
            self._set_status("Export annulé.", "idle")
            return

        directory, filename = os.path.split(save_path)
        self.set_processing_state(True)
        display_loading("Exportation du contenu de la note en Markdown...")
        chemin_final = export_markdown(raw_text, filename, directory=directory)
        self.set_processing_state(False)

        if chemin_final:
            self._set_status(f"✅ Note exportée : {chemin_final}", "ok")
            messagebox.showinfo("Succès", f"Le fichier est prêt et sauvegardé ici :\n{chemin_final}")
        else:
            self._set_status("❌ Erreur d'exportation.", "err")
            messagebox.showerror("Erreur", "Impossible d'enregistrer le fichier. Vérifiez les permissions.")

    # ------------------------------------------------------------------
    # ACTION : Workflow complet Analyse -> Exportation
    # ------------------------------------------------------------------
    def run_full_workflow(self):
        """Orchestre le processus Analyse -> Exportation."""
        raw_text = self.text_area.get("1.0", tk.END).strip()
        if not raw_text:
            display_status("Le texte est vide. Veuillez charger ou coller du contenu.", success=False)
            self._set_status("Le texte est vide.", "err")
            return

        self.set_processing_state(True)

        try:
            # 1. ANALYSE ET STRUCTURATION
            display_loading("Analyse structurelle en cours (Déduction de titres, sous-titres)...")
            self._set_status("⏳ Analyse en cours...", "wait")
            self.master.update()
            structured_data = analyze_and_structure_text(raw_text)
            display_analysis_summary(structured_data)

            # 2. CONSTRUCTION DU MARKDOWN FINAL
            final_markdown_content = self._build_markdown(structured_data)

            # 3. CHOIX DE L'EMPLACEMENT ET EXPORTATION
            suggested_name = sanitize_filename(structured_data["title"] or "note").replace(" ", "_")
            display_loading("Finalisation : Exportation du fichier Markdown...")

            save_path = filedialog.asksaveasfilename(
                parent=self.master,
                title="Exporter l'analyse en Markdown",
                defaultextension=".md",
                initialfile=f"{suggested_name}.md",
                filetypes=(("Fichier Markdown", "*.md"), ("Tous les fichiers", "*.*")),
            )
            if not save_path:
                self._set_status("Export annulé.", "idle")
                return

            directory, filename = os.path.split(save_path)
            chemin_final = export_markdown(final_markdown_content, filename, directory=directory)

            if chemin_final:
                self._set_status(f"✅ Processus terminé ! Fichier sauvegardé : {os.path.basename(chemin_final)}", "ok")
                messagebox.showinfo("Succès", f"Le fichier est prêt et sauvegardé ici :\n{chemin_final}")
            else:
                self._set_status("❌ Erreur d'exportation. Vérifiez les permissions.", "err")
                messagebox.showerror("Erreur", "Impossible d'enregistrer le fichier. Vérifiez les permissions.")

        except Exception as e:
            self._set_status(f"💥 Erreur critique : {e}", "err")
            messagebox.showerror("Erreur", f"Une erreur inattendue est survenue : {e}")
        finally:
            self.set_processing_state(False)

    def _build_markdown(self, data):
        """Assemble le contenu markdown final à partir des données structurées."""
        title = data.get("title") or "Sans titre"
        subtitle = data.get("subtitle") or ""

        # Les alias YAML sont mis entre guillemets pour éviter de casser le
        # frontmatter si le titre/sous-titre contient des caractères spéciaux.
        alias = f"{title} - {subtitle}" if subtitle else title
        alias_safe = alias.replace('"', "'")

        metadata = (
            "---\n"
            f'title: "{title}"\n'
            f"date: {datetime.now().strftime('%Y-%m-%d')}\n"
            "tags: analyse/obsidian\n"
            f'aliases: ["{alias_safe}"]\n'
            "---\n"
        )

        final_markdown_content = metadata

        if subtitle and subtitle not in ("Pas de sous-titre majeur détecté.", ""):
            final_markdown_content += f"\n# {subtitle}\n\n"

        final_markdown_content += data.get("body_text", "")

        return final_markdown_content


# ======================================================================
# FONCTION PRINCIPALE D'EXÉCUTION
# ======================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = ObsidianTextProcessorApp(root)
    root.mainloop()
