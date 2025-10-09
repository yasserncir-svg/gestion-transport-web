import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime, timedelta
import tempfile
from io import BytesIO
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class GestionTransportWeb:
    def __init__(self):
        self.df = None
        self.df_info = None
        self.df_chauffeurs = None
        self.dates_par_jour = {}
        self.liste_ramassage_actuelle = []
        self.liste_depart_actuelle = []
        
        # Initialiser l'état de session
        if 'chauffeurs_data' not in st.session_state:
            st.session_state.chauffeurs_data = pd.DataFrame(columns=[
                'Chauffeur', 'Heure', 'Agent', 'Adresse', 'Telephone', 'Societe', 'Vehicule', 'Type_Transport', 'Jour'
            ])
        
        self.df_chauffeurs = st.session_state.chauffeurs_data
        self.charger_infos_agents()
    
    def charger_infos_agents(self):
        """Charge le fichier info.xlsx avec les adresses et téléphones"""
        try:
            if os.path.exists("info.xlsx"):
                self.df_info = pd.read_excel("info.xlsx")
                st.sidebar.success("✅ Fichier info.xlsx chargé")
            else:
                self.df_info = pd.DataFrame()
                st.sidebar.warning("⚠️ Fichier info.xlsx non trouvé")
        except Exception as e:
            self.df_info = pd.DataFrame()
            st.sidebar.error(f"❌ Erreur chargement info.xlsx: {e}")
    
    def get_info_agent(self, nom_agent):
        """Récupère les informations d'un agent"""
        if self.df_info is None or self.df_info.empty:
            return {"adresse": "Adresse non renseignée", "tel": "Tél non renseigné", "societe": "Société non renseignée", "voiture": "Non"}
        
        try:
            nom_recherche = nom_agent.strip()
            
            for idx, row in self.df_info.iterrows():
                nom_info = str(row.iloc[0]).strip() if len(row) > 0 else ""
                
                if nom_recherche == nom_info:
                    a_voiture = "Non"
                    if len(row) > 4:
                        voiture_info = str(row.iloc[4]).strip().lower()
                        if voiture_info in ['oui', 'yes', 'true', '1', 'x']:
                            a_voiture = "Oui"
                    
                    return {
                        "adresse": str(row.iloc[1]) if len(row) > 1 else "Adresse non renseignée",
                        "tel": str(row.iloc[2]) if len(row) > 2 else "Tél non renseigné",
                        "societe": str(row.iloc[3]) if len(row) > 3 else "Société non renseignée",
                        "voiture": a_voiture
                    }
            
            return {"adresse": "Adresse non renseignée", "tel": "Tél non renseigné", "societe": "Société non renseignée", "voiture": "Non"}
            
        except Exception as e:
            return {"adresse": "Adresse non renseignée", "tel": "Tél non renseigné", "societe": "Société non renseignée", "voiture": "Non"}
    
    def get_liste_chauffeurs_voitures(self):
        """Récupère la liste des chauffeurs depuis info.xlsx"""
        if self.df_info is None or self.df_info.empty:
            return []
        
        try:
            chauffeurs_voitures = []
            
            for idx, row in self.df_info.iterrows():
                if len(row) > 6:
                    chauffeur = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ""
                    voiture = str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else ""
                    
                    if chauffeur and chauffeur != "nan" and chauffeur != "":
                        chauffeurs_voitures.append({
                            'chauffeur': chauffeur,
                            'voiture': voiture if voiture and voiture != "nan" else "Non renseigné"
                        })
            
            return chauffeurs_voitures
            
        except Exception as e:
            return []
    
    def extraire_dates_des_entetes(self, file):
        """Extrait les dates depuis la 2ème ligne du fichier Excel"""
        try:
            # Lire les 2 premières lignes pour les en-têtes
            df_entetes = pd.read_excel(file, nrows=2, header=None)
            dates_par_jour = {}
            
            st.write("🔍 Debug - Structure du fichier:")
            st.write("Ligne 0:", df_entetes.iloc[0].tolist())
            st.write("Ligne 1 (dates):", df_entetes.iloc[1].tolist())
            
            # Mapping des positions des colonnes vers les jours - CORRIGÉ
            positions_jours = {
                1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi', 
                5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'
            }
            
            # Parcourir les colonnes de jours - MAINTENANT ON PREND LA LIGNE 1 (2ème ligne)
            for col_index, jour_nom in positions_jours.items():
                if col_index < len(df_entetes.columns):
                    # Prendre la cellule de la DEUXIÈME ligne (ligne 1) qui contient les dates
                    cellule = df_entetes.iloc[1, col_index]
                    nom_colonne = str(cellule) if pd.notna(cellule) else ""
                    
                    st.write(f"Colonne {col_index} ({jour_nom}): '{nom_colonne}'")
                    
                    # Chercher un motif date (jj/mm ou jj/mm/aaaa)
                    match = re.search(r'(\d{1,2})[/-](\d{1,2})', nom_colonne)
                    if match:
                        jour = match.group(1)
                        mois = match.group(2)
                        
                        # Déterminer l'année
                        annee_courante = datetime.now().year
                        mois_actuel = datetime.now().month
                        
                        if int(mois) < mois_actuel:
                            annee_courante += 1
                        
                        date_trouvee = f"{jour.zfill(2)}/{mois.zfill(2)}/{annee_courante}"
                        dates_par_jour[jour_nom] = date_trouvee
                        st.success(f"✅ {jour_nom}: {date_trouvee}")
                    else:
                        # Date par défaut si non détectée
                        date_par_defaut = self.calculer_date_par_defaut(jour_nom)
                        dates_par_jour[jour_nom] = date_par_defaut
                        st.warning(f"⚠️ {jour_nom}: Date non détectée, utilisation: {date_par_defaut}")
            
            return dates_par_jour
            
        except Exception as e:
            st.error(f"Erreur extraction dates: {e}")
            return self.generer_dates_par_defaut()
    
    def calculer_date_par_defaut(self, jour_nom=None):
        aujourd_hui = datetime.now()
        jours_semaine = {
            'Lundi': 0, 'Mardi': 1, 'Mercredi': 2, 'Jeudi': 3, 
            'Vendredi': 4, 'Samedi': 5, 'Dimanche': 6
        }
        
        if jour_nom and jour_nom in jours_semaine:
            jour_cible = jours_semaine[jour_nom]
            jour_actuel = aujourd_hui.weekday()
            
            if jour_cible >= jour_actuel:
                decalage = jour_cible - jour_actuel
            else:
                decalage = 7 - (jour_actuel - jour_cible)
            
            date_calculee = aujourd_hui + timedelta(days=decalage)
        else:
            date_calculee = aujourd_hui
        
        return date_calculee.strftime("%d/%m/%Y")
    
    def generer_dates_par_defaut(self):
        aujourd_hui = datetime.now()
        dates_par_defaut = {}
        jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        jour_actuel = aujourd_hui.weekday()
        jours_vers_lundi = (0 - jour_actuel) % 7
        date_debut = aujourd_hui + timedelta(days=jours_vers_lundi)
        
        for i, jour in enumerate(jours_ordre):
            date_jour = date_debut + timedelta(days=i)
            dates_par_defaut[jour] = date_jour.strftime("%d/%m/%Y")
        
        return dates_par_defaut
    
    def get_date_du_jour(self, jour_nom):
        return self.dates_par_jour.get(jour_nom, self.calculer_date_par_defaut(jour_nom))
    
    def ajuster_heure_ete(self, heure, heure_ete_active):
        return heure - 1 if heure_ete_active else heure

    def extraire_heures(self, planning_str):
        """Extrait les heures de début et fin d'un planning - VERSION CORRIGÉE"""
        if pd.isna(planning_str) or planning_str in ['REPOS', 'ABSENCE', 'OFF', 'MALADIE', 'CONGÉ PAYÉ', 'CONGÉ MATERNITÉ']:
            return None, None
        
        texte = str(planning_str).strip()
        
        # Nettoyer le texte
        texte = re.sub(r'[^\dh\s\-à]', ' ', texte)
        texte = re.sub(r'\s+', ' ', texte)
        
        # Pattern pour formats: 7h-16h, 7h-16h, 14h-23h, etc.
        pattern_principal = r'(\d{1,2})h?\s*[\-à]\s*(\d{1,2})h?'
        match = re.search(pattern_principal, texte)
        
        if match:
            heure_debut = int(match.group(1))
            heure_fin = int(match.group(2))
            
            # Ajuster les heures de fin après minuit
            if heure_fin < heure_debut and heure_fin < 12:
                heure_fin += 24
            
            return heure_debut, heure_fin
        
        return None, None
    
    def traiter_donnees(self, heure_ete_active, jour_selectionne, heures_ramassage_selectionnees, heures_depart_selectionnees):
        """Traite les données du fichier Excel - VERSION CORRIGÉE"""
        if self.df is None:
            return
        
        self.liste_ramassage_actuelle = []
        self.liste_depart_actuelle = []
        
        jours_mapping = {
            'Lundi': 'Lundi', 'Mardi': 'Mardi', 'Mercredi': 'Mercredi', 
            'Jeudi': 'Jeudi', 'Vendredi': 'Vendredi', 'Samedi': 'Samedi', 'Dimanche': 'Dimanche'
        }
        
        for _, agent in self.df.iterrows():
            nom_agent = agent['Salarie']
            info_agent = self.get_info_agent(nom_agent)
            
            # DEBUG: Vérifier les agents exclus
            if info_agent['voiture'] == "Oui":
                continue
            
            jours_a_verifier = []
            if jour_selectionne == 'Tous':
                for jour_col, jour_nom in jours_mapping.items():
                    jours_a_verifier.append((jour_col, jour_nom))
            else:
                jours_a_verifier.append((jour_selectionne, jour_selectionne))
            
            for jour_col, jour_nom in jours_a_verifier:
                planning = agent[jour_col]
                heure_debut, heure_fin = self.extraire_heures(planning)
                
                # DEBUG pour Theo
                if "Theo" in nom_agent and jour_nom == "Mardi":
                    st.write(f"DEBUG Theo - Planning: '{planning}' -> Début: {heure_debut}, Fin: {heure_fin}")
                
                if heure_debut is not None and heure_fin is not None:
                    # Appliquer ajustement heure d'été si nécessaire
                    if heure_ete_active:
                        heure_debut_ajustee = self.ajuster_heure_ete(heure_debut, heure_ete_active)
                        heure_fin_ajustee = self.ajuster_heure_ete(heure_fin, heure_ete_active)
                    else:
                        heure_debut_ajustee = heure_debut
                        heure_fin_ajustee = heure_fin
                    
                    # RAMASSAGE - vérifier l'heure de début
                    if heure_debut_ajustee in heures_ramassage_selectionnees:
                        agent_data = {
                            'Agent': nom_agent,
                            'Jour': jour_nom,
                            'Heure': heure_debut_ajustee,
                            'Heure_affichage': f"{heure_debut_ajustee}h",
                            'Adresse': info_agent['adresse'],
                            'Telephone': info_agent['tel'],
                            'Societe': info_agent['societe'],
                            'Voiture': info_agent['voiture']
                        }
                        self.liste_ramassage_actuelle.append(agent_data)
                    
                    # DÉPART - vérifier l'heure de fin
                    heure_fin_comparaison = heure_fin_ajustee
                    if heure_fin_comparaison >= 24:
                        heure_fin_comparaison = heure_fin_comparaison - 24
                    
                    if heure_fin_comparaison in heures_depart_selectionnees:
                        heure_fin_affichee = heure_fin_ajustee
                        if heure_fin_ajustee >= 24:
                            heure_fin_affichee = heure_fin_ajustee - 24
                        
                        agent_data = {
                            'Agent': nom_agent,
                            'Jour': jour_nom,
                            'Heure': heure_fin_ajustee,
                            'Heure_affichage': f"{heure_fin_affichee}h",
                            'Adresse': info_agent['adresse'],
                            'Telephone': info_agent['tel'],
                            'Societe': info_agent['societe'],
                            'Voiture': info_agent['voiture']
                        }
                        self.liste_depart_actuelle.append(agent_data)
        
        # Trier par jour (dans l'ordre de la semaine) puis par heure
        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        self.liste_ramassage_actuelle.sort(key=lambda x: (ordre_jours.index(x['Jour']), x['Heure']))
        self.liste_depart_actuelle.sort(key=lambda x: (ordre_jours.index(x['Jour']), x['Heure']))
    
    def ajouter_affectation(self, chauffeur, heure, agents_selectionnes, type_transport, jour):
        """Ajoute une affectation de chauffeur"""
        for agent_nom in agents_selectionnes:
            info_agent = self.get_info_agent(agent_nom)
            
            nouvelle_affectation = {
                'Chauffeur': chauffeur,
                'Heure': heure,
                'Agent': agent_nom,
                'Adresse': info_agent['adresse'],
                'Telephone': info_agent['tel'],
                'Societe': info_agent['societe'],
                'Vehicule': "Non renseigné",
                'Type_Transport': type_transport,
                'Jour': jour
            }
            
            nouvelle_ligne = pd.DataFrame([nouvelle_affectation])
            self.df_chauffeurs = pd.concat([self.df_chauffeurs, nouvelle_ligne], ignore_index=True)
        
        st.session_state.chauffeurs_data = self.df_chauffeurs
    
    def supprimer_affectation(self, index):
        """Supprime une affectation"""
        self.df_chauffeurs = self.df_chauffeurs.drop(index).reset_index(drop=True)
        st.session_state.chauffeurs_data = self.df_chauffeurs

    def separer_chauffeurs_taxi(self, df_filtre):
        """Sépare les chauffeurs Taxi des autres chauffeurs"""
        chauffeurs_taxi = df_filtre[df_filtre['Chauffeur'].str.contains('taxi|Taxi|TAXI', na=False)]
        chauffeurs_autres = df_filtre[~df_filtre['Chauffeur'].str.contains('taxi|Taxi|TAXI', na=False)]
        
        return chauffeurs_taxi, chauffeurs_autres
    
    def exporter_suivi_chauffeurs(self, jour_selectionne_export):
        """Exporte le suivi des chauffeurs avec statistiques complètes et mise en forme - VERSION CORRIGÉE"""
        if self.df_chauffeurs.empty:
            return None
        
        if jour_selectionne_export == "Tous":
            df_filtre = self.df_chauffeurs
        else:
            df_filtre = self.df_chauffeurs[self.df_chauffeurs['Jour'] == jour_selectionne_export]
        
        if df_filtre.empty:
            return None
        
        # Séparer Taxi des autres chauffeurs
        chauffeurs_taxi, chauffeurs_autres = self.separer_chauffeurs_taxi(df_filtre)
        
        donnees_export = []
        
        # Style d'en-tête SIMPLIFIÉ
        entete_style = ["Salarié", "HEURE", "CHAUFFEUR", "DESTINATION", "Plateau", "type", "date"]
        donnees_export.append(entete_style)
        donnees_export.append(["", "", "", "", "", "", ""])
        
        # Traiter d'abord les chauffeurs normaux
        if not chauffeurs_autres.empty:
            donnees_export.append(["🚗 CHAUFFEURS NORMAUX", "", "", "", "", "", ""])
            donnees_export.append(["", "", "", "", "", "", ""])
            
            total_courses_normaux = 0
            statistiques_societes_normaux = {}
            statistiques_chauffeurs_normaux = {}
            
            # Grouper par jour, chauffeur, heure et type
            groupes = chauffeurs_autres.groupby(['Jour', 'Chauffeur', 'Heure', 'Type_Transport'])
            
            # Trier par date, puis chauffeur, puis heure
            ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            groupes_tries = sorted(groupes, key=lambda x: (
                ordre_jours.index(x[0][0]),
                x[0][1], 
                x[0][2]
            ))
            
            for (jour, chauffeur, heure, type_transport), groupe in groupes_tries:
                date_groupe = self.get_date_du_jour(jour)
                nb_personnes_course = len(groupe)
                societes_course = {}
                
                # Compter par chauffeur - CORRECTION ICI
                if chauffeur not in statistiques_chauffeurs_normaux:
                    statistiques_chauffeurs_normaux[chauffeur] = 0
                statistiques_chauffeurs_normaux[chauffeur] += 1
                
                # Ajouter chaque agent
                for idx, (_, ligne) in enumerate(groupe.iterrows()):
                    societe = ligne['Societe']
                    if societe not in societes_course:
                        societes_course[societe] = 0
                    societes_course[societe] += 1
                    
                    if societe not in statistiques_societes_normaux:
                        statistiques_societes_normaux[societe] = 0
                    statistiques_societes_normaux[societe] += 1
                    
                    donnees_export.append([
                        ligne['Agent'], f"{heure}", chauffeur, ligne['Adresse'],
                        societe, type_transport.lower(), date_groupe
                    ])
                
                # Ajouter les statistiques de la course
                if societes_course:
                    pourcentages = []
                    for societe, count in societes_course.items():
                        pourcentage = (count / nb_personnes_course) * 100
                        pourcentages.append(f"{pourcentage:.0f}% {societe}")
                    
                    texte_pourcentages = " + ".join(pourcentages)
                    donnees_export.append([
                        f"RÉPARTITION COURSE ({nb_personnes_course} pers.)", "", "", texte_pourcentages, "", "", ""
                    ])
            
                total_courses_normaux += 1
                donnees_export.append(["", "", "", "", "", "", ""])
        
        # Traiter les chauffeurs Taxi - CORRECTION COMPLÈTE
        if not chauffeurs_taxi.empty:
            donnees_export.append(["🚕 CHAUFFEURS TAXI", "", "", "", "", "", ""])
            donnees_export.append(["", "", "", "", "", "", ""])
            
            total_courses_taxi = 0
            statistiques_societes_taxi = {}
            statistiques_chauffeurs_taxi = {}
            
            # CORRECTION : Grouper correctement les courses Taxi
            groupes_taxi = chauffeurs_taxi.groupby(['Chauffeur', 'Heure', 'Type_Transport', 'Jour'])
            
            # Trier par chauffeur, puis heure
            groupes_taxi_tries = sorted(groupes_taxi, key=lambda x: (
                x[0][0],  # Chauffeur
                x[0][1],  # Heure
                x[0][3]   # Jour
            ))
            
            for (chauffeur, heure, type_transport, jour), groupe in groupes_taxi_tries:
                date_groupe = self.get_date_du_jour(jour)
                nb_personnes_course = len(groupe)
                societes_course = {}
                
                # CORRECTION : Compter correctement les chauffeurs taxi
                if chauffeur not in statistiques_chauffeurs_taxi:
                    statistiques_chauffeurs_taxi[chauffeur] = 0
                statistiques_chauffeurs_taxi[chauffeur] += 1
                
                # Ajouter chaque agent
                for idx, (_, ligne) in enumerate(groupe.iterrows()):
                    societe = ligne['Societe']
                    if societe not in societes_course:
                        societes_course[societe] = 0
                    societes_course[societe] += 1
                    
                    if societe not in statistiques_societes_taxi:
                        statistiques_societes_taxi[societe] = 0
                    statistiques_societes_taxi[societe] += 1
                    
                    donnees_export.append([
                        ligne['Agent'], f"{heure}", chauffeur, ligne['Adresse'],
                        societe, type_transport.lower(), date_groupe
                    ])
                
                # Ajouter les statistiques de la course
                if societes_course:
                    pourcentages = []
                    for societe, count in societes_course.items():
                        pourcentage = (count / nb_personnes_course) * 100
                        pourcentages.append(f"{pourcentage:.0f}% {societe}")
                    
                    texte_pourcentages = " + ".join(pourcentages)
                    donnees_export.append([
                        f"RÉPARTITION COURSE TAXI ({nb_personnes_course} pers.)", "", "", texte_pourcentages, "", "", ""
                    ])
                
                total_courses_taxi += 1
                donnees_export.append(["", "", "", "", "", "", ""])
        
        # 🔥 CORRECTION : Supprimer les doublons et vérifier le comptage
        # Supprimer les lignes vides en double à la fin
        while len(donnees_export) > 1 and donnees_export[-1] == ["", "", "", "", "", "", ""]:
            donnees_export.pop()
        
        # Vérifier le comptage réel des courses taxi
        courses_taxi_reel = 0
        for i, ligne in enumerate(donnees_export):
            if len(ligne) > 2 and "Taxi" in str(ligne[2]) and "RÉPARTITION" not in str(ligne[0]) and ligne[0] not in ["", "🚕 CHAUFFEURS TAXI"]:
                # Compter les courses uniques basées sur les lignes de répartition
                if i + 1 < len(donnees_export) and "RÉPARTITION COURSE TAXI" in str(donnees_export[i + 1][0]):
                    courses_taxi_reel += 1
        
        # Utiliser le comptage réel si différent
        if courses_taxi_reel > 0 and courses_taxi_reel != total_courses_taxi:
            total_courses_taxi = courses_taxi_reel
        
        # 🔥 STATISTIQUES GLOBALES SIMPLIFIÉES
        donnees_export.append(["STATISTIQUES GLOBALES", "", "", "", "", "", ""])
        
        # Statistiques pour chauffeurs normaux
        if not chauffeurs_autres.empty:
            donnees_export.append(["🚗 CHAUFFEURS NORMAUX", "", "", "", "", "", ""])
            donnees_export.append([f"Total des courses normales: {total_courses_normaux}", "", "", "", "", "", ""])
            
            # Statistiques par chauffeur normaux
            donnees_export.append(["📊 PAR CHAUFFEUR NORMAL", "", "", "", "", "", ""])
            for chauffeur, nb_courses in sorted(statistiques_chauffeurs_normaux.items(), key=lambda x: x[1], reverse=True):
                pourcentage_chauffeur = (nb_courses / total_courses_normaux * 100) if total_courses_normaux > 0 else 0
                donnees_export.append([
                    "", "", f"{chauffeur}: {nb_courses} courses ({pourcentage_chauffeur:.1f}%)", "", "", "", ""
                ])
            
            # Statistiques par société normaux
            donnees_export.append(["🏢 PAR SOCIÉTÉ NORMALE", "", "", "", "", "", ""])
            total_personnes_normaux = sum(statistiques_societes_normaux.values())
            for societe, count in sorted(statistiques_societes_normaux.items(), key=lambda x: x[1], reverse=True):
                pourcentage_global = (count / total_personnes_normaux * 100) if total_personnes_normaux > 0 else 0
                donnees_export.append([
                    "", "", "", f"{societe}: {count} personnes ({pourcentage_global:.1f}%)", "", "", ""
                ])
        
        # Statistiques pour Taxi
        if not chauffeurs_taxi.empty:
            donnees_export.append(["🚕 CHAUFFEURS TAXI", "", "", "", "", "", ""])
            donnees_export.append([f"Total des courses taxi: {total_courses_taxi}", "", "", "", "", "", ""])
            
            # Statistiques par chauffeur taxi
            donnees_export.append(["📊 PAR CHAUFFEUR TAXI", "", "", "", "", "", ""])
            for chauffeur, nb_courses in sorted(statistiques_chauffeurs_taxi.items(), key=lambda x: x[1], reverse=True):
                pourcentage_chauffeur = (nb_courses / total_courses_taxi * 100) if total_courses_taxi > 0 else 0
                donnees_export.append([
                    "", "", f"{chauffeur}: {nb_courses} courses ({pourcentage_chauffeur:.1f}%)", "", "", "", ""
                ])
            
            # Statistiques par société taxi
            donnees_export.append(["🏢 PAR SOCIÉTÉ TAXI", "", "", "", "", "", ""])
            total_personnes_taxi = sum(statistiques_societes_taxi.values())
            for societe, count in sorted(statistiques_societes_taxi.items(), key=lambda x: x[1], reverse=True):
                pourcentage_global = (count / total_personnes_taxi * 100) if total_personnes_taxi > 0 else 0
                donnees_export.append([
                    "", "", "", f"{societe}: {count} personnes ({pourcentage_global:.1f}%)", "", "", ""
                ])
        
        # RÉSUMÉ FINAL SIMPLIFIÉ
        donnees_export.append(["", "", "", "", "", "", ""])
        donnees_export.append(["RÉSUMÉ FINAL", "", "", "", "", "", ""])
        total_courses_global = total_courses_normaux + total_courses_taxi
        total_personnes_global = (sum(statistiques_societes_normaux.values()) if not chauffeurs_autres.empty else 0) + (sum(statistiques_societes_taxi.values()) if not chauffeurs_taxi.empty else 0)
        
        donnees_export.append([f"Total courses toutes catégories: {total_courses_global}", "", "", "", "", "", ""])
        donnees_export.append([f"Total personnes transportées: {total_personnes_global}", "", "", "", "", "", ""])
        
        return pd.DataFrame(donnees_export)

    def generer_rapport_imprimable(self, type_liste, jour_selectionne):
        """Génère un rapport imprimable pour les listes de ramassage/départ"""
        if type_liste == "ramassage":
            liste = self.liste_ramassage_actuelle
            titre = "LISTE DE RAMASSAGE"
        else:
            liste = self.liste_depart_actuelle
            titre = "LISTE DE DÉPART"
        
        if not liste:
            return None
        
        # Filtrer par jour si sélectionné
        if jour_selectionne != 'Tous':
            liste = [agent for agent in liste if agent['Jour'] == jour_selectionne]
        
        if not liste:
            return None
        
        # Créer le rapport
        donnees_rapport = []
        donnees_rapport.append([titre])
        donnees_rapport.append([f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"])
        donnees_rapport.append([])
        
        # Grouper par jour
        agents_par_jour = {}
        for agent in liste:
            jour = agent['Jour']
            if jour not in agents_par_jour:
                agents_par_jour[jour] = []
            agents_par_jour[jour].append(agent)
        
        # Trier les jours dans l'ordre
        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        for jour in ordre_jours:
            if jour in agents_par_jour:
                date_jour = self.get_date_du_jour(jour)
                donnees_rapport.append([f"📅 {jour} ({date_jour})"])
                donnees_rapport.append(["Agent", "Heure", "Adresse", "Téléphone", "Société"])
                
                # Trier les agents par heure
                agents_par_jour[jour].sort(key=lambda x: x['Heure'])
                for agent in agents_par_jour[jour]:
                    donnees_rapport.append([
                        agent['Agent'],
                        agent['Heure_affichage'],
                        agent['Adresse'],
                        agent['Telephone'],
                        agent['Societe']
                    ])
                donnees_rapport.append([])
        
        return pd.DataFrame(donnees_rapport)

    def generer_pdf_imprimable(self, type_liste, jour_selectionne):
        """Génère un PDF imprimable pour les listes de ramassage/départ"""
        if type_liste == "ramassage":
            liste = self.liste_ramassage_actuelle
            titre = "LISTE DE RAMASSAGE"
        else:
            liste = self.liste_depart_actuelle
            titre = "LISTE DE DÉPART"
        
        if not liste:
            return None
        
        # Filtrer par jour si sélectionné
        if jour_selectionne != 'Tous':
            liste = [agent for agent in liste if agent['Jour'] == jour_selectionne]
        
        if not liste:
            return None
        
        # Créer le PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
        elements = []
        
        styles = getSampleStyleSheet()
        titre_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1,  # Centré
            textColor=colors.HexColor('#1f77b4')
        )
        
        # Titre
        titre_para = Paragraph(titre, titre_style)
        elements.append(titre_para)
        
        # Date de génération
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,
            spaceAfter=20
        )
        date_para = Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", date_style)
        elements.append(date_para)
        
        elements.append(Spacer(1, 20))
        
        # Grouper par jour
        agents_par_jour = {}
        for agent in liste:
            jour = agent['Jour']
            if jour not in agents_par_jour:
                agents_par_jour[jour] = []
            agents_par_jour[jour].append(agent)
        
        # Trier les jours dans l'ordre
        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        for jour in ordre_jours:
            if jour in agents_par_jour:
                date_jour = self.get_date_du_jour(jour)
                
                # Titre du jour
                jour_style = ParagraphStyle(
                    'JourStyle',
                    parent=styles['Heading2'],
                    fontSize=12,
                    spaceAfter=12,
                    textColor=colors.HexColor('#ff7f0e')
                )
                jour_para = Paragraph(f"📅 {jour} ({date_jour})", jour_style)
                elements.append(jour_para)
                
                # Préparer les données du tableau
                data = [["Agent", "Heure", "Adresse", "Téléphone", "Société"]]
                
                # Trier les agents par heure
                agents_par_jour[jour].sort(key=lambda x: x['Heure'])
                for agent in agents_par_jour[jour]:
                    data.append([
                        agent['Agent'],
                        agent['Heure_affichage'],
                        agent['Adresse'],
                        agent['Telephone'],
                        agent['Societe']
                    ])
                
                # Créer le tableau
                table = Table(data, colWidths=[1.5*inch, 0.7*inch, 2.5*inch, 1.2*inch, 1.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 20))
        
        # Construire le PDF
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data

def main():
    st.set_page_config(
        page_title="🚗 Gestionnaire de Transport",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS personnalisé
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .section-header {
            font-size: 1.5rem;
            color: #ff7f0e;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .success-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .print-button {
            background-color: #28a745;
            color: white;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">🚗 Gestionnaire de Transport Avancé</h1>', unsafe_allow_html=True)
    
    # Initialiser la classe principale
    gestion = GestionTransportWeb()
    
    # Sidebar pour les paramètres
    with st.sidebar:
        st.header("⚙️ Paramètres")
        
        # Upload du fichier Excel
        uploaded_file = st.file_uploader("📁 Choisir le fichier Excel", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                # Charger les données en sautant les 2 premières lignes d'en-tête
                gestion.df = pd.read_excel(uploaded_file, skiprows=2)
                
                # Vérifier et renommer les colonnes
                if len(gestion.df.columns) >= 9:
                    gestion.df.columns = ['Salarie', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Qualification']
                    gestion.dates_par_jour = gestion.extraire_dates_des_entetes(uploaded_file)
                    
                    st.success(f"✅ {uploaded_file.name} chargé")
                    st.success(f"📊 {len(gestion.df)} agents détectés")
                    
                    # Afficher les dates détectées
                    with st.expander("📅 Dates détectées"):
                        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                        for jour in ordre_jours:
                            if jour in gestion.dates_par_jour:
                                st.write(f"**{jour}**: {gestion.dates_par_jour[jour]}")
                else:
                    st.error(f"❌ Format de fichier incorrect. Colonnes détectées: {len(gestion.df.columns)}")
                    st.write("Colonnes:", gestion.df.columns.tolist())
                        
            except Exception as e:
                st.error(f"❌ Erreur lors du chargement: {str(e)}")
        
        st.header("🎛️ Filtres")
        heure_ete_active = st.checkbox("🕒 Appliquer l'ajustement heure d'été", help="3h → 2h, 7h → 6h, etc.")
        
        jour_selectionne = st.selectbox(
            "Jour à afficher",
            ['Tous', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🚗 Ramassage")
            heure_6h = st.checkbox("6h", value=True, key="r6")
            heure_7h = st.checkbox("7h", value=True, key="r7")
            heure_8h = st.checkbox("8h", value=True, key="r8")
            heure_22h = st.checkbox("22h", value=True, key="r22")
        
        with col2:
            st.subheader("🚙 Départ")
            heure_22h_d = st.checkbox("22h ", value=True, key="d22")
            heure_23h = st.checkbox("23h", value=True, key="d23")
            heure_00h = st.checkbox("00h", value=True, key="d0")
            heure_01h = st.checkbox("01h", value=True, key="d1")
            heure_02h = st.checkbox("02h", value=True, key="d2")
            heure_03h = st.checkbox("03h", value=True, key="d3")
    
    # Contenu principal
    if gestion.df is not None:
        # Préparer les heures sélectionnées
        heures_ramassage = []
        if heure_6h: heures_ramassage.append(6)
        if heure_7h: heures_ramassage.append(7)
        if heure_8h: heures_ramassage.append(8)
        if heure_22h: heures_ramassage.append(22)
        
        heures_depart = []
        if heure_22h_d: heures_depart.append(22)
        if heure_23h: heures_depart.append(23)
        if heure_00h: heures_depart.append(0)
        if heure_01h: heures_depart.append(1)
        if heure_02h: heures_depart.append(2)
        if heure_03h: heures_depart.append(3)
        
        # Traiter les données
        gestion.traiter_donnees(heure_ete_active, jour_selectionne, heures_ramassage, heures_depart)
        
        # Onglets
        tab1, tab2, tab3 = st.tabs(["🚗 Liste de Ramassage", "🚙 Liste de Départ", "👨‍✈️ Gestion Chauffeurs"])
        
        with tab1:
            st.markdown('<h2 class="section-header">📋 Liste de Ramassage</h2>', unsafe_allow_html=True)
            
            # Boutons Imprimer
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            with col_btn1:
                if st.button("📄 Excel Imprimable", type="primary"):
                    rapport = gestion.generer_rapport_imprimable("ramassage", jour_selectionne)
                    if rapport is not None:
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            rapport.to_excel(writer, sheet_name='Liste_Ramassage', index=False, header=False)
                        
                        st.download_button(
                            label="📥 Télécharger Excel",
                            data=output.getvalue(),
                            file_name=f"Liste_Ramassage_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                    else:
                        st.warning("Aucune donnée à imprimer")
            
            with col_btn2:
                if st.button("📊 PDF Imprimable", type="secondary"):
                    pdf_data = gestion.generer_pdf_imprimable("ramassage", jour_selectionne)
                    if pdf_data is not None:
                        st.download_button(
                            label="📥 Télécharger PDF",
                            data=pdf_data,
                            file_name=f"Liste_Ramassage_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.warning("Aucune donnée à imprimer")
            
            if gestion.liste_ramassage_actuelle:
                mode_heure = "HEURE D'ÉTÉ" if heure_ete_active else "HEURE NORMALE"
                st.write(f"**Mode:** {mode_heure} | **Jours:** {jour_selectionne} | **Heures:** {', '.join([f'{h}h' for h in heures_ramassage])}")
                
                # Afficher par jour dans l'ordre
                ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                for jour in ordre_jours:
                    agents_du_jour = [a for a in gestion.liste_ramassage_actuelle if a['Jour'] == jour]
                    if agents_du_jour and (jour_selectionne == 'Tous' or jour == jour_selectionne):
                        date_jour = gestion.get_date_du_jour(jour)
                        st.subheader(f"📅 {jour} ({date_jour})")
                        
                        df_affiche = pd.DataFrame(agents_du_jour)[['Agent', 'Heure_affichage', 'Adresse', 'Telephone', 'Societe']]
                        st.dataframe(df_affiche, use_container_width=True)
            else:
                st.info("ℹ️ Aucun agent trouvé avec les filtres sélectionnés")
        
        with tab2:
            st.markdown('<h2 class="section-header">📋 Liste de Départ</h2>', unsafe_allow_html=True)
            
            # Boutons Imprimer
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            with col_btn1:
                if st.button("📄 Excel Imprimable", type="primary", key="excel_depart"):
                    rapport = gestion.generer_rapport_imprimable("depart", jour_selectionne)
                    if rapport is not None:
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            rapport.to_excel(writer, sheet_name='Liste_Depart', index=False, header=False)
                        
                        st.download_button(
                            label="📥 Télécharger Excel",
                            data=output.getvalue(),
                            file_name=f"Liste_Depart_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                    else:
                        st.warning("Aucune donnée à imprimer")
            
            with col_btn2:
                if st.button("📊 PDF Imprimable", type="secondary", key="pdf_depart"):
                    pdf_data = gestion.generer_pdf_imprimable("depart", jour_selectionne)
                    if pdf_data is not None:
                        st.download_button(
                            label="📥 Télécharger PDF",
                            data=pdf_data,
                            file_name=f"Liste_Depart_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.warning("Aucune donnée à imprimer")
            
            if gestion.liste_depart_actuelle:
                mode_heure = "HEURE D'ÉTÉ" if heure_ete_active else "HEURE NORMALE"
                st.write(f"**Mode:** {mode_heure} | **Jours:** {jour_selectionne} | **Heures:** {', '.join([f'{h}h' for h in heures_depart])}")
                
                # Afficher par jour dans l'ordre
                ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                for jour in ordre_jours:
                    agents_du_jour = [a for a in gestion.liste_depart_actuelle if a['Jour'] == jour]
                    if agents_du_jour and (jour_selectionne == 'Tous' or jour == jour_selectionne):
                        date_jour = gestion.get_date_du_jour(jour)
                        st.subheader(f"📅 {jour} ({date_jour})")
                        
                        df_affiche = pd.DataFrame(agents_du_jour)[['Agent', 'Heure_affichage', 'Adresse', 'Telephone', 'Societe']]
                        st.dataframe(df_affiche, use_container_width=True)
            else:
                st.info("ℹ️ Aucun agent trouvé avec les filtres sélectionnés")
        
        with tab3:
            st.markdown('<h2 class="section-header">👨‍✈️ Gestion des Chauffeurs</h2>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("➕ Ajouter une affectation")
                
                # Liste des chauffeurs existants + Taxi
                chauffeurs_liste = gestion.get_liste_chauffeurs_voitures()
                noms_chauffeurs = [ch['chauffeur'] for ch in chauffeurs_liste] if chauffeurs_liste else []
                
                # Ajouter "Taxi" à la liste des chauffeurs
                if "Taxi" not in noms_chauffeurs:
                    noms_chauffeurs.append("Taxi")
                
                if not noms_chauffeurs:
                    noms_chauffeurs = ["Aucun chauffeur trouvé"]
                
                chauffeur = st.selectbox("Chauffeur", noms_chauffeurs)
                type_transport = st.selectbox("Type de transport", ["Ramassage", "Départ"])
                
                # Heures selon le type
                if type_transport == "Ramassage":
                    heure = st.selectbox("Heure", ['6h', '7h', '8h', '22h'])
                else:
                    heure = st.selectbox("Heure", ['22h', '23h', '00h', '01h', '02h', '03h'])
                
                jour = st.selectbox("Jour", ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'])
                
                # Liste des agents disponibles
                if type_transport == "Ramassage":
                    agents_disponibles = [agent['Agent'] for agent in gestion.liste_ramassage_actuelle if agent['Jour'] == jour]
                else:
                    agents_disponibles = [agent['Agent'] for agent in gestion.liste_depart_actuelle if agent['Jour'] == jour]
                
                # Filtrer les agents déjà affectés
                agents_affectes = set(gestion.df_chauffeurs['Agent'].tolist()) if not gestion.df_chauffeurs.empty else set()
                agents_disponibles = [agent for agent in agents_disponibles if agent not in agents_affectes]
                
                if agents_disponibles:
                    agents_selectionnes = st.multiselect("Agents disponibles", agents_disponibles)
                    
                    if st.button("✅ Ajouter l'affectation", type="primary"):
                        if chauffeur and heure and agents_selectionnes:
                            gestion.ajouter_affectation(chauffeur, heure, agents_selectionnes, type_transport, jour)
                            st.success(f"Affectation ajoutée pour {len(agents_selectionnes)} agent(s) avec {chauffeur}")
                            st.rerun()
                        else:
                            st.warning("Veuillez sélectionner un chauffeur, une heure et au moins un agent")
                else:
                    st.warning("Aucun agent disponible pour ces critères")
            
            with col2:
                st.subheader("📋 Affectations en cours")
                
                if not gestion.df_chauffeurs.empty:
                    # Afficher les affectations
                    for idx, ligne in gestion.df_chauffeurs.iterrows():
                        with st.container():
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                chauffeur_nom = ligne['Chauffeur']
                                badge = "🚕" if "taxi" in chauffeur_nom.lower() else "🚗"
                                st.write(f"{badge} **{chauffeur_nom}** - {ligne['Heure']} - {ligne['Type_Transport']} - {ligne['Jour']}")
                                st.write(f"👤 {ligne['Agent']} | 📍 {ligne['Adresse']} | 📞 {ligne['Telephone']} | 🏢 {ligne['Societe']}")
                            with col_b:
                                if st.button("🗑️", key=f"del_{idx}"):
                                    gestion.supprimer_affectation(idx)
                                    st.rerun()
                            st.divider()
                    
                    # Bouton d'export
                    st.subheader("📊 Export avec Statistiques")
                    jour_export = st.selectbox("Jour à exporter", ['Tous', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'], key="export_jour")
                    
                    if st.button("💾 Exporter le suivi des chauffeurs", type="primary"):
                        df_export = gestion.exporter_suivi_chauffeurs(jour_export)
                        if df_export is not None:
                            # Créer le fichier Excel
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                df_export.to_excel(writer, sheet_name='Suivi_Chauffeurs', index=False, header=False)
                            
                            # Téléchargement
                            st.download_button(
                                label="📥 Télécharger le fichier Excel",
                                data=output.getvalue(),
                                file_name=f"Suivi_Chauffeurs_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx",
                                mime="application/vnd.ms-excel"
                            )
                            
                            # Aperçu des statistiques
                            st.markdown("### 📈 Aperçu des Statistiques Incluses")
                            st.markdown("""
                            - ✅ **Séparation Taxi/Chauffeurs normaux**
                            - ✅ **Total des courses par catégorie**
                            - ✅ **Courses par chauffeur** avec pourcentages
                            - ✅ **Personnes transportées par société** avec pourcentages
                            - ✅ **Résumé final détaillé**
                            """)
                        else:
                            st.warning("Aucune donnée à exporter pour les critères sélectionnés")
                
                else:
                    st.info("ℹ️ Aucune affectation de chauffeur enregistrée")
    
    else:
        st.info("👈 Veuillez sélectionner un fichier Excel dans la barre latérale pour commencer")

if __name__ == "__main__":
    main()
