# Architecture

## Principe : deux niveaux, deux questions différentes

| | Niveau 1 — surveillance | Niveau 2 — diagnostic |
|---|---|---|
| Question | Quelque chose a-t-il changé ? | Quoi exactement, et à quel point ? |
| Déclenchement | Continu, tous les équipements | À la demande, sur alerte confirmée |
| Traitement | Indicateurs statistiques + Isolation Forest | FFT, enveloppe, fréquences de défaut, ISO 20816-3 |
| Donnée manipulée | Features (≈10 flottants/s/capteur) | Bloc de signal brut (25 600 pts/s) |
| Sortie | Alerte + dashboard | Défaut qualifié, sévérité, rapport |

Cette séparation n'est pas cosmétique. Lancer une analyse d'enveloppe en continu sur tout le parc coûterait cher en calcul et en bande passante pour un gain nul : 99 % du temps, il n'y a rien à diagnostiquer. À l'inverse, se contenter du niveau 1 laisse le technicien devant une alerte sans interprétation — ce qui est précisément la situation qui faisait durer une analyse 4,5 heures.

## Couches

**Terrain.** Accéléromètres piézoélectriques sur les paliers, thermocouples type K pour la température de palier, capteurs de pression différentielle sur les circuits hydrauliques.

**Passerelle edge.** Fenêtrage du signal à 1 seconde, extraction des indicateurs, horodatage milliseconde, sérialisation JSON, publication MQTT. C'est là que le volume de données est divisé par ~2500.

**Transport.** Broker MQTT (Mosquitto 2.0). Convention de topic : `site/{site}/{atelier}/{equipement}/{grandeur}`. Le modèle publish/subscribe découple producteurs et consommateurs : on ajoute un consommateur (dashboard, archivage, alerting) sans toucher aux passerelles.

**Stockage.** InfluxDB, base série temporelle. Le choix contre un SGBD relationnel se justifie par le profil d'écriture : flux continu, append-only, requêtes quasi toujours bornées dans le temps, et rétention par politique automatique.

**Analytique.** Isolation Forest pour la détection, Power BI pour la restitution (connecteur ODBC vers InfluxDB).

**Diagnostic.** Déclenché sur alerte confirmée, à partir du bloc brut exporté en CSV.

## Choix techniques et leurs contreparties

| Choix | Raison | Ce qu'on paie |
|---|---|---|
| MQTT plutôt que REST | En-tête de 2 octets, publish/subscribe, résiste aux coupures réseau | Pas de requête/réponse : tout le contrôle de flux est à écrire |
| InfluxDB plutôt que PostgreSQL | Écritures haute fréquence, compression série temporelle, rétention native | Requêtes relationnelles (jointures sur référentiel équipement) plus lourdes |
| Isolation Forest | Aucun historique étiqueté disponible | Ne qualifie pas le défaut, sensible à la qualité de la baseline |
| Features à l'edge, brut à la demande | Le réseau atelier ne supporte pas le brut continu | Pas de rejeu a posteriori sur les périodes non archivées en brut |
| Traitement local | Confidentialité industrielle | Pas de mutualisation multi-sites sans architecture supplémentaire |

## Flux nominal

1. Le capteur échantillonne à 25 600 Hz ; la passerelle accumule 1 seconde.
2. Extraction des features → publication MQTT (~10 valeurs).
3. Le collecteur écrit dans InfluxDB et score la fenêtre.
4. Score négatif → alerte. Le dashboard Power BI l'affiche, le bloc brut correspondant est exporté en CSV.
5. Diagnostic : FFT, enveloppe, appariement des pics aux fréquences de défaut, classement ISO 20816-3.
6. Rapport transmis à la planification maintenance.
