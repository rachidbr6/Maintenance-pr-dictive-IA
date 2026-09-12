# Pipeline IoT

## Acquisition

**Fréquence d'échantillonnage : 25 600 Hz.** C'est une valeur usuelle des collecteurs vibratoires. La justification est directe : l'analyse d'enveloppe exploite des bandes de résonance de structure situées typiquement entre 3 et 10 kHz. La fréquence de Nyquist doit donc dépasser 10 kHz avec de la marge pour le filtre anti-repliement — 25 600 Hz place Nyquist à 12 800 Hz.

> Note : ISO 10816 porte sur l'évaluation de la sévérité vibratoire à partir de mesures sur parties non tournantes. Elle ne prescrit pas de fréquence d'échantillonnage. Le choix de 25,6 kHz relève de la contrainte de bande d'analyse ci-dessus, pas d'une exigence normative.

**Autres grandeurs.** Thermocouples type K (± 0,5 °C) sur les paliers ; capteurs de pression différentielle sur filtres et circuits hydrauliques. Ces voies sont lentes et échantillonnées à la seconde.

## Fenêtrage et débit

Le point d'architecture le plus important du pipeline.

Un capteur à 25 600 Hz produit 25 600 valeurs par seconde. Sur 18 équipements, publier le brut représenterait ~460 000 messages/s — infaisable sur un réseau atelier, et sans intérêt puisque la quasi-totalité de ce flux décrit un état nominal.

La passerelle :

1. accumule une fenêtre de 1 s en mémoire ;
2. calcule RMS, kurtosis, facteur de crête, amplitude crête-à-crête, niveaux d'enveloppe aux fréquences BPFO et BPFI ;
3. publie un message JSON d'une dizaine de champs ;
4. conserve le bloc brut dans un tampon circulaire, exporté uniquement sur demande.

Facteur de réduction : ~2500. Le bloc brut n'est remonté que lorsqu'une anomalie est confirmée.

## Transport

Convention de topic :

```
site/{site}/{atelier}/{equipement}/{grandeur}
```

Exemple : `site/pilote/preparation/K201/vibration_features`

QoS 1 (« au moins une fois ») : la perte d'une fenêtre est tolérable, la duplication l'est aussi puisque InfluxDB écrase sur clé `(measurement, tags, timestamp)`. QoS 2 coûterait un aller-retour supplémentaire sans bénéfice ici.

**Sécurité.** La configuration de ce dépôt utilise `allow_anonymous true` — développement local uniquement. En atelier : TLS, un compte par passerelle, ACL restreignant chaque passerelle en écriture à son propre préfixe de topic.

## Stockage

Schéma InfluxDB :

- measurement : `vibration_features`
- tags : `asset`, `bearing`
- fields : `rms`, `kurtosis`, `crest_factor`, `peak_to_peak`, `bpfo_level`, `bpfi_level`, `temperature`, `shaft_speed_hz`
- précision : milliseconde

Les tags sont indexés, les fields non : mettre l'identifiant d'équipement en tag est ce qui rend les requêtes par machine efficaces. Mettre une valeur continue en tag serait l'erreur symétrique (explosion de la cardinalité des séries).

## Restitution Power BI

Connexion à InfluxDB via connecteur ODBC. Le rapport expose :

- niveaux RMS temps réel avec seuils colorés A/B/C/D ;
- tendances de température sur 30 jours ;
- alertes générées par la détection d'anomalies ;
- TRS/OEE mensuel de l'atelier.

**Ce qui a fait la différence sur l'adoption, ce n'est pas le dashboard.** Ce sont les seuils. Les valeurs initiales étaient théoriques et produisaient trop d'alertes ; les techniciens ont cessé de les regarder. Recalibrés sur la base de leurs retours terrain, les mêmes dashboards sont devenus un outil consulté quotidiennement. Un seuil mal réglé tue un outil plus sûrement qu'un bug.
