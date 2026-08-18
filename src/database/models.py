from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Modele(Base):
    __tablename__ = "modeles"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    fournisseur = Column(String)
    version = Column(String)
    cout_par_1k_tokens = Column(Float)
    date_ajout = Column(DateTime, default=datetime.utcnow)


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    departement = Column(String, nullable=False)
    metier = Column(String)
    nom_cas_usage = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    sortie_attendue = Column(Text)
    critere_succes = Column(Text)


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"))
    modele_id = Column(Integer, ForeignKey("modeles.id"))
    reponse_generee = Column(Text)
    latence_secondes = Column(Float)
    cout_estime = Column(Float)
    date_execution = Column(DateTime, default=datetime.utcnow)

    scenario = relationship("Scenario")
    modele = relationship("Modele")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("executions.id"))
    critere = Column(String)
    note = Column(Float)
    commentaire = Column(Text)

    execution = relationship("Execution")


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    mot_de_passe_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    departement = Column(String, nullable=True)  # For client role: which department they can access
    date_creation = Column(DateTime, default=datetime.utcnow)