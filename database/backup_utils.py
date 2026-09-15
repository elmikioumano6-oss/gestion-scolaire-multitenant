import json
from datetime import datetime
from database.db_config import SessionLocal
from database.models import School, User, Classe, Eleve, Matiere, Note, Paiement, Depense

def executer_sauvegarde_complete():
    """Génère un dictionnaire JSON complet contenant toutes les données critiques des tenants."""
    db = SessionLocal()
    try:
        donnees_sauvegarde = {
            "metadata": {
                "date_sauvegarde": str(datetime.now()),
                "plateforme": "Gestion Scolaire Pro - Multi-Tenant"
            },
            "schools": [{"id": s.id, "nom": s.nom, "code": s.code, "devise": s.devise} for s in db.query(School).all()],
            "users": [{"username": u.username, "role": u.role, "school_id": u.school_id} for u in db.query(User).all()],
            "classes": [{"id": c.id, "libelle": c.libelle, "school_id": c.school_id} for c in db.query(Classe).all()],
            "eleves": [{"id": e.id, "nom": e.nom, "prenom": e.prenom, "classe_id": e.classe_id} for e in db.query(Eleve).all()],
            "notes": [{"id": n.id, "valeur": n.valeur, "eleve_id": n.eleve_id} for n in db.query(Note).all()],
            "paiements": [{"id": p.id, "montant": p.montant, "eleve_id": p.eleve_id} for p in db.query(Paiement).all()],
            "depenses": [{"id": d.id, "montant": d.montant, "motif": d.motif} for d in db.query(Depense).all()]
        }
        return json.dumps(donnees_sauvegarde, ensure_ascii=False, indent=4)
    finally:
        db.close()