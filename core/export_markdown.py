import os
import re
from typing import Optional

# Caractères interdits (ou à risque) dans un nom de fichier sous Windows/macOS/Linux
_INVALID_FILENAME_CHARS = re.compile(r'[\\/*?:"<>|\n\r\t]')


def sanitize_filename(filename: str, fallback: str = "note_sans_titre") -> str:
    """Nettoie un nom de fichier pour qu'il soit valide sur tous les OS.

    Corrige un bug latent : un titre déduit automatiquement (ex: contenant
    '/', ':' ou '?') pouvait auparavant faire planter l'écriture du fichier.
    """
    cleaned = _INVALID_FILENAME_CHARS.sub("_", filename).strip(" .")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or fallback


def export_markdown(content: str, filename: str, directory: Optional[str] = None) -> Optional[str]:
    """
    Écrit le contenu de chaîne de caractères Markdown dans un fichier au format .md.

    :param content: Le texte Markdown complet à enregistrer.
    :param filename: Le nom souhaité pour le fichier (avec ou sans extension .md).
    :param directory: Dossier de destination. Par défaut, le dossier courant.
    :return: Le chemin absolu du fichier créé, ou None en cas d'échec.
    """
    safe_name = sanitize_filename(filename)
    if not safe_name.lower().endswith(".md"):
        safe_name += ".md"

    target_dir = directory or os.getcwd()

    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError as e:
        print(f"\n❌ ERREUR : Impossible de créer le dossier de destination : {e}")
        return None

    full_file_path = os.path.join(target_dir, safe_name)

    print(f"\n💾 Tentative d'exportation vers : {full_file_path}")

    try:
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ Exportation réussie !")
        print(f"Le fichier Markdown a été créé avec succès : {os.path.abspath(full_file_path)}")
        return os.path.abspath(full_file_path)

    except PermissionError:
        print("\n❌ ERREUR : Permission refusée.")
        print("   Veuillez vérifier les droits d'écriture dans ce dossier.")
        return None
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE lors de l'exportation : {e}")
        return None


# ======================================================================
# EXEMPLE DE TEST
# ======================================================================
if __name__ == "__main__":
    exemple_content = """---
title: Test de l'Export Markdown
date: 2024-01-01
tags: test/export
---

# Sous-titre de Test

Ceci est un paragraphe de test.
Le contenu est écrit avec succès dans le format Markdown.

* Point 1
* Point 2
"""

    desired_filename = "Test_Export_Final"
    chemin_final = export_markdown(exemple_content, desired_filename)

    if chemin_final:
        print("\n----------------------------------------------------")
        print("Le fichier est prêt ! Vous le trouverez ici :")
        print(chemin_final)
        print("----------------------------------------------------")
