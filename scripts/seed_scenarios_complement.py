"""
Complète le catalogue de scénarios jusqu'à 16 par département.
Dédoublonne automatiquement sur (departement, nom_cas_usage) — peut être
relancé sans risque de créer des doublons.

Usage:
    python scripts/seed_scenarios_complement.py --dry-run
    python scripts/seed_scenarios_complement.py --apply
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import SessionLocal
from src.database.models import Scenario


NOUVEAUX_SCENARIOS = [
    # =========================================================
    # RH & Communication — 5 existants, +11 pour atteindre 16
    # =========================================================
    Scenario(
        departement="RH & Communication",
        metier="Recruteur / Talent Acquisition Specialist",
        nom_cas_usage="Rédaction d'annonce LinkedIn attractive",
        prompt="Transforme cette fiche de poste technique en annonce LinkedIn engageante pour un poste de Data Analyst, ton dynamique, avec appel à l'action clair.",
        sortie_attendue="Annonce courte (150-200 mots), accroche forte, ton humain, hashtags pertinents, CTA de candidature.",
        critere_succes="Ton engageant (pas administratif), structure scannable, absence de jargon RH excessif."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Recruteur / Talent Acquisition Specialist",
        nom_cas_usage="Réponse de refus de candidature personnalisée",
        prompt="Rédige un email de refus bienveillant pour un candidat ayant passé un entretien technique mais non retenu, en soulignant un point positif de son profil.",
        sortie_attendue="Email court et respectueux (100-150 mots), mentionne un point fort du candidat, ouvre la porte à de futures opportunités.",
        critere_succes="Ton empathique, pas de formule générique impersonnelle, aucune information confidentielle divulguée."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Chargé de Formation / L&D",
        nom_cas_usage="Conception de plan de formation individuel",
        prompt="Propose un plan de formation sur 6 mois pour un développeur junior souhaitant monter en compétence sur l'architecture cloud, à raison de 4h/semaine.",
        sortie_attendue="Plan structuré par mois avec objectifs, ressources suggérées et jalons d'évaluation.",
        critere_succes="Progression logique et réaliste, charge horaire respectée, jalons mesurables."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Chargé de Formation / L&D",
        nom_cas_usage="Génération de quiz d'évaluation post-formation",
        prompt="Crée un quiz de 10 questions à choix multiples pour évaluer les acquis d'une formation sur la cybersécurité de base destinée aux employés non-techniques.",
        sortie_attendue="10 questions QCM avec 4 options chacune, une réponse correcte indiquée, difficulté progressive.",
        critere_succes="Questions non ambiguës, adaptées à un public non-technique, couvre les fondamentaux."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Gestionnaire Paie & Administration du Personnel",
        nom_cas_usage="Réponse à question sur bulletin de paie (RAG)",
        prompt="Un employé demande : 'Pourquoi mon salaire net de ce mois est différent du mois dernier ?' Réponds en te basant uniquement sur le règlement de paie fourni en contexte.",
        sortie_attendue="Explication claire des éléments variables possibles (primes, absences, cotisations), basée sur le document source.",
        critere_succes="Réponse fidèle au document, ton rassurant, invite à contacter le service RH si besoin de détail personnalisé."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Responsable Relations Sociales",
        nom_cas_usage="Synthèse de compte-rendu de réunion CSE",
        prompt="Voici la transcription d'une réunion du Comité Social et Économique : [texte transcript]. Rédige une synthèse à destination des employés, sans jargon juridique.",
        sortie_attendue="Synthèse en langage clair, points principaux abordés, décisions prises, prochaines étapes.",
        critere_succes="Fidélité au contenu de la réunion, accessibilité pour un public non-initié, ton neutre."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Chargé de Communication Interne",
        nom_cas_usage="Rédaction de newsletter interne mensuelle",
        prompt="Rédige l'édito d'une newsletter interne mensuelle mettant en avant les succès du trimestre et les événements à venir, ton positif et fédérateur.",
        sortie_attendue="Édito de 200-300 mots, ton chaleureux, structure engageante, mention des événements à venir.",
        critere_succes="Ton fédérateur sans être artificiel, longueur respectée, informations cohérentes avec le contexte fourni."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Chargé de Communication Interne",
        nom_cas_usage="Rédaction de FAQ sur le télétravail",
        prompt="Génère une FAQ de 8 questions/réponses sur la politique de télétravail de l'entreprise, en te basant sur le règlement interne fourni en contexte.",
        sortie_attendue="8 paires question/réponse claires, basées sur le document source, format facile à scanner.",
        critere_succes="Fidélité au règlement fourni, pas d'invention de règles non mentionnées, format FAQ lisible."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Responsable Marque Employeur",
        nom_cas_usage="Rédaction de témoignage collaborateur (ghostwriting)",
        prompt="Voici les notes brutes d'un entretien avec un employé sur son parcours dans l'entreprise : [notes]. Rédige un témoignage à la première personne pour la page carrières.",
        sortie_attendue="Témoignage de 150-200 mots à la première personne, ton authentique, structure narrative claire.",
        critere_succes="Fidélité aux notes fournies, ton authentique et non promotionnel excessif, cohérence narrative."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Chargé de Recrutement",
        nom_cas_usage="Extraction de compétences depuis une offre concurrente",
        prompt="Voici une offre d'emploi d'un concurrent pour un poste similaire : [texte offre]. Extrais les compétences et avantages mis en avant pour comparer avec notre offre.",
        sortie_attendue="Liste structurée des compétences requises et avantages proposés par le concurrent.",
        critere_succes="Extraction fidèle au texte source, pas d'invention d'éléments non mentionnés."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Chargé de Communication Interne",
        nom_cas_usage="Traduction de communiqué interne multilingue",
        prompt="Traduis ce communiqué interne du français vers l'anglais en conservant le ton professionnel et empathique de l'original : [texte communiqué].",
        sortie_attendue="Traduction fidèle en anglais professionnel, ton et intention préservés.",
        critere_succes="Fidélité sémantique au texte source, ton adapté au contexte professionnel anglophone."
    ),
    Scenario(
        departement="RH & Communication",
        metier="Gestionnaire Onboarding",
        nom_cas_usage="Génération de parcours d'intégration nouvel arrivant",
        prompt="Crée un programme d'intégration sur 2 semaines pour un nouveau développeur backend, incluant présentation équipe, outils, et premiers objectifs.",
        sortie_attendue="Planning jour par jour sur 10 jours ouvrés avec activités, contacts clés et objectifs progressifs.",
        critere_succes="Planning réaliste et progressif, couvre les aspects techniques et humains de l'intégration."
    ),

    # =========================================================
    # Marketing & Digital — 2 existants, +14 pour atteindre 16
    # =========================================================
    Scenario(
        departement="Marketing & Digital",
        metier="Responsable de Campagnes Digitales",
        nom_cas_usage="Génération de titres publicitaires A/B testing",
        prompt="Génère 6 variantes de titre publicitaire (max 60 caractères) pour une campagne Google Ads promouvant un forfait internet fibre, à tester en A/B.",
        sortie_attendue="6 titres distincts, chacun sous 60 caractères, angles d'accroche variés (prix, vitesse, fiabilité).",
        critere_succes="Respect strict de la limite de caractères, diversité réelle des angles, pas de répétition de formulation."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Responsable de Campagnes Digitales",
        nom_cas_usage="Rédaction de description produit e-commerce",
        prompt="Rédige une fiche produit pour un smartphone milieu de gamme, orientée bénéfices utilisateur plutôt que caractéristiques techniques brutes, 150 mots.",
        sortie_attendue="Description structurée avec accroche, 3 bénéfices clés, ton persuasif mais factuel.",
        critere_succes="Longueur respectée (~150 mots), orientation bénéfices (pas juste specs), pas d'exagération non fondée."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Community Manager",
        nom_cas_usage="Génération de posts réseaux sociaux multi-formats",
        prompt="Crée 3 posts pour Instagram, LinkedIn et Twitter/X annonçant le lancement d'une nouvelle offre 5G, adaptés au ton de chaque plateforme.",
        sortie_attendue="3 posts distincts, chacun adapté au format et au ton propre à sa plateforme (visuel/pro/concis).",
        critere_succes="Différenciation réelle de ton entre plateformes, respect des contraintes de longueur par réseau."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Community Manager",
        nom_cas_usage="Réponse à commentaire négatif sur réseaux sociaux",
        prompt="Un client se plaint publiquement sur Facebook d'une facturation erronée. Rédige une réponse publique professionnelle qui désamorce la situation et invite à un échange privé.",
        sortie_attendue="Réponse courte (50-80 mots), ton empathique et professionnel, invite à poursuivre en message privé.",
        critere_succes="Absence de ton défensif, désamorçage effectif, redirection vers canal privé."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Concepteur-Rédacteur / Brand Content Manager",
        nom_cas_usage="Rédaction de script vidéo publicitaire courte",
        prompt="Écris le script d'une publicité vidéo de 30 secondes pour promouvoir une application mobile bancaire, avec voix-off et indications visuelles.",
        sortie_attendue="Script structuré avec timing, texte de voix-off, et description des visuels par séquence.",
        critere_succes="Respect de la contrainte de 30 secondes, structure claire narration/visuel, message principal identifiable."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Concepteur-Rédacteur / Brand Content Manager",
        nom_cas_usage="Rédaction de newsletter client mensuelle",
        prompt="Rédige une newsletter client mettant en avant 3 nouveautés produit du mois, avec un ton engageant et des call-to-action clairs pour chaque section.",
        sortie_attendue="Newsletter structurée en 3 sections, chacune avec accroche, description et CTA.",
        critere_succes="Structure claire et scannable, CTA présents et pertinents pour chaque section."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Analyste SEO / Growth",
        nom_cas_usage="Génération de méta-descriptions optimisées SEO",
        prompt="Génère 5 méta-descriptions (max 155 caractères) pour des pages produits différents (forfaits mobiles), optimisées pour le clic et le SEO.",
        sortie_attendue="5 méta-descriptions distinctes, chacune sous 155 caractères, incluant un mot-clé pertinent et un CTA implicite.",
        critere_succes="Respect strict de la limite de caractères, présence de mots-clés naturels, incitation au clic."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Analyste SEO / Growth",
        nom_cas_usage="Analyse de mots-clés depuis un brief client",
        prompt="Voici un brief client décrivant son activité : [texte brief]. Propose une liste de 10 mots-clés SEO pertinents classés par intention de recherche.",
        sortie_attendue="10 mots-clés classés par catégorie (informationnel, transactionnel, navigationnel).",
        critere_succes="Pertinence par rapport au brief fourni, classification cohérente, pas de mots-clés hors sujet."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Chargé d'Études Marché",
        nom_cas_usage="Synthèse d'étude de satisfaction client",
        prompt="Voici les résultats bruts d'une enquête de satisfaction client (200 répondants) : [données]. Rédige une synthèse exécutive de 300 mots avec les points saillants.",
        sortie_attendue="Synthèse structurée avec chiffres clés, tendances principales, recommandations.",
        critere_succes="Fidélité aux données fournies, pas de chiffres inventés, synthèse actionnable."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Chargé d'Études Marché",
        nom_cas_usage="Identification de personas marketing",
        prompt="À partir de cette description de clientèle cible : [texte description], construis 2 personas marketing détaillés avec besoins et freins à l'achat.",
        sortie_attendue="2 personas avec nom fictif, profil démographique, besoins, freins, canaux de communication préférés.",
        critere_succes="Cohérence avec la description fournie, personas différenciés et réalistes."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Responsable de Campagnes Digitales",
        nom_cas_usage="Rédaction d'email de relance panier abandonné",
        prompt="Rédige une séquence de 2 emails (J+1 et J+3) pour relancer un client ayant abandonné son panier avec un forfait internet non finalisé.",
        sortie_attendue="2 emails distincts avec objet, corps court, incitation différenciée (rappel vs offre limitée).",
        critere_succes="Progression logique entre les 2 emails, ton non insistant, CTA clair dans chaque email."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Concepteur-Rédacteur / Brand Content Manager",
        nom_cas_usage="Rédaction de slogan de campagne",
        prompt="Propose 5 slogans courts (max 8 mots) pour une campagne de rentrée mettant en avant la fiabilité du réseau mobile.",
        sortie_attendue="5 slogans distincts, chacun sous 8 mots, mémorables et alignés avec le thème fiabilité.",
        critere_succes="Respect de la contrainte de longueur, diversité des angles, absence de clichés excessifs."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Community Manager",
        nom_cas_usage="Modération et catégorisation de commentaires clients",
        prompt="Voici 10 commentaires clients reçus sur les réseaux sociaux : [textes]. Classe-les par catégorie (question, plainte, compliment, spam) et priorité de réponse.",
        sortie_attendue="Tableau des 10 commentaires avec catégorie et niveau de priorité assignés.",
        critere_succes="Classification cohérente avec le contenu réel des commentaires, priorisation logique."
    ),
    Scenario(
        departement="Marketing & Digital",
        metier="Analyste SEO / Growth",
        nom_cas_usage="Chatbot FAQ produit marketing (RAG)",
        prompt="Un visiteur du site demande : 'Quelle est la différence entre le forfait Essentiel et le forfait Premium ?' Réponds en te basant uniquement sur la documentation produit fournie en contexte.",
        sortie_attendue="Réponse comparative claire basée sur le document source, format facile à lire.",
        critere_succes="Fidélité au document fourni, pas d'invention de caractéristiques, réponse structurée."
    ),

    # =========================================================
    # IT & Architecture — 3 existants, +13 pour atteindre 16
    # =========================================================
    Scenario(
        departement="IT & Architecture",
        metier="Développeur Logiciel / Ingénieur d'Études",
        nom_cas_usage="Revue de code et suggestions d'amélioration",
        prompt="Voici un extrait de code Python : [extrait de code]. Identifie les problèmes potentiels (performance, lisibilité, sécurité) et propose des améliorations concrètes.",
        sortie_attendue="Liste des problèmes identifiés avec explication, suggestions de correction avec exemples de code.",
        critere_succes="Problèmes réels identifiés (pas inventés), suggestions applicables et justifiées."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Développeur Logiciel / Ingénieur d'Études",
        nom_cas_usage="Génération de tests unitaires pour code existant",
        prompt="Voici une fonction Python de validation de numéro de téléphone : [code]. Génère une suite de tests unitaires couvrant les cas limites.",
        sortie_attendue="Suite de tests avec au moins 5 cas (valide, invalide, vide, format international, caractères spéciaux).",
        critere_succes="Tests exécutables, couverture des cas limites principaux, syntaxe pytest correcte."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Architecte Solutions",
        nom_cas_usage="Proposition d'architecture microservices",
        prompt="Voici les besoins fonctionnels d'une plateforme de facturation : [besoins]. Propose une architecture microservices avec les services principaux et leurs interactions.",
        sortie_attendue="Schéma textuel des services proposés, responsabilités de chacun, mode de communication entre eux.",
        critere_succes="Architecture cohérente avec les besoins fournis, séparation des responsabilités logique."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Architecte Solutions",
        nom_cas_usage="Comparaison de technologies (RAG)",
        prompt="Quelles sont les différences principales entre PostgreSQL et MongoDB pour un cas d'usage de facturation ? Réponds en te basant sur la documentation technique fournie en contexte.",
        sortie_attendue="Comparaison structurée sur les critères pertinents (cohérence, scalabilité, requêtes complexes).",
        critere_succes="Fidélité au contexte fourni, comparaison équilibrée, recommandation justifiée pour le cas d'usage."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="DevOps / SRE",
        nom_cas_usage="Rédaction de script de déploiement CI/CD",
        prompt="Rédige un fichier de configuration GitHub Actions pour déployer automatiquement une application Python sur un serveur après chaque merge sur main.",
        sortie_attendue="Fichier YAML fonctionnel avec étapes de build, test, et déploiement.",
        critere_succes="Syntaxe YAML valide, étapes logiques (test avant déploiement), déclencheur correct."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="DevOps / SRE",
        nom_cas_usage="Diagnostic d'incident depuis logs serveur",
        prompt="Voici un extrait de logs d'erreur serveur : [logs]. Identifie la cause probable de l'incident et propose des étapes de résolution.",
        sortie_attendue="Diagnostic argumenté à partir des logs, étapes de résolution priorisées.",
        critere_succes="Diagnostic cohérent avec les logs fournis, pas d'hypothèses non fondées sur le contenu."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Ingénieur QA / Test",
        nom_cas_usage="Génération de cas de test fonctionnels",
        prompt="Voici la spécification d'une fonctionnalité de réinitialisation de mot de passe : [spec]. Génère 8 cas de test fonctionnels couvrant les scénarios nominaux et d'erreur.",
        sortie_attendue="8 cas de test avec préconditions, étapes, résultat attendu.",
        critere_succes="Couverture des cas nominaux et d'erreur, cas de test réalistes et exécutables manuellement."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Ingénieur QA / Test",
        nom_cas_usage="Rédaction de rapport de bug structuré",
        prompt="Voici une description informelle d'un bug rapporté par un testeur : [texte informel]. Reformule-la en rapport de bug structuré (titre, étapes, résultat attendu/obtenu, sévérité).",
        sortie_attendue="Rapport structuré avec tous les champs standards d'un ticket de bug.",
        critere_succes="Fidélité à la description originale, structure complète et exploitable par un développeur."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Data Engineer",
        nom_cas_usage="Génération de requête SQL complexe",
        prompt="Écris une requête SQL qui calcule le chiffre d'affaires mensuel par région pour les 12 derniers mois, à partir des tables commandes et clients dont le schéma est fourni en contexte.",
        sortie_attendue="Requête SQL fonctionnelle avec jointures et agrégations correctes.",
        critere_succes="Requête syntaxiquement correcte, logique d'agrégation juste, cohérente avec le schéma fourni."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Data Engineer",
        nom_cas_usage="Explication de pipeline ETL existant",
        prompt="Voici le code d'un pipeline ETL Python : [code]. Explique en langage simple ce que fait ce pipeline, étape par étape, pour un public non-technique.",
        sortie_attendue="Explication vulgarisée en 5-6 points, sans jargon technique excessif.",
        critere_succes="Fidélité au code fourni, accessibilité pour un public non-technique."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Développeur Logiciel / Ingénieur d'Études",
        nom_cas_usage="Refactoring de code pour lisibilité",
        prompt="Voici une fonction Python difficile à lire avec des noms de variables peu clairs : [code]. Refactorise-la pour améliorer la lisibilité sans changer le comportement.",
        sortie_attendue="Code refactorisé avec noms explicites, structure clarifiée, comportement identique.",
        critere_succes="Comportement fonctionnel préservé, lisibilité objectivement améliorée."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Ingénieur Sécurité / DevSecOps",
        nom_cas_usage="Identification de vulnérabilités dans un extrait de code",
        prompt="Voici un extrait de code gérant l'authentification utilisateur : [code]. Identifie les failles de sécurité potentielles (sans exploiter, juste analyser).",
        sortie_attendue="Liste des failles identifiées (ex: injection SQL, mot de passe en clair) avec explication du risque.",
        critere_succes="Identification de failles réelles présentes dans le code fourni, pas de généralités hors contexte."
    ),
    Scenario(
        departement="IT & Architecture",
        metier="Chef de Projet Technique",
        nom_cas_usage="Rédaction de spécification technique fonctionnelle",
        prompt="Voici un besoin métier exprimé de façon informelle : [besoin informel]. Rédige une spécification technique structurée (contexte, objectifs, contraintes, critères d'acceptation).",
        sortie_attendue="Spécification structurée avec sections standards, critères d'acceptation mesurables.",
        critere_succes="Fidélité au besoin exprimé, structure professionnelle, critères d'acceptation testables."
    ),

    # =========================================================
    # Réseau / Support Technique (NOC) — 1 existant, +15 pour atteindre 16
    # =========================================================
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Technicien Support Clientèle Entreprises (B2B)",
        nom_cas_usage="Rédaction de rapport d'incident post-mortem",
        prompt="Voici les logs et la chronologie d'un incident réseau ayant duré 3h : [données]. Rédige un rapport post-mortem structuré (cause, impact, actions correctives).",
        sortie_attendue="Rapport avec sections cause racine, impact client, chronologie, actions correctives futures.",
        critere_succes="Fidélité à la chronologie fournie, actions correctives réalistes et pertinentes."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Technicien Support Clientèle Entreprises (B2B)",
        nom_cas_usage="Chatbot diagnostic premier niveau (RAG)",
        prompt="Un client signale : 'Ma connexion internet coupe toutes les 10 minutes.' Propose un diagnostic de premier niveau en te basant sur le guide de dépannage fourni en contexte.",
        sortie_attendue="Liste d'étapes de diagnostic ordonnées, basées sur le guide source, langage accessible.",
        critere_succes="Fidélité au guide fourni, étapes dans un ordre logique, pas d'étapes inventées."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Ingénieur Réseau",
        nom_cas_usage="Explication vulgarisée de panne technique",
        prompt="Voici une description technique d'une panne de routage BGP : [texte technique]. Reformule-la en langage simple pour un client B2B non-technique.",
        sortie_attendue="Explication vulgarisée en 3-4 phrases, sans jargon réseau, rassurante et factuelle.",
        critere_succes="Fidélité technique au texte source, accessibilité réelle pour un non-technicien."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Ingénieur Réseau",
        nom_cas_usage="Priorisation de tickets d'incidents multiples",
        prompt="Voici 5 tickets d'incidents réseau ouverts simultanément avec leur impact décrit : [tickets]. Classe-les par ordre de priorité de traitement avec justification.",
        sortie_attendue="Classement des 5 tickets avec justification basée sur l'impact et la criticité décrits.",
        critere_succes="Priorisation cohérente avec les impacts décrits, justification claire pour chaque ticket."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Technicien Support Clientèle Entreprises (B2B)",
        nom_cas_usage="Rédaction de communication client pendant incident majeur",
        prompt="Un incident majeur affecte plusieurs clients B2B depuis 1h. Rédige un message de communication proactive à leur envoyer, sans détails techniques excessifs.",
        sortie_attendue="Message court et rassurant, mention de l'incident, actions en cours, estimation si disponible.",
        critere_succes="Ton rassurant et transparent, absence de jargon technique, pas de fausse promesse de délai."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Superviseur NOC",
        nom_cas_usage="Synthèse quotidienne d'activité NOC",
        prompt="Voici la liste des incidents traités durant la journée : [liste incidents]. Rédige une synthèse quotidienne pour la direction technique.",
        sortie_attendue="Synthèse avec nombre d'incidents, criticité moyenne, incidents notables, tendances.",
        critere_succes="Fidélité aux données fournies, synthèse concise et actionnable pour la direction."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Ingénieur Réseau",
        nom_cas_usage="Analyse de tendance de tickets récurrents",
        prompt="Voici l'historique des 20 derniers tickets d'un même client sur 3 mois : [historique]. Identifie les patterns récurrents et propose une action préventive.",
        sortie_attendue="Identification des causes récurrentes et recommandation d'action préventive argumentée.",
        critere_succes="Patterns identifiés réellement présents dans l'historique fourni, recommandation pertinente."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Technicien Support Clientèle Entreprises (B2B)",
        nom_cas_usage="Rédaction de procédure de dépannage standardisée",
        prompt="À partir de ces notes informelles de résolution d'un problème de latence réseau : [notes], rédige une procédure standardisée réutilisable par l'équipe support.",
        sortie_attendue="Procédure structurée en étapes numérotées, réutilisable, langage clair pour un technicien.",
        critere_succes="Fidélité aux notes fournies, procédure claire et réutilisable, étapes dans un ordre logique."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Ingénieur Réseau",
        nom_cas_usage="Chatbot FAQ technique interne (RAG)",
        prompt="Un technicien junior demande : 'Quelle est la procédure d'escalade pour un incident de niveau critique ?' Réponds en te basant sur la documentation interne fournie en contexte.",
        sortie_attendue="Réponse claire basée sur la documentation source, étapes d'escalade dans l'ordre.",
        critere_succes="Fidélité au document source, pas d'invention de procédure non documentée."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Superviseur NOC",
        nom_cas_usage="Rédaction de plan de communication de maintenance planifiée",
        prompt="Une maintenance planifiée impactera le réseau de 2h à 4h du matin. Rédige le message d'annonce préventive à envoyer aux clients 48h à l'avance.",
        sortie_attendue="Message clair mentionnant date, heure, durée estimée et impact attendu.",
        critere_succes="Informations complètes et exactes selon le contexte fourni, ton professionnel et informatif."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Technicien Support Clientèle Entreprises (B2B)",
        nom_cas_usage="Analyse de sentiment sur ticket client mécontent",
        prompt="Voici le texte d'un ticket client visiblement frustré par une panne récurrente : [texte ticket]. Évalue le niveau d'urgence émotionnelle et propose une réponse adaptée.",
        sortie_attendue="Évaluation du niveau d'urgence avec justification, réponse empathique et orientée solution.",
        critere_succes="Évaluation cohérente avec le ton du ticket, réponse empathique sans être artificielle."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Ingénieur Réseau",
        nom_cas_usage="Traduction technique pour équipe internationale",
        prompt="Traduis cette procédure de dépannage réseau du français vers l'anglais technique, en conservant la précision des termes techniques : [texte procédure].",
        sortie_attendue="Traduction fidèle en anglais technique, terminologie réseau correcte.",
        critere_succes="Précision technique préservée, terminologie anglaise appropriée au domaine réseau."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Superviseur NOC",
        nom_cas_usage="Estimation d'impact d'incident sur SLA",
        prompt="Un incident a duré 45 minutes sur un client ayant un SLA de disponibilité de 99.9%. Calcule l'impact sur le SLA mensuel et propose une communication adaptée.",
        sortie_attendue="Calcul d'impact sur le SLA avec explication, recommandation de communication au client.",
        critere_succes="Calcul cohérent avec les données fournies, recommandation adaptée à la sévérité de l'impact."
    ),
    Scenario(
        departement="Réseau / Support Technique (NOC)",
        metier="Technicien Support Clientèle Entreprises (B2B)",
        nom_cas_usage="Checklist de vérification avant clôture de ticket",
        prompt="Génère une checklist de vérification à suivre par un technicien avant de clôturer un ticket d'incident réseau résolu.",
        sortie_attendue="Checklist de 6-8 points couvrant vérification technique, confirmation client, documentation.",
        critere_succes="Checklist complète et pratique, couvre les aspects techniques et administratifs de clôture."
    ),

    # =========================================================
    # Productivité Personnelle — 3 existants, +13 pour atteindre 16
    # =========================================================
    Scenario(
        departement="Productivité Personnelle",
        metier="Chef de Projet / Manager",
        nom_cas_usage="Rédaction d'ordre du jour de réunion",
        prompt="Prépare un ordre du jour structuré pour une réunion de lancement de projet de 1h, avec 4 participants et 3 sujets à traiter.",
        sortie_attendue="Ordre du jour avec horaires indicatifs par sujet, objectifs de chaque point, participants concernés.",
        critere_succes="Répartition du temps réaliste sur 1h, structure claire et actionnable."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Chef de Projet / Manager",
        nom_cas_usage="Découpage de projet en tâches (breakdown)",
        prompt="Voici la description d'un projet de refonte de site web : [description]. Découpe-le en une liste de tâches avec estimation de durée pour chacune.",
        sortie_attendue="Liste de 8-10 tâches avec estimation de durée réaliste et dépendances si pertinentes.",
        critere_succes="Découpage cohérent avec la description fournie, estimations réalistes."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Assistant(e) de Direction",
        nom_cas_usage="Planification d'agenda avec contraintes multiples",
        prompt="Voici les disponibilités de 4 personnes sur une semaine : [disponibilités]. Propose 3 créneaux possibles pour une réunion d'1h regroupant tout le monde.",
        sortie_attendue="3 créneaux proposés compatibles avec toutes les disponibilités fournies.",
        critere_succes="Créneaux réellement compatibles avec les contraintes fournies, pas d'erreur de calcul."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Assistant(e) de Direction",
        nom_cas_usage="Rédaction de compte-rendu de voyage professionnel",
        prompt="Voici les notes brutes prises pendant un déplacement professionnel : [notes]. Rédige une note de synthèse pour la direction incluant les points clés et frais engagés.",
        sortie_attendue="Note structurée avec objectif du déplacement, points clés retenus, résumé des frais.",
        critere_succes="Fidélité aux notes fournies, structure claire et professionnelle."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Consultant Interne / Analyste de Direction",
        nom_cas_usage="Synthèse de documents multiples en un rapport",
        prompt="Voici 3 rapports courts sur des sujets liés à la stratégie digitale : [textes]. Fusionne-les en une synthèse unique de 400 mots sans redondance.",
        sortie_attendue="Synthèse unifiée de 400 mots, sans répétition entre les sources, structure logique.",
        critere_succes="Fidélité aux 3 sources, absence de redondance, longueur respectée."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Consultant Interne / Analyste de Direction",
        nom_cas_usage="Préparation de slides pour présentation exécutive",
        prompt="À partir de ces données de performance trimestrielle : [données], propose un plan de présentation en 5 slides avec titre et contenu clé de chaque slide.",
        sortie_attendue="5 slides avec titre et 3-4 points clés par slide, structure narrative logique.",
        critere_succes="Cohérence avec les données fournies, structure narrative claire (contexte → résultats → recommandations)."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Chef de Projet / Manager",
        nom_cas_usage="Identification de risques projet",
        prompt="Voici la description d'un projet de migration système : [description]. Identifie les 5 risques principaux et propose une mesure de mitigation pour chacun.",
        sortie_attendue="5 risques identifiés avec probabilité/impact estimés et mesure de mitigation associée.",
        critere_succes="Risques pertinents par rapport au projet décrit, mitigations réalistes et actionnables."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Assistant(e) de Direction",
        nom_cas_usage="Rédaction de réponse d'absence automatique",
        prompt="Rédige un message d'absence automatique professionnel pour un cadre en congés 2 semaines, avec contact de remplacement.",
        sortie_attendue="Message court et professionnel, dates de retour, contact alternatif mentionné.",
        critere_succes="Ton professionnel, informations essentielles présentes (dates, contact de remplacement)."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Consultant Interne / Analyste de Direction",
        nom_cas_usage="Chatbot support outils internes (RAG)",
        prompt="Un employé demande : 'Comment demander un accès à l'outil de gestion de projet ?' Réponds en te basant sur le guide utilisateur interne fourni en contexte.",
        sortie_attendue="Réponse étape par étape basée sur le guide source, langage clair et actionnable.",
        critere_succes="Fidélité au guide fourni, pas d'étapes inventées, réponse orientée self-service."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Chef de Projet / Manager",
        nom_cas_usage="Rédaction de message de recadrage bienveillant",
        prompt="Un membre de l'équipe a manqué plusieurs délais récemment. Rédige un message pour aborder le sujet lors d'un entretien individuel, ton constructif et non accusateur.",
        sortie_attendue="Message structuré avec observation factuelle, question ouverte, proposition d'accompagnement.",
        critere_succes="Ton constructif et non accusateur, orienté solution plutôt que reproche."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Assistant(e) de Direction",
        nom_cas_usage="Extraction d'actions depuis un long email",
        prompt="Voici un email long et peu structuré contenant plusieurs demandes : [texte email]. Extrais la liste des actions à réaliser avec leur priorité apparente.",
        sortie_attendue="Liste des actions extraites avec niveau de priorité, fidèle au contenu de l'email.",
        critere_succes="Extraction fidèle au texte source, aucune action inventée, priorisation cohérente."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Consultant Interne / Analyste de Direction",
        nom_cas_usage="Rédaction de note de recommandation stratégique",
        prompt="Voici une analyse de marché synthétique : [analyse]. Rédige une note de recommandation de 200 mots à destination du comité de direction.",
        sortie_attendue="Note structurée avec contexte bref, recommandation claire, justification synthétique.",
        critere_succes="Cohérence avec l'analyse fournie, recommandation claire et actionnable, longueur respectée."
    ),
    Scenario(
        departement="Productivité Personnelle",
        metier="Chef de Projet / Manager",
        nom_cas_usage="Rédaction de rétrospective de sprint (agile)",
        prompt="Voici les notes brutes d'une rétrospective d'équipe agile : [notes]. Rédige un compte-rendu structuré avec points positifs, points d'amélioration et actions décidées.",
        sortie_attendue="Compte-rendu structuré en 3 sections (positif/amélioration/actions), fidèle aux notes fournies.",
        critere_succes="Fidélité aux notes, structure claire en 3 sections, actions concrètes et assignables."
    ),

    # =========================================================
    # Agents IA et Automatisation — 0 existant, +16 pour atteindre 16
    # =========================================================
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Chatbot service client (RAG)",
        prompt="Un client demande : 'Comment activer mon forfait 4G+ depuis l'application My Ooredoo ?' Réponds en te basant sur la FAQ fournie en contexte.",
        sortie_attendue="Réponse étape par étape basée sur la FAQ, ton clair et orienté self-service.",
        critere_succes="Réponse fidèle à la FAQ source, pas d'étapes inventées non présentes dans le document."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Analyse de sentiment sur appel client",
        prompt="Voici la transcription d'un appel client : [texte transcript]. Détermine le sentiment global (positif/neutre/négatif) et identifie le principal point d'irritation mentionné, s'il y en a un.",
        sortie_attendue="Sentiment classé + point d'irritation identifié avec citation courte du transcript à l'appui.",
        critere_succes="Classification cohérente avec le ton du transcript, point d'irritation réellement présent dans le texte."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Génération de résumé d'appel pour CRM",
        prompt="Voici la transcription complète d'un appel client de 5 minutes : [transcript]. Rédige un résumé de 3-4 phrases à insérer dans la fiche CRM du client.",
        sortie_attendue="Résumé concis couvrant motif d'appel, résolution apportée, suivi éventuel nécessaire.",
        critere_succes="Fidélité au transcript, concision (3-4 phrases), informations exploitables pour un futur agent."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Responsable Automatisation des Processus",
        nom_cas_usage="Détection d'intention pour routage automatique",
        prompt="Voici un message client entrant : 'Je veux résilier mon abonnement.' Détermine l'intention principale et le service à router (résiliation, facturation, support technique, etc.).",
        sortie_attendue="Intention identifiée avec niveau de confiance qualitatif, service de routage recommandé.",
        critere_succes="Classification correcte de l'intention, routage cohérent avec le message fourni."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Responsable Automatisation des Processus",
        nom_cas_usage="Génération de réponse automatique email entrant",
        prompt="Voici un email client demandant le statut de sa demande de portabilité : [texte email]. Génère une réponse automatique basée sur le statut fourni en contexte.",
        sortie_attendue="Réponse email personnalisée basée sur le statut réel, ton professionnel et rassurant.",
        critere_succes="Fidélité au statut fourni en contexte, pas d'invention d'information sur l'avancement."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Chatbot de qualification de demande avant transfert humain",
        prompt="Un client écrit : 'J'ai un problème avec ma facture.' Pose 2-3 questions de qualification pertinentes avant un transfert vers un conseiller humain.",
        sortie_attendue="2-3 questions ciblées permettant de mieux qualifier le problème avant transfert.",
        critere_succes="Questions pertinentes et non redondantes, orientées vers une qualification utile."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Responsable Automatisation des Processus",
        nom_cas_usage="Extraction de données structurées depuis document scanné",
        prompt="Voici le texte extrait d'une facture scannée : [texte OCR]. Extrais les champs structurés : numéro de facture, date, montant total, nom du client.",
        sortie_attendue="Champs extraits sous forme structurée (JSON ou tableau), fidèles au texte source.",
        critere_succes="Extraction fidèle au texte fourni, pas de champ inventé si absent du document."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Génération de script d'appel sortant personnalisé",
        prompt="Prépare un script d'appel sortant pour un conseiller devant recontacter un client suite à une réclamation résolue, avec un ton empathique et professionnel.",
        sortie_attendue="Script avec accroche, rappel du contexte, vérification de satisfaction, clôture.",
        critere_succes="Structure logique d'appel, ton empathique cohérent, pas trop long à l'oral."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Responsable Automatisation des Processus",
        nom_cas_usage="Résumé automatique de longs tickets support",
        prompt="Voici un ticket de support de 500 mots avec plusieurs échanges : [texte ticket]. Génère un résumé de 3 phrases pour un agent qui reprend le dossier.",
        sortie_attendue="Résumé de 3 phrases couvrant le problème initial, les actions déjà entreprises, l'état actuel.",
        critere_succes="Fidélité au ticket, concision réelle (3 phrases), informations essentielles présentes."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Chatbot multilingue support de premier niveau",
        prompt="Un client écrit en anglais : 'How can I check my remaining data balance?' Réponds dans la même langue, en te basant sur la FAQ fournie en contexte (rédigée en français).",
        sortie_attendue="Réponse en anglais fidèle à la FAQ française fournie, traduite avec justesse.",
        critere_succes="Réponse dans la langue de la question, fidélité au contenu source malgré le changement de langue."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Responsable Automatisation des Processus",
        nom_cas_usage="Détection d'anomalie dans un flux de tickets",
        prompt="Voici le nombre de tickets support reçus par heure sur une journée : [données horaires]. Identifie s'il y a un pic anormal et à quelle heure.",
        sortie_attendue="Identification du ou des pics anormaux avec l'heure concernée, basé uniquement sur les données fournies.",
        critere_succes="Analyse fidèle aux données fournies, pas de pic signalé s'il n'y en a pas réellement un."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Proposition d'offre personnalisée basée sur profil client",
        prompt="Voici le profil d'usage d'un client (consommation data, historique d'appels) : [profil]. Propose l'offre la plus adaptée parmi le catalogue fourni en contexte.",
        sortie_attendue="Recommandation d'offre avec justification basée sur le profil et le catalogue fournis.",
        critere_succes="Recommandation cohérente avec le profil et le catalogue réels, justification claire."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Responsable Automatisation des Processus",
        nom_cas_usage="Classification automatique de tickets par urgence",
        prompt="Voici 5 tickets support avec leur texte brut : [tickets]. Classe chacun par niveau d'urgence (faible/moyen/élevé/critique) avec justification courte.",
        sortie_attendue="5 tickets classés avec justification d'une phrase pour chaque niveau attribué.",
        critere_succes="Classification cohérente avec le contenu réel de chaque ticket, justification pertinente."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Chatbot d'aide au self-troubleshooting",
        prompt="Un client écrit : 'Mon application ne se connecte plus depuis ce matin.' Guide-le à travers 3 étapes de dépannage simple avant d'envisager une escalade.",
        sortie_attendue="3 étapes de dépannage progressives et simples, formulées pour un utilisateur non-technique.",
        critere_succes="Étapes logiques et progressives, langage accessible, pas d'étape technique complexe en premier."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Responsable Automatisation des Processus",
        nom_cas_usage="Génération de rapport d'activité agent IA hebdomadaire",
        prompt="Voici les statistiques d'usage du chatbot sur une semaine (nombre de conversations, taux de résolution, sujets fréquents) : [données]. Rédige un rapport de synthèse pour le management.",
        sortie_attendue="Rapport structuré avec chiffres clés, tendances, recommandations d'amélioration.",
        critere_succes="Fidélité aux données fournies, synthèse claire et actionnable, pas de chiffre inventé."
    ),
    Scenario(
        departement="Agents IA et Automatisation",
        metier="Conseiller Service Client (Call Center)",
        nom_cas_usage="Transfert de contexte entre chatbot et agent humain",
        prompt="Voici l'historique de conversation entre un client et le chatbot avant transfert : [historique]. Rédige la note de contexte à transmettre à l'agent humain qui reprend la conversation.",
        sortie_attendue="Note de contexte concise résumant la demande, les tentatives déjà faites, et le point de blocage.",
        critere_succes="Fidélité à l'historique fourni, note exploitable immédiatement par l'agent humain."
    ),
]


def main(dry_run: bool = True) -> None:
    db = SessionLocal()
    try:
        existants = {
            (s.departement, s.nom_cas_usage)
            for s in db.query(Scenario.departement, Scenario.nom_cas_usage).all()
        }

        a_inserer = [
            s for s in NOUVEAUX_SCENARIOS
            if (s.departement, s.nom_cas_usage) not in existants
        ]
        deja_presents = len(NOUVEAUX_SCENARIOS) - len(a_inserer)

        print(f"Scénarios déjà en base (parmi la liste proposée) : {deja_presents}")
        print(f"Scénarios à insérer : {len(a_inserer)}")

        if dry_run:
            print("\n--- DRY RUN : aucun scénario inséré ---")
            for s in a_inserer:
                print(f"  [{s.departement}] {s.nom_cas_usage}")
            return

        db.add_all(a_inserer)
        db.commit()
        print(f"\n✅ {len(a_inserer)} scénarios insérés avec succès.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Insère réellement les scénarios")
    args = parser.parse_args()
    main(dry_run=not args.apply)