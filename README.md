# 📸 PhotoBooth Manager

Application complète de gestion pour votre business de location de photobooth.

## Fonctionnalités

- ✅ **Devis & Factures** — Création, modification, PDF, numérotation automatique
- ✅ **Suivi clients** — Base de données, historique, CA par client
- ✅ **Suivi paiements** — Acomptes, reste à payer, statuts complets
- ✅ **Calendrier** — Vue mensuelle des événements avec codes couleur
- ✅ **Export iCal** — Synchronisation avec Google Calendar / Apple Calendar
- ✅ **Tableau de bord** — Stats, graphique CA, prochains événements
- ✅ **100% responsive** — Fonctionne sur mobile ET ordinateur

## Installation

### Étape 1 — Python (si pas déjà installé)
Télécharger sur https://python.org

### Étape 2 — Installer les dépendances
```bash
cd photobooth
pip install -r requirements.txt
```

### Étape 3 — Lancer l'application
```bash
python app.py
```

### Étape 4 — Ouvrir dans le navigateur
Aller sur : **http://localhost:5000**

## Accès depuis téléphone (même réseau Wi-Fi)

1. Sur l'ordinateur, noter votre IP locale (ex: 192.168.1.42)
   - Mac : `ifconfig | grep "inet "`
   - Windows : `ipconfig`
2. Depuis le téléphone : **http://192.168.1.42:5000**

## Statuts des devis/factures

| Statut | Couleur | Signification |
|--------|---------|---------------|
| Devis | 🟡 Jaune | Proposition envoyée, en attente |
| Accepté | 🔵 Bleu | Client a dit oui |
| Facture | 🟣 Violet | Facture émise, paiement attendu |
| Payé | 🟢 Vert | Paiement reçu |
| Annulé | ⚫ Gris | Annulation |

## Export Calendrier

Cliquer sur "Export iCal" pour télécharger un fichier `.ics`
- **Google Calendar** : Paramètres > Importer
- **Apple Calendar** : Double-cliquer sur le fichier
- **Outlook** : Fichier > Importer

## PDF

Les PDFs sont générés avec WeasyPrint. Si l'installation pose problème,
le bouton PDF affiche le document dans le navigateur que vous pouvez imprimer.

## Données

Les données sont stockées localement dans `instance/photobooth.db` (SQLite).
Pensez à sauvegarder ce fichier régulièrement !
# Photo-Booth-manager
