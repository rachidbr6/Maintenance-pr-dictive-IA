# Pilotage du projet

8 semaines, un périmètre technique large, des contraintes d'accès terrain subies. La partie pilotage a conditionné la partie technique plus que l'inverse.

## Instances

**Réunion hebdomadaire d'avancement** avec l'encadrante industrielle (ingénieur maintenance), les techniciens impliqués dans l'instrumentation, et ponctuellement le responsable d'atelier pour toute décision touchant la production (pose de capteurs, arrêt programmé pour inspection).

Format tenu : jalon, état, points bloquants. Un tableau de bord d'une page, mis à jour avant chaque réunion.

## Registre de risques

| Risque | Probabilité | Sévérité | Mitigation | Réalisé ? |
|---|---|---|---|---|
| Indisponibilité des capteurs terrain | Moyenne | Élevée | Priorisation des équipements critiques, capteurs de secours identifiés en amont | Partiellement |
| Connectivité réseau limitée en atelier | Faible | Moyenne | Traitement local sur passerelle, pas de dépendance au cloud | Non |
| Résistance au changement des techniciens | Moyenne | Moyenne | Formation structurée, démonstrations sur cas réels | Non |
| Qualité dégradée du signal vibratoire | Moyenne | Élevée | Ajustement du taux de contamination, filtrage adaptatif | **Oui** |
| Dépassement du planning | Faible | Moyenne | Jalons hebdomadaires, arbitrage des priorités en réunion | Non |

Le seul risque réalisé a été la qualité du signal. Les premiers réglages de l'Isolation Forest produisaient trop de faux positifs, ce qui alimentait directement le risque d'adoption : quelques alertes injustifiées suffisent à ce qu'un technicien cesse de regarder l'outil. Traité en ajustant le taux de contamination et en filtrant le signal en amont de l'extraction de features.

## Ce que les techniciens ont changé

Trois décisions issues du terrain, pas de la conception :

- **Les seuils d'alerte.** Initialement théoriques, donc trop bas, donc bruyants. Recalibrés sur les valeurs observées en fonctionnement nominal.
- **Les gammes opératoires.** Révisées en tenant compte de l'outillage et de la formation réellement disponibles, pas de ce que la procédure supposait.
- **La fenêtre de validation terrain.** L'inspection du roulement diagnostiqué a été calée sur un arrêt déjà programmé, ce qui a rendu la vérification possible sans coût de production.

## Formation

Deux sessions, ciblées :

1. **Lecture des dashboards** — indicateurs TRS/OEE, interprétation des zones ISO 20816, remontée d'information terrain.
2. **Interprétation d'un rapport de diagnostic** — ce que signifie un pic BPFO, ce que la sévérité ISO dit et ne dit pas.

Documents produits : gammes de lubrification, procédure d'alignement laser, fiche de collecte vibratoire.

## Analyse causale — 5 Pourquoi

Sur le défaut de roulement confirmé :

| | Question → réponse |
|---|---|
| 1 | Pourquoi un défaut de piste extérieure ? → Écaillage dû à un chargement anormal |
| 2 | Pourquoi ce chargement anormal ? → Désalignement résiduel après la dernière révision |
| 3 | Pourquoi le désalignement n'a-t-il pas été corrigé ? → Pas de mesure par aligneur laser au remontage |
| 4 | Pourquoi l'aligneur n'a-t-il pas été utilisé ? → Non mentionné dans la gamme opératoire |
| 5 | Pourquoi la gamme ne le prévoit-elle pas ? → Gamme non mise à jour depuis une modification de la pompe en 2018 |

**Action :** mise à jour de la gamme, alignement laser rendu obligatoire pour tout remontage de pompe ou motoréducteur, formation associée.

La valeur de cette analyse dépasse le système de surveillance : elle corrige la cause d'un mode de défaillance récurrent sur l'atelier. Un système prédictif qui détecte cinq fois le même défaut sans qu'on remonte à sa cause n'a pas rempli sa fonction.
