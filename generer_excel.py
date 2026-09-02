import pandas as pd

# Données officielles des 32 couples matière-niveau du premier cycle
donnees_programmes = [
    ["ANG6", "Anglais (6e)", 3, 96, "Annuel", "Life At School, Domestic, Family Life, Shopping and Vacation, Health, Tradition, School Events"],
    ["ANG5", "Anglais (5e)", 3, 96, "Annuel", "Life in the City, Celebrations, Folk Tales, Traveling, Health, Hobbies, Recreation, Environment"],
    ["ANG4", "Anglais (4e)", 3, 100, "Annuel", "Story Telling, Health and Entertainment, Farming, Education, History"],
    ["ANG3", "Anglais (3e)", 3, 100, "Annuel", "Tradition in Niger, Sports, Social Conflicts, Juvenile, Environment"],
    ["EFS6", "Économie familiale et sociale (6e)", 2, 25, "Annuel", "Alimentation de l'enfant et de l'adolescent, Hygiène alimentaire"],
    ["EFS5", "Économie familiale et sociale (5e)", 2, 25, "Annuel", "Préparation au sevrage, Reproduction humaine, La grossesse"],
    ["EFS4", "Économie familiale et sociale (4e)", 2, 25, "Annuel", "L'enfant en bonne santé, L'enfant et la maladie, Prévention"],
    ["EFS3", "Économie familiale et sociale (3e)", 2, 25, "Annuel", "Santé de l'enfant, Maladies infectieuses, Pratiques néfastes, Toxicomanie"],
    ["EPS6", "Éducation physique et sportive (6e)", 2, 50, "Annuel", "Recherche d'allure, Courses, Éducation motrice"],
    ["EPS5", "Éducation physique et sportive (5e)", 2, 50, "Annuel", "Posture, foulée adaptée, Endurance"],
    ["EPS4", "Éducation physique et sportive (4e)", 2, 50, "Annuel", "Connaissance et maîtrise des allures, Poussée, Endurance"],
    ["EPS3", "Éducation physique et sportive (3e)", 2, 50, "Annuel", "Soutien et maintien d'une course, Accélération, Gymnastique"],
    ["FR6", "Français (6e)", 4, 156, "Annuel", "Communication, salutations, description, grammaire de base"],
    ["FR5", "Français (5e)", 4, 104, "Annuel", "Donner des informations, situer dans l'espace/temps, enrichir le récit"],
    ["FR4", "Français (4e)", 4, 104, "Annuel", "Présentation d'un objet/être, récits, justification des faits"],
    ["FR3", "Français (3e)", 4, 104, "Annuel", "Informer, récits complexes, argumentation thèse-antithèse"],
    ["HG6", "Histoire-Géographie (6e)", 3, 75, "Annuel", "Préhistoire, Égypte ancienne, Grèce, Rome, Islam"],
    ["HG5", "Histoire-Géographie (5e)", 3, 75, "Annuel", "Empires du Soudan (Ghana, Mali, Songhay), Traite des Noirs, Empire Ottoman"],
    ["HG4", "Histoire-Géographie (4e)", 3, 75, "Annuel", "Étude de la Terre, Climat, Vents, Précipitations, Relief, Eaux"],
    ["HG3", "Histoire-Géographie (3e)", 3, 75, "Annuel", "Peuples, langues, religions, Démographie, Urbanisation, Présentation du Niger"],
    ["MATH6", "Mathématiques (6e)", 4, 182, "Annuel", "Droites dans le plan, Segments, Fractions, Angles, Cercles, Triangles, Statistiques"],
    ["MATH5", "Mathématiques (5e)", 4, 130, "Annuel", "Division euclidienne, Nombres premiers, Angles, Triangles, Puissances, Équations"],
    ["MATH4", "Mathématiques (4e)", 4, 130, "Annuel", "Nombres rationnels, Symétries, Puissances, Calcul littéral, Statistiques, Théorème de Pythagore"],
    ["MATH3", "Mathématiques (3e)", 4, 130, "Annuel", "Propriétés de Thalès, Vecteurs, Monômes et polynômes, Trigonométrie, Fonctions"],
    ["PC6", "Sciences physiques (6e)", 2, 50, "Annuel", "Propriétés physiques de la matière, Combustions, Température, Électricité"],
    ["PC5", "Sciences physiques (5e)", 2, 50, "Annuel", "Séparation physique, Distillation, Masse volumique, Électromagnétisme"],
    ["PC4", "Sciences physiques (4e)", 3, 75, "Annuel", "Mécanique, Dissolution, Structure de la matière, Température, Électricité, Optique"],
    ["PC3", "Sciences physiques (3e)", 3, 100, "Annuel", "Mécanique, Chimie minérale, Électricité, Optique, Chimie organique"],
    ["SVT6", "Sciences de la vie et de la terre (6e)", 2, 50, "Annuel", "Environnement, Reproduction, Respiration chez les vertébrés, Géologie"],
    ["SVT5", "Sciences de la vie et de la terre (5e)", 2, 50, "Annuel", "Gestion des ressources, Digestion, Reproduction humaine, Sols, Volcanisme"],
    ["SVT4", "Sciences de la vie et de la terre (4e)", 2, 50, "Annuel", "Milieu intérieur, Nutrition, Circulation sanguine, Fonction de relation, Immunité"],
    ["SVT3", "Sciences de la vie et de la terre (3e)", 2, 50, "Annuel", "Milieu intérieur, Nutrition humaine, Système immunitaire, Séismes"]
]

df_complet = pd.DataFrame(donnees_programmes, columns=[
    "Code_Matiere", "Nom_Matiere", "Coefficient", "Volume_Horaire", "Semestre", "Description"
])

# Export direct au format Excel
nom_fichier = "progression_college_complete_niger.xlsx"
df_complet.to_excel(nom_fichier, index=False, sheet_name='Programmes_College')
print(f"✅ Fichier Excel généré avec succès : {nom_fichier}")