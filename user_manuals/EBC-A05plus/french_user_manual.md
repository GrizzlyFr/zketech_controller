* Paragraphes 1-4 & 6 non traduits pour l'instant*

# 1 Description du produit

# 2 Aperçu des fonctions

# 3 Spécifications

# 4 Tester le raccordement

# 5 Affichage et paramètres

## 5.1 Ecran d'interface

L'écran d'interface est divisé en six champs :
1. Première ligne
  a. Mode de test
    - CC : Décharge à courant constant
	- CP : Décharge à puissance constante
	- Ni : Charge de batterie NiCd ou NiMH
	- Li : Charge de batterie LiFe ou Liion
	- Pb : Charge de batterie plomb-acide
	- CV : Charge personnalisée à tension constante
	- MT : Monitoring de la tension et du courant
  b. Mesure de tension
  c. Mesure de courant
2. Deuxième ligne
  a. Etat du test
    - OFF : à l'arrêt
	- DSG : en décharge
	- CHG : en charge
	- ATx : en test automatique (à l'étape x)
  b. Durée d'exécution (en min)
  c. Capacité mesurée (en mAh)
  
Un appui court sur le bouton **SET** remplace la deuxième ligne par l'affichage de la durée depuis mise sous tension et la mesure de l'énergie (en mWh). Un nouvel appui court sur le bouton **SET** retourne à l'affichage original.

Un appui sur le bouton **ON** démarre le test et un nouvel appui le stoppe.

## 5.2 Interface de configuration

Dans l'interface de test, maintenez enfoncé le bouton **SET** pendant deux secondes (pendant que le test est arrêté) pour accéder à l'interface de réglage.

Remarque : cette fonction est désactivée lors d'une connection active à un ordinateur.

### 5.2.1 Ecran pour la décharge à courant constant

|*(1)*DSC-CC|*(2)*00.30A|
|*(3)*02.00V|*(4)*000Min|

1. Indique le programme de test : décharge à courant constant
2. Courant de décharge
3. Tension de coupure
4. Durée du test

Le curseur est par défaut sur le mode de test. Appuyez sur **INC** ou **DEC** pour changer de mode. Appuyez ensuite sur **SET** pour déplacer le curseur d'une position vers la droite. Appuyez sur **INC** ou **DEC** pour définir la valeur sous le curseur. Lorsque la valeur dépasse la plage autorisée, elle est automatiquement réglée. Appuyez sur le bouton **ON** pour passer rapidement l'ensemble des paramètres.

Remarques :
- Lorsque la tension mesurée est inférieure à la tension de coupure, le test s'arrête automatiquement
- La durée maximale de test est réglable de 0 à 999 minutes. Réglée à 0, la durée du test est illimitée

### 5.2.2 Ecran pour la décharge à puissance contante

|*(1)*DSC-CP|*(2)*10.0W|
|*(3)*00.00V|*(4)*000Min|

1. Indique le programme de test : décharge à puissance constante
2. Puissance de décharge
3. Tension de coupure
4. Durée du test

### 5.2.3 Ecran pour la charge de batteries standard

|*(1)*CHG-NiMH|*(2)*0.30A|
|*(3)*01|*(4)*000Min|*(5)*Auto|

1. Indique le programme de test :
- CHG-NiMh
- CHG-NiCd
- CHG-LiPo
- CHG-LiFe
- CHG-Pb
2. Courant de charge
3. Nombre de cellules
4. Temps maximal de charge
5. Indique le mode de test
- NOR : Se termine lorsque la charge est terminée
- AUTO : Effecture automatiquement trois étapes charge-décharge-charge

### 5.2.4 Ecran pour la charge personnalisée

|*(1)*CHG-CV|*(2)*0.30A|
|*(3)*04.20V|*(4)*0.01|*(5)*NOR|

1. Indique le programme de test : charge personnalisée
2. Courant de charge
3. Tension pour la phase de charge à tension constante
4. Courant de coupure
5. Identique à la charge constante

Remarque : Le test charge à courant constant la batterie jusqu'à atteindre la tension définie pour la charge à tension constante. L'appareil maintient alors cette tension jusqu'à ce que le courant atteigne le courant de coupure.

### 5.2.5 Ecran pour la mesure de tension et de courant

|*(1)*METER|
|*(3)*Cutoff:0.01A|

1. Indique le programme de test : mode moniteur de tension et de courant
2. Courant de coupure

### 5.2.6 Ecran pour la réalisation d'un test charge-décharge-charge automatique

Ce paragraphe prend en exemple une charge à tension constante.

#### (1)

Appuyez deux secondes sur **SET** pour accéder à l'interface de réglage.

|CHG-CV|0.30A|
|04.20V|0.01|NOR|

#### (2)

Déplacer le curseur sur NOR et appuyez sur **INC** ou **DEC** pour changer NOR en AUTO.

|CHG-CV|0.30A|
|04.20V|0.01|AUTO|

#### (3)

Lorsque le curseur est sur AUTO, appuyez longuement sur **ON** pour accéder à la deuxième étape de l'interface de réglage des paramètres de décharge.

|*(1)*AUTO Discharge|
|*(2)*1.00A|*(3)*01.00V|*(4)*05|

1. Mode de décharge
2. Courant de décharge
3. Tension de coupure
4. Durée de pause (minutes)

Remarque : La durée de pause (recommandé d'au moins cinq à dix minutes) est là pour laisser le temps à la batterie de refroidir avant de repasser à l'étape de décharge.

#### (4)

Une fois le réglage de décharge terminée, appuyez longuement sur **SET** pour revenir à l'interface de charge à tension constante.

|CHG-CV|0.30A|
|04.200|0.01|AUTO|

#### (5)

Une fois le réglage des paramètres terminée, appuyez longuement sur **SET** pour revenir à l'interface de test à partir de l'interface de réglage. Appuyez sur le bouton **ON** pour démarrer le test. Pour terminer les test, appuyez à nouveau sur **ON**.

#### (6)

Une fois le test terminé, appuyez sur **INC** ou **DEC** pour afficher les résultats de chaque étape.

|Auto Test:|
|AT1: CV 2000mAh|

|Auto Test:|
|AT2: CV 1999mAh|

|Auto Test:|
|AT3: CV 2000mAh|

# 6 Exemple de paramétrage