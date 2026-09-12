# Diagnostic vibratoire

## Pourquoi la FFT directe ne suffit pas

Un écaillage naissant sur une piste de roulement produit, à chaque passage d'un élément roulant, un choc bref. Ce choc excite une résonance de la structure (quelques kHz) qui s'amortit en quelques millisecondes.

Dans le spectre direct, cette énergie est répartie sur un large bande haute fréquence et reste très en dessous du balourd à `fr` et de ses harmoniques. Le défaut existe, il est mesuré, et il est invisible.

L'information n'est pas dans la fréquence de la résonance — elle est dans **la périodicité avec laquelle cette résonance est réexcitée**. C'est une modulation d'amplitude, et c'est ce que l'analyse d'enveloppe extrait.

## Chaîne de traitement

1. **Filtrage passe-bande** 3–10 kHz : on isole la bande de résonance et on élimine le balourd basse fréquence qui écraserait tout.
2. **Démodulation de Hilbert** : construction du signal analytique `xₐ(t) = x(t) + j·x̂(t)`, l'enveloppe est `e(t) = |xₐ(t)|`.
3. **FFT moyennée de l'enveloppe** : blocs recouvrants à 50 %, moyennage quadratique. La variance du plancher de bruit chute d'un facteur √n, au prix de la résolution. Sans ce moyennage, les raies de défaut ne se distinguent pas du bruit.
4. **Appariement** des pics aux fréquences `BPFO`, `BPFI`, `BSF`, `FTF` et à leurs harmoniques, avec tolérance relative (2 % par défaut).

## Fréquences caractéristiques

Pour un roulement de `Z` éléments, diamètre d'élément `d`, diamètre primitif `D`, angle de contact `α`, arbre à `fr` :

| Défaut | Formule |
|---|---|
| BPFO (piste extérieure) | `(Z/2)·fr·(1 − (d/D)·cos α)` |
| BPFI (piste intérieure) | `(Z/2)·fr·(1 + (d/D)·cos α)` |
| BSF (élément roulant) | `(D/2d)·fr·(1 − ((d/D)·cos α)²)` |
| FTF (cage) | `(fr/2)·(1 − (d/D)·cos α)` |

**Contrôle de cohérence à faire systématiquement.** Divisez la fréquence par `fr` : vous obtenez un ordre. Pour un roulement rigide à billes courant, BPFO tombe entre 2 et 5, BPFI entre 3 et 7, FTF toujours sous 0,5. Un pic présenté comme BPFO à un ordre de 5,7 sur un roulement à 8 billes n'est pas un BPFO — c'est une harmonique, ou une erreur de géométrie dans le catalogue.

Pour un SKF 6317 (`Z = 8`, `d ≈ 34,9 mm`, `D ≈ 132,5 mm`, `α = 0`) :

| | Ordre | À 24,8 Hz (1488 tr/min) |
|---|---|---|
| BPFO | 2,946 | 73,0 Hz |
| BPFI | 5,054 | 125,4 Hz |
| BSF | 1,765 | 43,8 Hz |
| FTF | 0,368 | 9,1 Hz |

Ces valeurs sont vérifiées par `tests/test_diagnostics.py`.

> La géométrie du catalogue embarqué est indicative et doit être confrontée à la fiche constructeur. Un nombre d'éléments roulants erroné décale toutes les fréquences et rend le diagnostic faux sans le rendre suspect — c'est le mode de défaillance le plus dangereux de cette chaîne.

## Indicateurs temporels

| Indicateur | Formule | Lecture |
|---|---|---|
| RMS | `√(⟨x²⟩)` | Énergie globale ; monte tard dans la dégradation |
| Kurtosis | `⟨(x−x̄)⁴⟩/σ⁴` | ≈ 3 pour du bruit gaussien ; > 6 signale des impacts |
| Facteur de crête | `max\|x\|/RMS` | Sensible aux chocs isolés, mais sature quand le défaut se généralise |

Le kurtosis est le meilleur détecteur précoce des trois — et il redescend quand le défaut s'étend et que les impacts deviennent continus. Un kurtosis qui baisse n'est donc pas nécessairement une bonne nouvelle : il faut le lire avec le RMS.

## Sévérité ISO 20816-3

Machines > 15 kW, 120–15 000 tr/min, vitesse vibratoire efficace bande 10–1000 Hz :

| Zone | État | v RMS (mm/s) | Recommandation |
|---|---|---|---|
| A | Bon | < 2,3 | Surveillance normale |
| B | Acceptable | 2,3 – 4,5 | Surveillance rapprochée |
| C | Alerte | 4,5 – 7,1 | Intervention à planifier |
| D | Danger | ≥ 7,1 | Arrêt à envisager |

L'intégration accélération → vitesse se fait dans le domaine fréquentiel (`v(f) = a(f)/2πf`) : une intégration temporelle dérive et fausse le niveau.

**Ces zones et l'analyse d'enveloppe répondent à des questions différentes.** Un roulement en défaut naissant reste typiquement en zone A ou B — c'est normal, le niveau global n'a pas encore bougé. Classer un équipement « bon » sur la seule base ISO 20816 et s'arrêter là, c'est rater exactement les défauts qu'on cherche à anticiper.

## Estimation de durée de vie résiduelle

Trois modèles sont documentés dans la littérature et implémentables ici : linéaire `F(t) = F₀ + βt`, exponentiel `F(t) = F₀·e^(λt)`, et Weibull.

Ils ne sont **pas implémentés dans ce dépôt**, pour une raison assumée : leur calibration exige un historique de dégradation de plusieurs mois par type d'équipement. Sur un pilote de 8 semaines, toute RUL produite serait un nombre sans support statistique — et un nombre faux est plus dangereux qu'une absence de nombre quand il arrive dans un planning de maintenance.
