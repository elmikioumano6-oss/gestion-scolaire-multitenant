from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db_config import Base

class School(Base):
    __tablename__ = "schools"
    
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(150), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    devise = Column(String(255), default="Excellence - Persévérance - Réussite")
    adresse = Column(String(255), default="Quartier, Niamey - Niger")
    contacts = Column(String(255), default="N/D")
    logo = Column(String(255), nullable=True)
    
    actif = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft Delete ERP
    date_expiration = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    annees = relationship("AnneeScolaire", back_populates="school", cascade="all, delete-orphan")
    classes = relationship("Classe", back_populates="school", cascade="all, delete-orphan")
    eleves = relationship("Eleve", back_populates="school", cascade="all, delete-orphan")
    users = relationship("User", back_populates="school", cascade="all, delete-orphan")
    matieres = relationship("Matiere", back_populates="school", cascade="all, delete-orphan")
    enseignants = relationship("Enseignant", back_populates="school", cascade="all, delete-orphan")

class AnneeScolaire(Base):
    __tablename__ = "annees_scolaires"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    libelle = Column(String, index=True)
    active = Column(Boolean, default=False)
    date_debut = Column(Date, nullable=True)
    date_fin = Column(Date, nullable=True)

    school = relationship("School", back_populates="annees")

class Classe(Base):
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    libelle = Column(String, index=True)
    niveau = Column(String, nullable=True)
    cycle = Column(String, default="Collège")
    capacite = Column(Integer, default=30)
    
    frais_scolarite = Column(Float, default=0.0)
    frais_inscription = Column(Float, default=0.0)
    frais_transport = Column(Float, default=0.0)
    frais_cantine = Column(Float, default=0.0)
    frais_coges = Column(Float, default=0.0)
    
    deleted_at = Column(DateTime, nullable=True)  # Soft Delete ERP

    school = relationship("School", back_populates="classes")
    eleves = relationship("Eleve", back_populates="classe", cascade="all, delete-orphan")

    @property
    def nom(self):
        return self.libelle

    @nom.setter
    def nom(self, value):
        self.libelle = value

class Eleve(Base):
    __tablename__ = "eleves"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    nom = Column(String, index=True)
    prenom = Column(String, index=True)
    matricule = Column(String, unique=True, index=True)
    sexe = Column(String, nullable=True)
    cycle = Column(String, default="Collège")
    classe_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    tuteur = Column(String, nullable=True)
    
    type_reduction = Column(String, default="Aucune")
    montant_reduction = Column(Float, default=0.0)
    document_justificatif = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    deleted_at = Column(DateTime, nullable=True)  # Soft Delete ERP

    school = relationship("School", back_populates="eleves")
    classe = relationship("Classe", back_populates="eleves")
    notes = relationship("Note", back_populates="eleve", cascade="all, delete-orphan")
    presences = relationship("Presence", back_populates="eleve", cascade="all, delete-orphan")
    paiements = relationship("Paiement", back_populates="eleve", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    
    derniere_activite = Column(DateTime, nullable=True)
    changer_mdp_requis = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft Delete ERP

    enseignant_id = Column(Integer, ForeignKey("enseignants.id"), nullable=True)
    eleve_id = Column(Integer, ForeignKey("eleves.id"), nullable=True)

    school = relationship("School", back_populates="users")
    enseignant = relationship("Enseignant", foreign_keys=[enseignant_id])
    eleve = relationship("Eleve", foreign_keys=[eleve_id])

class Matiere(Base):
    __tablename__ = "matieres"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    libelle = Column(String, index=True, nullable=True)
    code = Column(String, nullable=True)
    coefficient = Column(Float, default=1.0)
    cycle = Column(String, default="Collège", nullable=False)

    school = relationship("School", back_populates="matieres")

    @property
    def nom(self):
        return self.libelle

    @nom.setter
    def nom(self, value):
        self.libelle = value

class Programme(Base):
    __tablename__ = "programmes"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    code_matiere = Column(String, index=True, nullable=True)
    nom_matiere = Column(String, nullable=True)
    coefficient = Column(Float, default=1.0)
    volume_horaire = Column(Float, default=0.0)
    semestre = Column(String, nullable=True)
    description = Column(String, nullable=True)

class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    eleve_id = Column(Integer, ForeignKey("eleves.id"))
    matiere_id = Column(Integer, ForeignKey("matieres.id"), nullable=True)
    valeur = Column(Float)
    semestre = Column("trimestre", String, default="Trimestre 1")
    type_evaluation = Column(String)

    eleve = relationship("Eleve", back_populates="notes")
    matiere = relationship("Matiere")

class Enseignant(Base):
    __tablename__ = "enseignants"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    nom = Column(String, index=True)
    prenom = Column(String, index=True)
    specialite = Column(String, nullable=True)
    qualite = Column(String, nullable=True)
    telephone = Column(String, nullable=True)
    statut = Column(String, default="Permanent")
    volume_horaire = Column(Float, default=18.0)
    classes_attribuees = Column(String, nullable=True)
    matieres_attribuees = Column(String, nullable=True)

    school = relationship("School", back_populates="enseignants")

class Affectation(Base):
    __tablename__ = "affectations"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    enseignant_id = Column(Integer, ForeignKey("enseignants.id"), nullable=True)
    classe_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    matiere_id = Column(Integer, ForeignKey("matieres.id"), nullable=True)

    enseignant = relationship("Enseignant")
    classe = relationship("Classe")
    matiere = relationship("Matiere")

class Presence(Base):
    __tablename__ = "presences"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    eleve_id = Column(Integer, ForeignKey("eleves.id"), nullable=True)
    date = Column(Date, nullable=True)
    statut = Column(String, nullable=True)
    motif = Column(String, nullable=True)

    eleve = relationship("Eleve", back_populates="presences")

class EmploiDuTemps(Base):
    __tablename__ = "emplois_du_temps"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    classe_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    classe = Column(String, nullable=True)
    jour = Column(String)
    heure = Column(String)
    matiere = Column(String)
    enseignant = Column(String)

    classe_rel = relationship("Classe")

class CahierTexte(Base):
    __tablename__ = "cahiers_texte"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    classe_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    matiere_id = Column(Integer, ForeignKey("matieres.id"), nullable=True)
    enseignant_username = Column(String, ForeignKey("users.username"), nullable=True)
    date = Column(DateTime, nullable=True)
    contenu_realise = Column(String, nullable=True)
    difficultees = Column(String, nullable=True)
    mesures_correctives = Column(String, nullable=True)
    duree = Column(Float, default=1.0)

    classe = relationship("Classe")
    matiere = relationship("Matiere")
    enseignant = relationship("User")

class EcheancePaiement(Base):
    __tablename__ = "echeances_paiements"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    libelle = Column(String)
    montant_attendu = Column(Float)
    date_limite = Column(Date, nullable=True)

class PlanificationEvaluation(Base):
    __tablename__ = "planification_evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    classe_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    matiere_id = Column(Integer, ForeignKey("matieres.id"), nullable=True)
    type_evaluation = Column(String)
    periode = Column(String, nullable=True)
    date_eval = Column(Date, nullable=True)
    horaire = Column(String, nullable=True)
    coefficient = Column(Integer, default=2)
    salle = Column(String, nullable=True)

    classe = relationship("Classe")
    matiere = relationship("Matiere")

class ActivityLog(Base):
    __tablename__ = "journal_activites"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    username = Column(String, nullable=True)
    action = Column(String, nullable=True)
    module = Column(String, nullable=True)
    statut = Column(String, default="Succès")
    
    ip_address = Column(String(50), default="127.0.0.1")
    session_id = Column(String(100), default="SES-PROD-01")
    valeur_avant = Column(Text, nullable=True)
    valeur_apres = Column(Text, nullable=True)

JournalActivite = ActivityLog

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    level = Column(String(50), default="ERROR")
    source = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    stacktrace = Column(Text, nullable=True)

class Paiement(Base):
    __tablename__ = "paiements"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    reference_recu = Column(String, unique=True, index=True)
    eleve_id = Column(Integer, ForeignKey("eleves.id"))
    montant = Column(Float, nullable=False)
    mode_reglement = Column(String)
    motif = Column(String)
    nom_payeur = Column(String)
    contact_payeur = Column(String)
    agent_caisse = Column(String)
    date_paiement = Column(DateTime)

    eleve = relationship("Eleve", back_populates="paiements")

class Depense(Base):
    __tablename__ = 'depenses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)
    cycle = Column(String(50), nullable=False)
    libelle = Column(String(200), nullable=False)
    montant = Column(Float, nullable=False)
    categorie = Column(String(100), nullable=False)
    date_depense = Column(DateTime, default=datetime.now)
    auteur = Column(String(100), nullable=True)