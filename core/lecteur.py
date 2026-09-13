import tkinter as tk
from tkinter import filedialog
from typing import Optional


def select_file(
    prompt: str = "Veuillez sélectionner le fichier à lire.",
    parent: Optional[tk.Misc] = None,
) -> Optional[str]:
    """
    Ouvre la boîte de dialogue de sélection de fichier de l'OS et renvoie
    le chemin complet du fichier sélectionné.

    :param prompt: Le message de titre à afficher dans la fenêtre de sélection.
    :param parent: Fenêtre Tk parente déjà existante (ex: la fenêtre principale
                    de l'application). Si None, une racine Tk temporaire et
                    cachée est créée puis détruite pour cet usage ponctuel.
                    IMPORTANT : créer un second tk.Tk() alors qu'une fenêtre
                    principale tourne déjà provoque des bugs d'affichage
                    (fenêtres fantômes, blocages) — d'où ce paramètre.
    :return: Le chemin du fichier sélectionné, ou None si l'utilisateur annule.
    """
    print("--- Ouverture de la boîte de dialogue de sélection de fichier ---")

    owns_root = False
    root = parent
    if root is None:
        root = tk.Tk()
        root.withdraw()
        owns_root = True

    try:
        file_path = filedialog.askopenfilename(
            parent=root,
            title=prompt,
            filetypes=(
                ("Fichiers Markdown", "*.md"),
                ("Fichiers Texte", "*.txt"),
                ("Tous les fichiers", "*.*"),
            ),
        )
    finally:
        if owns_root:
            root.destroy()

    return file_path or None


def read_file_text(file_path: str) -> Optional[str]:
    """
    Lit le contenu texte d'un fichier donné par son chemin.
    Tente l'UTF-8 en priorité, puis se rabat sur Latin-1 si besoin
    au lieu d'échouer purement et simplement.

    :param file_path: Le chemin complet du fichier.
    :return: Le contenu du fichier sous forme de chaîne de caractères (str), ou None en cas d'erreur.
    """
    if not file_path:
        print("❌ Erreur : Aucun chemin de fichier n'a été fourni.")
        return None

    print(f"\n⚙️ Tentative de lecture du fichier : {file_path}")

    for encoding in ("utf-8", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                text_content = f.read()
            print(f"✅ Lecture terminée avec succès (encodage : {encoding}).")
            return text_content
        except FileNotFoundError:
            print(f"❌ Erreur : Le fichier n'a pas été trouvé au chemin : {file_path}")
            return None
        except UnicodeDecodeError:
            if encoding == "utf-8":
                print("⚠️ Attention : Impossible de décoder en UTF-8, nouvel essai en Latin-1...")
                continue
            print("❌ Impossible de décoder le fichier, même en Latin-1.")
            return None
        except Exception as e:
            print(f"❌ Une erreur inattendue s'est produite lors de la lecture : {e}")
            return None

    return None


# ======================================================================
# POINT D'ENTRÉE POUR TESTER LE MODULE
# ======================================================================
if __name__ == "__main__":
    print("================================================")
    print("     Lecteur de fichiers pour l'analyse de texte")
    print("================================================")

    chemin_selectionne = select_file("Choisissez le document que vous souhaitez analyser.")

    if chemin_selectionne:
        contenu = read_file_text(chemin_selectionne)

        if contenu:
            print("\n" + "=" * 80)
            print("         📄 CONTENU DU FICHIER LECTURÉ (extrait)         ")
            print("=" * 80)

            extrait = contenu[:500] + ("..." if len(contenu) > 500 else "")
            print(extrait)
