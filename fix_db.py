python -c "
import sqlite3
conn = sqlite3.connect('database.db') # ou le nom de votre fichier de base de données (ex: ecole.db)
cursor = conn.cursor()
try:
    cursor.execute('ALTER TABLE user ADD COLUMN enseignant_id INTEGER;')
    conn.commit()
    print('Colonne enseignant_id ajoutée avec succès !')
except Exception as e:
    print('Information :', e)
try:
    cursor.execute('ALTER TABLE user ADD COLUMN derniere_activite DATETIME;')
    conn.commit()
    print('Colonne derniere_activite ajoutée avec succès !')
except Exception as e:
    print('Information :', e)
conn.close()
"