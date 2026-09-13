from __future__ import annotations

import importlib.util
import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

# ── Vérification des dépendances ────────────────────────────────
def _check_dep(name: str, install: str) -> None:
    if importlib.util.find_spec(name) is None:
        print(f"[ERREUR] '{name}' manquant. pip install {install}")
        sys.exit(1)

_check_dep("customtkinter", "customtkinter")

# ── Modules internes ─────────────────────────────────────────────
# FIX : les imports étaient brisés (module.detecteur / core.creation inexistants).
# On importe directement depuis les fichiers voisins.
try:
    from detecteur import analyze_text, analyze_file, AnalysisResult
except ModuleNotFoundError:
    print("[ERREUR] 'detecteur.py' introuvable dans le même dossier.")
    sys.exit(1)

try:
    from anti_detecteur import MetadataCleaner
except ModuleNotFoundError:
    print("[ERREUR] 'anti_detecteur.py' introuvable dans le même dossier.")
    sys.exit(1)

try:
    from refile import TextReformatter, STYLE_LABELS
except ModuleNotFoundError:
    print("[ERREUR] 'refile.py' introuvable dans le même dossier.")
    sys.exit(1)

# ── Palette & typographie ────────────────────────────────────────
C_BG      = "#0F1117"
C_PANEL   = "#1A1D27"
C_PANEL2  = "#21253A"
C_ACCENT  = "#6C63FF"
C_ACCENT2 = "#8B85FF"
C_TEXT    = "#E8E6F0"
C_MUTED   = "#7A788A"
C_BORDER  = "#2E3247"
C_GREEN   = "#2ECC71"
C_ORANGE  = "#F39C12"
C_RED     = "#FF6B6B"

FONT_MONO   = ("JetBrains Mono", 11)
FONT_MONO_S = ("JetBrains Mono", 9)
FONT_BODY   = ("Inter", 11)
FONT_BODY_S = ("Inter", 9)
FONT_LABEL  = ("Inter", 10)

PLACEHOLDER = "Collez ou saisissez le texte ici…"


def score_color(s: float) -> str:
    """Couleur selon le score IA (0 = humain/vert, 100 = IA/rouge)."""
    if s < 20:  return C_GREEN
    if s < 40:  return "#A8E063"
    if s < 55:  return C_ORANGE
    if s < 70:  return "#FF8C42"
    return C_RED


class CircularGauge(tk.Canvas):
    SIZE   = 200
    STROKE = 14

    def __init__(self, master: tk.Widget) -> None:
        super().__init__(
            master,
            width=self.SIZE, height=self.SIZE,
            bg=C_PANEL, highlightthickness=0,
        )
        self._target  = 0.0
        self._current = 0.0
        self._color   = C_MUTED
        self._label   = "En attente…"
        self._draw(0.0, C_MUTED, "En attente…", C_MUTED)

    def _draw(self, ratio: float, color: str, label: str, label_color: str) -> None:
        self.delete("all")
        cx = cy = self.SIZE // 2
        r  = cx - self.STROKE - 6

        self.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-360,
            outline=C_BORDER, width=self.STROKE, style="arc",
        )
        if ratio > 0:
            self.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=90, extent=-ratio * 360,
                outline=color, width=self.STROKE, style="arc",
            )
        self.create_text(cx, cy - 12, text=f"{ratio * 100:.0f}",
                         font=("JetBrains Mono", 38, "bold"), fill=color)
        self.create_text(cx, cy + 22, text="/100",
                         font=("JetBrains Mono", 11), fill=C_MUTED)
        self.create_text(cx, cy + 46, text=label,
                         font=("Inter", 9), fill=label_color,
                         width=self.SIZE - 20, justify="center")

    def animate_to(self, target: float, color: str, label: str) -> None:
        self._target = target
        self._color  = color
        self._label  = label
        self._step()

    def _step(self) -> None:
        delta = self._target - self._current
        if abs(delta) < 0.003:
            self._current = self._target
            self._draw(self._current, self._color, self._label, self._color)
            return
        self._current += delta * 0.12
        self._draw(self._current, self._color, self._label, self._color)
        self.after(16, self._step)

    def reset(self) -> None:
        self._current = 0.0
        self._target  = 0.0
        self._draw(0.0, C_MUTED, "En attente…", C_MUTED)


class DimensionBar(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkFrame, name: str) -> None:
        super().__init__(master, fg_color="transparent")
        self.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text=name, font=FONT_LABEL,
            text_color=C_MUTED, width=160,
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self._bg = ctk.CTkFrame(self, height=6, fg_color=C_BORDER, corner_radius=3)
        self._bg.grid(row=0, column=1, sticky="ew")
        self._bg.grid_propagate(False)

        self._fill = ctk.CTkFrame(self._bg, height=6, fg_color=C_ACCENT, corner_radius=3)
        self._fill.place(relheight=1, relwidth=0)

        self._lbl = ctk.CTkLabel(
            self, text="—", font=FONT_MONO_S,
            text_color=C_MUTED, width=38,
        )
        self._lbl.grid(row=0, column=2, padx=(8, 0))

    def set_value(self, ratio: float) -> None:
        color = score_color(ratio * 100)
        self._fill.configure(fg_color=color)
        self._fill.place(relwidth=max(0.0, min(1.0, ratio)))
        self._lbl.configure(text=f"{ratio * 100:.0f}%", text_color=color)


class MetaCard(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkFrame, label: str) -> None:
        super().__init__(master, fg_color=C_PANEL2, corner_radius=8)
        ctk.CTkLabel(self, text=label, font=FONT_BODY_S, text_color=C_MUTED).pack(pady=(10, 0))
        self._v = ctk.CTkLabel(
            self, text="—",
            font=("JetBrains Mono", 18, "bold"), text_color=C_TEXT,
        )
        self._v.pack(pady=(2, 10))

    def set(self, val: str, color: str = C_TEXT) -> None:
        self._v.configure(text=val, text_color=color)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("AI Detector")
        self.geometry("1150x740")
        self.minsize(940, 640)
        self.configure(fg_color=C_BG)

        self._pending_file: Path | None = None
        self._last_result: AnalysisResult | None = None
        self._cleaner = MetadataCleaner()
        self._reformatter = TextReformatter()
        self._label_to_style: dict[str, str] = {
            v: k for k, v in STYLE_LABELS.items()
        }

        self._build_ui()

    # ── Construction de l'UI ─────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=0, minsize=390)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_left()
        self._build_right()

    def _build_left(self) -> None:
        left = ctk.CTkFrame(self, fg_color=C_PANEL)
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)

        # En-tête
        h = ctk.CTkFrame(left, fg_color="transparent")
        h.grid(row=0, column=0, sticky="ew", padx=20, pady=(22, 0))
        ctk.CTkLabel(h, text="◈  AI DETECTOR",
                     font=("JetBrains Mono", 14, "bold"),
                     text_color=C_ACCENT).pack(anchor="w")
        ctk.CTkLabel(h, text="Analyse forensique de texte",
                     font=FONT_BODY_S, text_color=C_MUTED).pack(anchor="w")

        ctk.CTkFrame(left, height=1, fg_color=C_BORDER).grid(
            row=1, column=0, sticky="ew", padx=20, pady=14)

        ctk.CTkLabel(left, text="TEXTE À ANALYSER",
                     font=FONT_MONO_S, text_color=C_MUTED).grid(
            row=2, column=0, sticky="w", padx=20)

        # Zone de saisie
        self._text_input = ctk.CTkTextbox(
            left, font=FONT_BODY, fg_color=C_PANEL2,
            text_color=C_MUTED, border_color=C_BORDER,
            border_width=1, corner_radius=8, wrap="word",
        )
        self._text_input.grid(row=3, column=0, sticky="nsew", padx=20, pady=(6, 12))
        self._text_input.insert("1.0", PLACEHOLDER)
        self._text_input.bind("<FocusIn>",  self._clear_placeholder)
        self._text_input.bind("<FocusOut>", self._restore_placeholder)

        # Bouton import
        ctk.CTkButton(
            left, text="⊕  Importer un fichier",
            fg_color=C_PANEL2, hover_color=C_PANEL,
            text_color=C_MUTED, border_color=C_BORDER,
            border_width=1, corner_radius=8, height=36,
            command=self._import_file,
        ).grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 10))

        # Bouton Analyser
        self._analyze_btn = ctk.CTkButton(
            left, text="Analyser",
            fg_color=C_ACCENT, hover_color=C_ACCENT2,
            text_color="white", corner_radius=8, height=42,
            command=self._launch_analysis,
        )
        self._analyze_btn.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 6))

        # Sélecteur de mode d'humanisation
        self._mode_var = ctk.StringVar(value="subtil")
        mode_row = ctk.CTkFrame(left, fg_color="transparent")
        mode_row.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 4))
        mode_row.columnconfigure(1, weight=1)
        ctk.CTkLabel(mode_row, text="Mode :", font=FONT_LABEL,
                     text_color=C_MUTED).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkOptionMenu(
            mode_row,
            variable=self._mode_var,
            values=["subtil", "fort", "extreme", "furtif", "etudiant",
                    "pro", "academique", "journaliste", "technique",
                    "scientifique", "juridique", "medical", "marketing",
                    "historique", "philo"],
            fg_color=C_PANEL2, button_color=C_ACCENT,
            button_hover_color=C_ACCENT2, dropdown_fg_color=C_PANEL2,
            text_color=C_TEXT, font=FONT_BODY_S, corner_radius=8,
        ).grid(row=0, column=1, sticky="ew")

        # Bouton Humaniser
        self._humanize_btn = ctk.CTkButton(
            left, text="Humaniser le texte",
            fg_color="#3A3A8C", hover_color="#5050B8",
            text_color="white", corner_radius=8, height=42,
            command=self._launch_humanize,
        )
        self._humanize_btn.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 6))

        # Bouton Export JSON
        self._export_btn = ctk.CTkButton(
            left, text="Exporter JSON",
            fg_color="transparent", hover_color=C_PANEL2,
            text_color=C_MUTED, border_color=C_BORDER,
            border_width=1, corner_radius=8, height=32,
            command=self._export_json, state="disabled",
        )
        self._export_btn.grid(row=8, column=0, sticky="ew", padx=20, pady=(0, 6))

        # Bouton Réinitialiser
        ctk.CTkButton(
            left, text="Réinitialiser",
            fg_color="transparent", hover_color=C_PANEL2,
            text_color=C_MUTED, border_color=C_BORDER,
            border_width=1, corner_radius=8, height=32,
            command=self._reset,
        ).grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 16))

        # ── Séparateur + bloc Reformatage ──────────────────────
        ctk.CTkFrame(left, height=1, fg_color=C_BORDER).grid(
            row=10, column=0, sticky="ew", padx=20, pady=(0, 12))

        ctk.CTkLabel(left, text="REFORMATER LE TEXTE",
                     font=FONT_MONO_S, text_color=C_MUTED).grid(
            row=11, column=0, sticky="w", padx=20, pady=(0, 6))

        self._refile_var = ctk.StringVar(value="pave")
        refile_row = ctk.CTkFrame(left, fg_color="transparent")
        refile_row.grid(row=12, column=0, sticky="ew", padx=20, pady=(0, 6))
        refile_row.columnconfigure(1, weight=1)
        ctk.CTkLabel(refile_row, text="Style :", font=FONT_LABEL,
                     text_color=C_MUTED).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkOptionMenu(
            refile_row,
            variable=self._refile_var,
            values=list(STYLE_LABELS.values()),
            fg_color=C_PANEL2, button_color=C_ACCENT,
            button_hover_color=C_ACCENT2, dropdown_fg_color=C_PANEL2,
            text_color=C_TEXT, font=FONT_BODY_S, corner_radius=8,
        ).grid(row=0, column=1, sticky="ew")

        self._refile_btn = ctk.CTkButton(
            left, text="Reformater le texte",
            fg_color=C_PANEL2, hover_color=C_PANEL,
            text_color=C_TEXT, border_color=C_BORDER,
            border_width=1, corner_radius=8, height=36,
            command=self._launch_refile,
        )
        self._refile_btn.grid(row=13, column=0, sticky="ew", padx=20, pady=(0, 16))

        # Barre de progression (masquée par défaut)
        self._progress = ctk.CTkProgressBar(
            left, fg_color=C_BORDER, progress_color=C_ACCENT,
            corner_radius=4, height=4,
        )
        self._progress.grid(row=14, column=0, sticky="ew", padx=20, pady=(0, 4))
        self._progress.set(0)
        self._progress.grid_remove()

        # Statut
        self._status_lbl = ctk.CTkLabel(
            left, text="", font=FONT_BODY_S, text_color=C_MUTED)
        self._status_lbl.grid(row=15, column=0, pady=(0, 16))

    def _build_right(self) -> None:
        right = ctk.CTkScrollableFrame(self, fg_color=C_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        # ── Jauges + métadonnées ──────────────────────────────────
        sec = ctk.CTkFrame(right, fg_color=C_PANEL, corner_radius=12)
        sec.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        sec.columnconfigure(1, weight=1)

        gwrap = ctk.CTkFrame(sec, fg_color="transparent")
        gwrap.grid(row=0, column=0, padx=20, pady=20)
        self._gauge = CircularGauge(gwrap)
        self._gauge.pack()

        meta = ctk.CTkFrame(sec, fg_color="transparent")
        meta.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        meta.columnconfigure((0, 1), weight=1)

        self._card_verdict    = MetaCard(meta, "VERDICT")
        self._card_verdict.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self._card_tokens     = MetaCard(meta, "TOKENS")
        self._card_tokens.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        self._card_confidence = MetaCard(meta, "CONFIANCE")
        self._card_confidence.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        ctk.CTkFrame(right, height=1, fg_color=C_BORDER).grid(
            row=1, column=0, sticky="ew", padx=20, pady=4)

        # ── Barres de dimensions ──────────────────────────────────
        dim_frame = ctk.CTkFrame(right, fg_color=C_PANEL, corner_radius=12)
        dim_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        dim_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dim_frame, text="DÉTAIL PAR DIMENSION",
            font=FONT_MONO_S, text_color=C_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 8))

        self._dim_bars: dict[str, DimensionBar] = {}
        dims = [
            "Perplexité lex.",
            "Uniformité phrases",
            "Marqueurs IA",
            "Richesse ponctuation",
            "Diversité lexicale",
            "Structures IA",
            "Burstiness",
            "Ton assertif/prudent",
        ]
        for i, name in enumerate(dims):
            bar = DimensionBar(dim_frame, name)
            bar.grid(row=i + 1, column=0, sticky="ew", padx=20, pady=4)
            self._dim_bars[name] = bar

        ctk.CTkFrame(dim_frame, height=1, fg_color=C_BORDER).grid(
            row=len(dims) + 1, column=0, sticky="ew", padx=20, pady=(8, 0))

        # Légende
        legend = ctk.CTkFrame(dim_frame, fg_color="transparent")
        legend.grid(row=len(dims) + 2, column=0, sticky="w", padx=20, pady=(6, 14))
        for color, label in [
            (C_GREEN,  "< 20 — Humain"),
            (C_ORANGE, "40-55 — Incertain"),
            (C_RED,    "> 70 — IA"),
        ]:
            dot = tk.Frame(legend, width=10, height=10, bg=color)
            dot.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(legend, text=label, font=FONT_BODY_S,
                         text_color=C_MUTED).pack(side="left", padx=(0, 14))

        # ── Avertissements ────────────────────────────────────────
        self._warn_frame = ctk.CTkFrame(right, fg_color=C_PANEL, corner_radius=12)
        self._warn_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        self._warn_frame.columnconfigure(0, weight=1)
        self._warn_frame.grid_remove()

        self._warn_label = ctk.CTkLabel(
            self._warn_frame, text="",
            font=FONT_BODY_S, text_color=C_ORANGE, justify="left",
        )
        self._warn_label.grid(row=0, column=0, sticky="ew", padx=20, pady=12)

    # ── Placeholder ──────────────────────────────────────────────

    def _clear_placeholder(self, _: tk.Event = None) -> None:
        if self._text_input.get("1.0", "end-1c") == PLACEHOLDER:
            self._text_input.delete("1.0", "end")
            self._text_input.configure(text_color=C_TEXT)

    def _restore_placeholder(self, _: tk.Event = None) -> None:
        if not self._text_input.get("1.0", "end-1c").strip():
            self._text_input.insert("1.0", PLACEHOLDER)
            self._text_input.configure(text_color=C_MUTED)

    # ── Import fichier ───────────────────────────────────────────

    def _import_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("Documents", "*.txt *.pdf *.docx *.md"),
                ("Tous", "*.*"),
            ]
        )
        if not path:
            return
        self._pending_file = Path(path)
        self._status_lbl.configure(
            text=f"📄 {self._pending_file.name}", text_color=C_MUTED)
        self._text_input.configure(text_color=C_MUTED)
        self._text_input.delete("1.0", "end")
        self._text_input.insert("1.0", f"[FICHIER] {path}")

    # ── Analyse ──────────────────────────────────────────────────

    def _launch_analysis(self) -> None:
        raw = self._text_input.get("1.0", "end-1c").strip()
        if not raw or raw == PLACEHOLDER:
            self._status_lbl.configure(
                text="Aucun texte à analyser.", text_color=C_RED)
            return

        self._set_busy(True, "Analyse en cours…")
        self._gauge.reset()
        self._warn_frame.grid_remove()
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self) -> None:
        try:
            raw = self._text_input.get("1.0", "end-1c").strip()
            if raw.startswith("[FICHIER] ") and self._pending_file:
                result = analyze_file(self._pending_file)
                self._pending_file = None
            else:
                result = analyze_text(raw)
            self.after(0, lambda: self._show_result(result))
        except Exception as exc:
            msg = str(exc)
            self.after(0, lambda m=msg: (
                self._set_busy(False),
                self._status_lbl.configure(text=f"Erreur : {m}", text_color=C_RED),
            ))

    # ── Humanisation ─────────────────────────────────────────────

    def _launch_humanize(self) -> None:
        """Lance l'humanisation dans un thread séparé pour ne pas bloquer l'UI."""
        raw = self._text_input.get("1.0", "end-1c").strip()
        if not raw or raw == PLACEHOLDER:
            self._status_lbl.configure(
                text="Aucun texte à humaniser.", text_color=C_RED)
            return

        self._set_busy(True, "Humanisation en cours…")
        threading.Thread(
            target=self._run_humanize, args=(raw, self._mode_var.get()), daemon=True
        ).start()

    def _run_humanize(self, raw: str, mode: str) -> None:
        try:
            # FIX : utilisation directe de MetadataCleaner (create_humanized_file
            # n'existe pas dans core.creation — module inexistant dans le projet).
            humanized = self._cleaner._human_targeted(raw, mode)

            # Si un fichier source était sélectionné, on le sauvegarde aussi.
            saved_path: Path | None = None
            if self._pending_file:
                out_path = self._pending_file.with_stem(
                    self._pending_file.stem + "_humanisé"
                )
                out_path.write_text(humanized, encoding="utf-8")
                saved_path = out_path
                self._pending_file = None

            self.after(0, lambda: self._apply_humanized(humanized, saved_path))
        except Exception as exc:
            msg = str(exc)
            self.after(0, lambda m=msg: (
                self._set_busy(False),
                self._status_lbl.configure(text=f"Erreur humanisation : {m}", text_color=C_RED),
            ))

    def _apply_humanized(self, text: str, saved_path: Path | None) -> None:
        self._set_busy(False)
        self._text_input.configure(text_color=C_TEXT)
        self._text_input.delete("1.0", "end")
        self._text_input.insert("1.0", text)

        if saved_path:
            self._status_lbl.configure(
                text=f"✔ Fichier sauvegardé : {saved_path.name}",
                text_color=C_GREEN)
        else:
            self._status_lbl.configure(
                text="✔ Texte humanisé.", text_color=C_GREEN)

    # ── Reformatage (refile) ─────────────────────────────────────

    def _launch_refile(self) -> None:
        """Lance le reformatage de syntaxe dans un thread séparé."""
        raw = self._text_input.get("1.0", "end-1c").strip()
        if not raw or raw == PLACEHOLDER:
            self._status_lbl.configure(
                text="Aucun texte à reformater.", text_color=C_RED)
            return
        if raw.startswith("[FICHIER] "):
            self._status_lbl.configure(
                text="Le reformatage ne s'applique qu'au texte saisi.",
                text_color=C_RED)
            return

        label = self._refile_var.get()
        style_key = self._label_to_style.get(label, "pave")

        self._set_busy(True, "Reformatage en cours…")
        threading.Thread(
            target=self._run_refile, args=(raw, style_key), daemon=True
        ).start()

    def _run_refile(self, raw: str, style_key: str) -> None:
        try:
            reformatted = self._reformatter.reformat(raw, style_key)
            self.after(0, lambda: self._apply_refile(reformatted))
        except Exception as exc:
            msg = str(exc)
            self.after(0, lambda m=msg: (
                self._set_busy(False),
                self._status_lbl.configure(text=f"Erreur de reformatage : {m}", text_color=C_RED),
            ))

    def _apply_refile(self, text: str) -> None:
        self._set_busy(False)
        self._text_input.configure(text_color=C_TEXT)
        self._text_input.delete("1.0", "end")
        self._text_input.insert("1.0", text)
        self._status_lbl.configure(text="✔ Texte reformaté.", text_color=C_GREEN)


    # ── Export JSON ──────────────────────────────────────────────

    def _export_json(self) -> None:
        if self._last_result is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tous", "*.*")],
            initialfile="analyse_ai.json",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._last_result.to_dict(), fh, ensure_ascii=False, indent=2)
            self._status_lbl.configure(
                text=f"✔ Exporté : {Path(path).name}", text_color=C_GREEN)
        except Exception as exc:
            messagebox.showerror("Erreur d'export", str(exc))

    # ── Affichage des résultats ──────────────────────────────────

    def _show_result(self, result: AnalysisResult) -> None:
        self._last_result = result
        self._set_busy(False)

        color = score_color(result.score)
        self._gauge.animate_to(result.score / 100, color, result.verdict)
        self._card_verdict.set(result.verdict, color)
        self._card_tokens.set(str(result.token_count))

        conf_color = {
            "faible":  C_RED,
            "modérée": C_ORANGE,
            "élevée":  C_GREEN,
        }.get(result.confidence, C_TEXT)
        self._card_confidence.set(result.confidence.capitalize(), conf_color)

        for dim in result.dimensions:
            if dim.name in self._dim_bars:
                self._dim_bars[dim.name].set_value(dim.score)

        if result.warnings:
            self._warn_frame.grid()
            self._warn_label.configure(
                text="⚠  " + "\n⚠  ".join(result.warnings))
        else:
            self._warn_frame.grid_remove()

        self._export_btn.configure(state="normal")
        self._status_lbl.configure(text="✔ Analyse terminée.", text_color=C_GREEN)

    # ── État occupé / libre ──────────────────────────────────────

    def _set_busy(self, busy: bool, label: str = "") -> None:
        state = "disabled" if busy else "normal"
        self._analyze_btn.configure(
            state=state,
            text=label if busy else "Analyser",
        )
        self._humanize_btn.configure(
            state=state,
            text=label if busy else "Humaniser le texte",
        )
        self._refile_btn.configure(
            state=state,
            text=label if busy else "Reformater le texte",
        )
        if busy:
            self._progress.grid()
            self._progress.configure(mode="indeterminate")
            self._progress.start()
            self._status_lbl.configure(text=label, text_color=C_MUTED)
        else:
            self._progress.stop()
            self._progress.configure(mode="determinate")
            self._progress.set(0)
            self._progress.grid_remove()

    # ── Réinitialisation ─────────────────────────────────────────

    def _reset(self) -> None:
        self._text_input.delete("1.0", "end")
        self._text_input.insert("1.0", PLACEHOLDER)
        self._text_input.configure(text_color=C_MUTED)
        self._gauge.reset()
        self._card_verdict.set("—")
        self._card_tokens.set("—")
        self._card_confidence.set("—")
        for bar in self._dim_bars.values():
            bar.set_value(0)
        self._warn_frame.grid_remove()
        self._status_lbl.configure(text="", text_color=C_MUTED)
        self._export_btn.configure(state="disabled")
        self._last_result  = None
        self._pending_file = None
        self._set_busy(False)


if __name__ == "__main__":
    app = App()
    app.mainloop()