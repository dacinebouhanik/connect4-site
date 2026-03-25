import tensorflow as tf
from tensorflow.keras import layers, models
import numpy as np
import os

# --- CONFIGURATION SYNCHRONISÉE 9x9 ---
LIGNES = 9
COLONNES = 9
CHEMIN_MODELE = 'cerveau_expert.h5'


def creer_cerveau_tf():
    """Crée l'architecture du réseau de neurones pour un plateau 9x9"""
    model = models.Sequential([
        # Entrée : Plateau 9x9 avec 3 couches (Mes pions, Adversaire, Tour)
        layers.Input(shape=(LIGNES, COLONNES, 3)),

        # Couches de détection (Convolutions) : scanne les alignements
        layers.Conv2D(64, (4, 4), activation='relu', padding='same'),
        layers.Conv2D(64, (4, 4), activation='relu', padding='same'),
        layers.BatchNormalization(),

        layers.Flatten(),
        layers.Dense(256, activation='relu'),
        layers.Dropout(0.2),

        # Sortie : 9 neurones (un par colonne) avec probabilités (softmax)
        layers.Dense(COLONNES, activation='softmax')
    ])

    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model


def preparer_tenseur(plateau, joueur_actuel):
    """Transforme la liste 2D du jeu en tenseur 3D (9, 9, 3) pour l'IA"""
    tenseur = np.zeros((LIGNES, COLONNES, 3), dtype=np.float32)

    for r in range(LIGNES):
        for c in range(COLONNES):
            if plateau[r][c] == joueur_actuel:
                tenseur[r, c, 0] = 1.0  # Couche 0 : Mes pions
            elif plateau[r][c] != 0:
                tenseur[r, c, 1] = 1.0  # Couche 1 : Pions adverses

    # Couche 2 : Indique à l'IA si c'est au joueur 1 (Rouge) de jouer
    if joueur_actuel == 1:
        tenseur[:, :, 2] = 1.0

    return tenseur


# --- LOGIQUE DE PRÉDICTION ---

# On charge le modèle globalement pour éviter de le relire à chaque coup
model_ia = None
if os.path.exists(CHEMIN_MODELE):
    try:
        model_ia = tf.keras.models.load_model(CHEMIN_MODELE)
        print(f"✅ Succès : Modèle '{CHEMIN_MODELE}' chargé.")
    except Exception as e:
        print(f"❌ Erreur lors du chargement du modèle : {e}")


def predire_meilleur_coup_tf(plateau, joueur):
    """Demande au cerveau TensorFlow de choisir la meilleure colonne"""
    global model_ia

    if model_ia is None:
        return None  # Retourne None si le cerveau n'est pas encore entraîné

    # 1. Préparation des données
    tenseur = preparer_tenseur(plateau, joueur)
    # Ajouter la dimension de 'batch' (1, 9, 9, 3)
    input_data = np.expand_dims(tenseur, axis=0)

    # 2. Prédiction
    predictions = model_ia.predict(input_data, verbose=0)[0]

    # 3. Sécurité : On ne veut pas jouer dans une colonne pleine
    # On met le score à -1 pour les colonnes invalides
    for c in range(COLONNES):
        if plateau[0][c] != 0:  # Si la case du haut n'est pas VIDE
            predictions[c] = -1.0

    # 4. Retourner l'index de la colonne ayant la plus haute probabilité
    return int(np.argmax(predictions))