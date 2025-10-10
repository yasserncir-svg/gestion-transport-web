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
        self.dates_par_jour = {}
        self.liste_ramassage_actuelle = []
        self.liste_depart_actuelle = []
        
        # Fichier de sauvegarde permanent
        self.fichier_sauvegarde = "affectations_permanentes.xlsx"
        self.fichier_info_complementaire = "info_complementaire.xlsx"
        
        # Prix par défaut
        self.prix_course_chauffeur = 10  # Prix par défaut pour les chauffeurs normaux
        self.prix_course_taxi = 15       # Prix par défaut pour les taxis
        
        # Initialiser ou charger les données
        self.initialiser_donnees()
        self.charger_infos_agents()
    
    def initialiser_donnees(self):
        """Initialise ou charge les données depuis le fichier de sauvegarde"""
        # Essayer de charger depuis la session state d'abord
        if 'chauffeurs_data' not in st.session_state:
            # Si pas en session, charger depuis le fichier
            if os.path.exists(self.fichier_sauvegarde):
                try:
                    self.df_chauffeurs = pd.read_excel(self.fichier_sauvegarde)
                    st.session_state.chauffeurs_data = self.df_chauffeurs
                    st.sidebar.success("✅ Affectations chargées depuis la sauvegarde")
                except Exception as e:
                    st.sidebar.warning("⚠️ Erreur chargement sauvegarde, nouvelle session créée")
                    self.df_chauffeurs = pd.DataFrame(columns=[
                        'Chauffeur', 'Heure', 'Agent', 'Adresse', 'Telephone', 'Societe', 
                        'Vehicule', 'Type_Transport', 'Jour', 'Date_Ajout', 'Date_Reelle',
                        'Prix_Course', 'Statut_Paiement'
                    ])
                    st.session_state.chauffeurs_data = self.df_chauffeurs
            else:
                # Première utilisation
                self.df_chauffeurs = pd.DataFrame(columns=[
                    'Chauffeur', 'Heure', 'Agent', 'Adresse', 'Telephone', 'Societe', 
                    'Vehicule', 'Type_Transport', 'Jour', 'Date_Ajout', 'Date_Reelle',
                    'Prix_Course', 'Statut_Paiement'
                ])
                st.session_state.chauffeurs_data = self.df_chauffeurs
        else:
            # Déjà en session state
            self.df_chauffeurs = st.session_state.chauffeurs_data
        
        # Initialiser les informations complémentaires
        if 'info_complementaire' not in st.session_state:
            if os.path.exists(self.fichier_info_complementaire):
                try:
                    self.df_info_complementaire = pd.read_excel(self.fichier_info_complementaire)
                    st.session_state.info_complementaire = self.df_info_complementaire
                except:
                    self.df_info_complementaire = pd.DataFrame(columns=['Agent', 'Adresse', 'Telephone', 'Societe'])
                    st.session_state.info_complementaire = self.df_info_complementaire
            else:
                self.df_info_complementaire = pd.DataFrame(columns=['Agent', 'Adresse', 'Telephone', 'Societe'])
                st.session_state.info_complementaire = self.df_info_complementaire
        else:
            self.df_info_complementaire = st.session_state.info_complementaire
    
    def sauvegarder_donnees_permanentes(self):
        """Sauvegarde les données dans un fichier permanent"""
        try:
            if not self.df_chauffeurs.empty:
                self.df_chauffeurs.to_excel(self.fichier_sauvegarde, index=False)
            
            if not self.df_info_complementaire.empty:
                self.df_info_complementaire.to_excel(self.fichier_info_complementaire, index=False)
            
            return True
        except Exception as e:
            st.error(f"❌ Erreur sauvegarde permanente: {e}")
            return False
    
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
        """Récupère les informations d'un agent depuis info.xlsx ou les données complémentaires"""
        # Chercher d'abord dans info.xlsx
        if self.df_info is not None and not self.df_info.empty:
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
                        
                        adresse = str(row.iloc[1]) if len(row) > 1 else ""
                        tel = str(row.iloc[2]) if len(row) > 2 else ""
                        societe = str(row.iloc[3]) if len(row) > 3 else ""
                        
                        # Si toutes les informations sont présentes, retourner
                        if adresse and tel and societe:
                            return {
                                "adresse": adresse,
                                "tel": tel,
                                "societe": societe,
                                "voiture": a_voiture
                            }
            except:
                pass
        
        # Chercher dans les informations complémentaires
        if not self.df_info_complementaire.empty:
            agent_trouve = self.df_info_complementaire[self.df_info_complementaire['Agent'] == nom_agent]
            if not agent_trouve.empty:
                return {
                    "adresse": agent_trouve.iloc[0]['Adresse'] if pd.notna(agent_trouve.iloc[0]['Adresse']) else "",
                    "tel": agent_trouve.iloc[0]['Telephone'] if pd.notna(agent_trouve.iloc[0]['Telephone']) else "",
                    "societe": agent_trouve.iloc[0]['Societe'] if pd.notna(agent_trouve.iloc[0]['Societe']) else "",
                    "voiture": "Non"
                }
        
        return {"adresse": "", "tel": "", "societe": "", "voiture": "Non"}
    
    def ajouter_info_agent(self, agent, adresse, telephone, societe):
        """Ajoute ou met à jour les informations d'un agent"""
        # Vérifier si l'agent existe déjà
        if not self.df_info_complementaire.empty:
            index_existant = self.df_info_complementaire[self.df_info_complementaire['Agent'] == agent].index
            if not index_existant.empty:
                # Mettre à jour
                self.df_info_complementaire.at[index_existant[0], 'Adresse'] = adresse
                self.df_info_complementaire.at[index_existant[0], 'Telephone'] = telephone
                self.df_info_complementaire.at[index_existant[0], 'Societe'] = societe
            else:
                # Ajouter nouveau
                nouvelle_info = pd.DataFrame({
                    'Agent': [agent],
                    'Adresse': [adresse],
                    'Telephone': [telephone],
                    'Societe': [societe]
                })
                self.df_info_complementaire = pd.concat([self.df_info_complementaire, nouvelle_info], ignore_index=True)
        else:
            # Première ajout
            self.df_info_complementaire = pd.DataFrame({
                'Agent': [agent],
                'Adresse': [adresse],
                'Telephone': [telephone],
                'Societe': [societe]
            })
        
        # Mettre à jour la session state
        st.session_state.info_complementaire = self.df_info_complementaire
        
        # Sauvegarder
        self.sauvegarder_donnees_permanentes()
    
    def verifier_agent_complet(self, nom_agent):
        """Vérifie si un agent a toutes les informations nécessaires"""
        info_agent = self.get_info_agent(nom_agent)
        return bool(info_agent['adresse'] and info_agent['tel'] and info_agent['societe'])
    
    def sauvegarder_affectations(self):
        """Sauvegarde les affectations dans un fichier Excel pour export"""
        if self.df_chauffeurs.empty:
            return None, None
        
        # Créer un nom de fichier avec la date du mois
        nom_fichier = f"affectations_chauffeurs_{datetime.now().strftime('%Y_%m')}.xlsx"
        
        # Sauvegarder dans un buffer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            self.df_chauffeurs.to_excel(writer, sheet_name='Affectations', index=False)
        
        return output.getvalue(), nom_fichier
    
    def charger_affectations(self, uploaded_file):
        """Charge les affectations depuis un fichier Excel"""
        try:
            df_charge = pd.read_excel(uploaded_file)
            # Vérifier que le fichier a les bonnes colonnes
            colonnes_requises = ['Chauffeur', 'Heure', 'Agent', 'Adresse', 'Telephone', 'Societe', 'Vehicule', 'Type_Transport', 'Jour', 'Date_Reelle']
            
            if all(col in df_charge.columns for col in colonnes_requises):
                self.df_chauffeurs = df_charge
                st.session_state.chauffeurs_data = self.df_chauffeurs
                # Sauvegarder en permanent
                self.sauvegarder_donnees_permanentes()
                return True
            else:
                st.error("❌ Le fichier ne contient pas les colonnes requises")
                return False
                
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement du fichier: {e}")
            return False
    
    def get_info_agent_original(self, nom_agent):
        """Récupère les informations d'un agent (version originale)"""
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
            
            # Mapping des positions des colonnes vers les jours
            positions_jours = {
                1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi', 
                5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'
            }
            
            # Parcourir les colonnes de jours
            for col_index, jour_nom in positions_jours.items():
                if col_index < len(df_entetes.columns):
                    # Prendre la cellule de la DEUXIÈME ligne (ligne 1) qui contient les dates
                    cellule = df_entetes.iloc[1, col_index]
                    nom_colonne = str(cellule) if pd.notna(cellule) else ""
                    
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
                    else:
                        # Date par défaut si non détectée
                        date_par_defaut = self.calculer_date_par_defaut(jour_nom)
                        dates_par_jour[jour_nom] = date_par_defaut
            
            return dates_par_jour
            
        except Exception as e:
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
            info_agent = self.get_info_agent_original(nom_agent)
            
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
                            'Voiture': info_agent['voiture'],
                            'Date_Reelle': self.get_date_du_jour(jour_nom)
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
                            'Voiture': info_agent['voiture'],
                            'Date_Reelle': self.get_date_du_jour(jour_nom)
                        }
                        self.liste_depart_actuelle.append(agent_data)
        
        # Trier par jour (dans l'ordre de la semaine) puis par heure
        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        self.liste_ramassage_actuelle.sort(key=lambda x: (ordre_jours.index(x['Jour']), x['Heure']))
        self.liste_depart_actuelle.sort(key=lambda x: (ordre_jours.index(x['Jour']), x['Heure']))
    
    def get_prix_course(self, chauffeur, type_transport):
        """Retourne le prix d'une course selon le type de chauffeur"""
        if "taxi" in str(chauffeur).lower():
            return self.prix_course_taxi
        else:
            return self.prix_course_chauffeur
    
    def ajouter_affectation(self, chauffeur, heure, agents_selectionnes, type_transport, jour, prix_specifique=None):
        """Ajoute une affectation de chauffeur avec la date réelle et le prix"""
        date_reelle = self.get_date_du_jour(jour)
        
        # Vérifier d'abord si tous les agents ont des informations complètes
        agents_incomplets = []
        for agent_nom in agents_selectionnes:
            if not self.verifier_agent_complet(agent_nom):
                agents_incomplets.append(agent_nom)
        
        # Si des agents ont des informations manquantes, afficher le formulaire
        if agents_incomplets:
            st.error(f"❌ Informations manquantes pour {len(agents_incomplets)} agent(s)")
            
            for agent_nom in agents_incomplets:
                info_agent = self.get_info_agent(agent_nom)
                
                with st.expander(f"📝 Compléter les informations pour: {agent_nom}", expanded=True):
                    st.warning(f"Veuillez compléter les informations manquantes pour {agent_nom}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        nouvelle_adresse = st.text_input(
                            "Adresse complète", 
                            value=info_agent['adresse'] if info_agent['adresse'] else "",
                            key=f"addr_{agent_nom}"
                        )
                        nouveau_telephone = st.text_input(
                            "Numéro de téléphone", 
                            value=info_agent['tel'] if info_agent['tel'] else "",
                            key=f"tel_{agent_nom}"
                        )
                    with col2:
                        nouvelle_societe = st.text_input(
                            "Société/Plateau", 
                            value=info_agent['societe'] if info_agent['societe'] else "",
                            key=f"soc_{agent_nom}"
                        )
                    
                    # Vérifier que tous les champs sont remplis
                    champs_remplis = nouvelle_adresse and nouveau_telephone and nouvelle_societe
                    
                    if st.button(f"💾 Sauvegarder les informations pour {agent_nom}", 
                                key=f"save_{agent_nom}", 
                                disabled=not champs_remplis):
                        if champs_remplis:
                            self.ajouter_info_agent(agent_nom, nouvelle_adresse, nouveau_telephone, nouvelle_societe)
                            st.success(f"✅ Informations sauvegardées pour {agent_nom}")
                            st.rerun()
                        else:
                            st.error("Veuillez remplir tous les champs")
            
            return False  # Empêcher l'ajout de l'affectation
        
        # Déterminer le prix
        if prix_specifique is not None:
            prix_course = prix_specifique
        else:
            prix_course = self.get_prix_course(chauffeur, type_transport)
        
        # Si tous les agents ont des informations complètes, ajouter l'affectation
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
                'Jour': jour,
                'Date_Ajout': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'Date_Reelle': date_reelle,
                'Prix_Course': prix_course,
                'Statut_Paiement': "Non payé"
            }
            
            nouvelle_ligne = pd.DataFrame([nouvelle_affectation])
            self.df_chauffeurs = pd.concat([self.df_chauffeurs, nouvelle_ligne], ignore_index=True)
        
        # Mettre à jour la session state
        st.session_state.chauffeurs_data = self.df_chauffeurs
        
        # Sauvegarder en permanent
        self.sauvegarder_donnees_permanentes()
        return True
    
    def supprimer_affectation(self, index):
        """Supprime une affectation"""
        self.df_chauffeurs = self.df_chauffeurs.drop(index).reset_index(drop=True)
        st.session_state.chauffeurs_data = self.df_chauffeurs
        
        # Sauvegarder en permanent
        self.sauvegarder_donnees_permanentes()

    def supprimer_toutes_affectations(self):
        """Supprime toutes les affectations"""
        self.df_chauffeurs = pd.DataFrame(columns=[
            'Chauffeur', 'Heure', 'Agent', 'Adresse', 'Telephone', 'Societe', 
            'Vehicule', 'Type_Transport', 'Jour', 'Date_Ajout', 'Date_Reelle',
            'Prix_Course', 'Statut_Paiement'
        ])
        st.session_state.chauffeurs_data = self.df_chauffeurs
        
        # Sauvegarder en permanent
        self.sauvegarder_donnees_permanentes()
        st.success("✅ Toutes les affectations ont été supprimées")

    # ... (TOUTES LES AUTRES MÉTHODES RESTENT IDENTIQUES À VOTRE SCRIPT ORIGINAL)
    # separer_chauffeurs_taxi, calculer_statistiques_mensuelles, calculer_paiements_mensuels, 
    # generer_rapport_paie_mensuel, exporter_suivi_chauffeurs, generer_rapport_imprimable, 
    # generer_pdf_imprimable - TOUTES CES MÉTHODES RESTENT EXACTEMENT COMME DANS VOTRE SCRIPT

def main():
    # TOUT LE CODE DE VOTRE FONCTION MAIN RESTE EXACTEMENT LE MÊME
    # Je n'ai modifié que la logique d'ajout d'affectation pour inclure la détection des agents manquants

if __name__ == "__main__":
    main()
