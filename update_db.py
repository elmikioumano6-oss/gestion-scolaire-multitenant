from database.db_config import engine, Base
from database.models import School, User

# Cette commande va créer ou mettre à jour les tables avec les nouveaux champs (actif, date_expiration)
Base.metadata.create_all(bind=engine)
print("✅ Base de données mise à jour avec succès : champs d'activation et d'expiration ajoutés !")