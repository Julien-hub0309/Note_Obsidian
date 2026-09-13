import re
from typing import Dict


def analyze_and_structure_text(raw_text: str) -> Dict[str, str]:
    """
    Analyse le texte brut en utilisant des heuristiques pour déduire :
    1. Le Titre (Titre principal de la note).
    2. Le Sous-titre (La première section majeure du document).
    3. Le Corps (Le texte nettoyé et structuré).

    :param raw_text: Le texte brut récupéré (par exemple, depuis un fichier .md).
    :return: Un dictionnaire contenant 'title', 'subtitle', et 'body_text'.
    """

    print("✨ Analyse en cours des structures et des patrons...")

    # Initialisation des variables de sortie
    title = "Titre non détecté"
    subtitle = "Pas de sous-titre majeur détecté."

    # --- ÉTAPE 1: Nettoyage préliminaire ---
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    if not lines:
        return {"title": "", "subtitle": "", "body_text": ""}

    # --- ÉTAPE 2: Détection du Titre et du Sous-titre ---

    # Heuristique 1 : le titre principal est souvent la première ligne
    # non-formatée (pas déjà un en-tête Markdown).
    first_line = lines[0]

    if not re.match(r"^#+\s", first_line):
        title = first_line
        lines_working = lines[1:]
    else:
        lines_working = lines

    if not lines_working:
        # Il ne restait que le titre, aucun corps de texte.
        return {"title": title, "subtitle": subtitle, "body_text": ""}

    # Heuristique 2 : le sous-titre est souvent le premier en-tête
    # Markdown (## ...) ou une ligne fortement mise en avant (MAJUSCULES).
    subtitle_index = -1
    for i, line in enumerate(lines_working):
        if re.match(r"^#+.*$", line) and len(line) > 5 and any(char.isupper() for char in line):
            subtitle = line.lstrip("#").strip()
            subtitle_index = i
            break

    # --- ÉTAPE 3: Construction du Corps de Texte (sans duplication) ---
    if subtitle_index != -1:
        # Le corps inclut le sous-titre détecté et tout ce qui le suit.
        # (Bug corrigé : on ne concatène plus deux fois les mêmes lignes.)
        body_lines = lines_working[subtitle_index:]
    else:
        # Pas de sous-titre clair : tout le texte restant est le corps.
        body_lines = lines_working

    body_text = clean_body_text("\n".join(body_lines))

    return {
        "title": title,
        "subtitle": subtitle,
        "body_text": body_text,
    }


def clean_body_text(text: str) -> str:
    """Nettoie le texte pour s'assurer que les séparations de paragraphes sont optimales."""
    # Remplace les multiples sauts de lignes par deux sauts de lignes (standard Markdown)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    # Supprime les espaces en début/fin de ligne
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text


# ======================================================================
# TEST DU MODULE
# ======================================================================
if __name__ == "__main__":
    test_raw_text = """
Les grandes capitales sont des endroits fascinants.
On y trouve beaucoup d'histoire.

## Théorie des liens
Il est crucial de bien comprendre la théorie des liens.
Cette théorie explique comment les choses sont connectées, comme les réseaux.
Il faut lire le guide de base pour bien maîtriser le sujet.

# L'Histoire Romaine

Rome était une capitale incroyablement importante. L'empire romain a laissé beaucoup de vestiges.
Quand on étudie l'histoire, on doit regarder des sources comme Jules César ou des textes anciens.

La Renaissance a été une période de réveil artistique. Elle a eu un impact sur toute l'Europe.
N'oubliez pas que l'architecture de Florence est un exemple parfait. #Art #Histoire

---

Résumé des points clés
1. Ne pas oublier les dates.
2. Lire le guide pour améliorer vos connaissances.
3. La méthode d'étude est clé.
"""

    resultat = analyze_and_structure_text(test_raw_text)

    print("\n" + "=" * 80)
    print("          📊 ANALYSE STRUCTURELLE RÉSUMÉE 📊")
    print("=" * 80)

    print(f"\n⭐ TITRE DÉDUIT : {resultat['title'].upper()}")
    print("-" * 40)
    print(f"📚 SOUS-TITRE DÉDUIT : {resultat['subtitle'].upper()}")
    print("-" * 40)
    print("\n✍️ CORPS DU TEXTE OPTIMISÉ :\n")
    print(resultat["body_text"])
