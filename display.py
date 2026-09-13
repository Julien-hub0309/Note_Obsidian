# display.py
"""
Module de gestion du reporting de statut pour la console.
Doit être minimaliste pour ne pas interférer avec l'interface graphique.
"""
from typing import Dict


def display_status(message: str, success: bool = True) -> None:
    """Affiche un message de statut général dans la console."""
    emoji = "✅" if success else "❌"
    print(f"\n[STATUS] {emoji} {message}")


def display_loading(message: str) -> None:
    """Affiche un message d'attente dans la console."""
    print(f"\n[LOG] ⏳ {message} ... Traitement en cours.")


def display_analysis_summary(data: Dict[str, str]) -> None:
    """
    Affiche un récapitulatif de l'analyse effectuée dans la console pour le log.
    Utilise .get() partout pour ne jamais planter si une clé venait à manquer.
    """
    title = (data.get("title") or "Titre non détecté").upper()
    subtitle = (data.get("subtitle") or "Pas de sous-titre majeur détecté.").upper()
    body_text = data.get("body_text") or ""

    print("\n" + "█" * 80)
    print("          █ ANALYSE STRUCTURELLE RÉSUMÉE █")
    print("█" * 80)

    print(f"\n⭐ TITRE DÉDUIT : {title}")
    print("-" * 40)
    print(f"📚 SOUS-TITRE DÉDUIT : {subtitle}")
    print("-" * 40)

    # Afficher un extrait pour confirmation (limité pour ne pas noyer la console)
    apercu = body_text if len(body_text) <= 800 else body_text[:800] + " […]"
    print("\n📝 Aperçu du contenu structuré :\n", apercu)
    print("█" * 80)
