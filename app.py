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
        self.fichier_info_sauvegarde = "info_complementaire.xlsx"
        
        # Prix par défaut
        self.prix_course_chauffeur = 10  # Prix par défaut pour les chauffeurs normaux
        self.prix_course_taxi = 15       # Prix par défaut pour les taxis
        
        # Initialiser ou charger les données
        self.initialiser_donnees()
        self.charger_infos_agents()
    
    def initialiser_donnees(self):
        """Initialise ou charger les données depuis le fichier de sauvegarde"""
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
        
        # Charger les informations complémentaires
        if 'info_complementaire' not in st.session_state:
            if os.path.exists(self.fichier_info_sauvegarde):
                try:
                    self.df_info_complementaire = pd.read_excel(self.fichier_info_sauvegarde)
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
                self.df_info_complementaire.to_excel(self.fichier_info_sauvegarde, index=False)
            
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
        info_par_defaut = {
            "adresse": "Adresse non renseignée", 
            "tel": "Tél non renseigné", 
            "societe": "Société non renseignée", 
            "voiture": "Non"
        }
        
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
                        
                        return {
                            "adresse": str(row.iloc[1]) if len(row) > 1 else "Adresse non renseignée",
                            "tel": str(row.iloc[2]) if len(row) > 2 else "Tél non renseigné",
                            "societe": str(row.iloc[3]) if len(row) > 3 else "Société non renseignée",
                            "voiture": a_voiture
                        }
            except:
                pass
        
        # Chercher dans les informations complémentaires
        if not self.df_info_complementaire.empty:
            agent_trouve = self.df_info_complementaire[self.df_info_complementaire['Agent'] == nom_agent]
            if not agent_trouve.empty:
                return {
                    "adresse": agent_trouve.iloc[0]['Adresse'] if pd.notna(agent_trouve.iloc[0]['Adresse']) else "Adresse non renseignée",
                    "tel": agent_trouve.iloc[0]['Telephone'] if pd.notna(agent_trouve.iloc[0]['Telephone']) else "Tél non renseigné",
                    "societe": agent_trouve.iloc[0]['Societe'] if pd.notna(agent_trouve.iloc[0]['Societe']) else "Société non renseignée",
                    "voiture": "Non"
                }
        
        return info_par_defaut
    
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
    
    def get_prix_course(self, chauffeur, type_transport):
        """Retourne le prix d'une course selon le type de chauffeur"""
        if "taxi" in str(chauffeur).lower():
            return self.prix_course_taxi
        else:
            return self.prix_course_chauffeur
    
    def ajouter_affectation(self, chauffeur, heure, agents_selectionnes, type_transport, jour, prix_specifique=None):
        """Ajoute une affectation de chauffeur avec la date réelle et le prix"""
        date_reelle = self.get_date_du_jour(jour)
        
        # Déterminer le prix
        if prix_specifique is not None:
            prix_course = prix_specifique
        else:
            prix_course = self.get_prix_course(chauffeur, type_transport)
        
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
    
    def calculer_paiements_mensuels(self, mois=None, annee=None):
        """Calcule les paiements mensuels détaillés"""
        stats = self.calculer_statistiques_mensuelles(mois, annee)
        
        if not stats:
            return None
        
        paiements = {
            'periode': stats['periode'],
            'chauffeurs_normaux': {},
            'chauffeurs_taxi': {},
            'total_paiements': 0,
            'details': []
        }
        
        # Calculer les paiements pour les chauffeurs normaux
        for chauffeur, nb_courses in stats['chauffeurs_normaux'].items():
            montant = nb_courses * self.prix_course_chauffeur
            paiements['chauffeurs_normaux'][chauffeur] = {
                'nb_courses': nb_courses,
                'montant_total': montant,
                'prix_unitaire': self.prix_course_chauffeur
            }
            paiements['total_paiements'] += montant
        
        # Calculer les paiements pour les taxis
        for chauffeur, nb_courses in stats['chauffeurs_taxi'].items():
            montant = nb_courses * self.prix_course_taxi
            paiements['chauffeurs_taxi'][chauffeur] = {
                'nb_courses': nb_courses,
                'montant_total': montant,
                'prix_unitaire': self.prix_course_taxi
            }
            paiements['total_paiements'] += montant
        
        return paiements
    
    def generer_rapport_paie_mensuel(self, mois=None, annee=None):
        """Génère un rapport détaillé pour la paie mensuelle avec les prix"""
        paiements = self.calculer_paiements_mensuels(mois, annee)
        stats = self.calculer_statistiques_mensuelles(mois, annee)
        
        if not paiements or not stats:
            return None
        
        donnees_rapport = []
        
        # En-tête
        donnees_rapport.append(["RAPPORT DE PAIE MENSUEL - TRANSPORT"])
        donnees_rapport.append([f"Période: {paiements['periode']}"])
        donnees_rapport.append([f"Total des courses: {stats['total_courses']}"])
        donnees_rapport.append([f"Total à payer: {paiements['total_paiements']} €"])
        donnees_rapport.append([])
        
        # Chauffeurs normaux avec prix
        if paiements['chauffeurs_normaux']:
            donnees_rapport.append(["CHAUFFEURS NORMAUX"])
            donnees_rapport.append(["Chauffeur", "Nb courses", "Prix/unité", "Montant total"])
            
            for chauffeur, details in sorted(paiements['chauffeurs_normaux'].items(), 
                                           key=lambda x: x[1]['montant_total'], reverse=True):
                donnees_rapport.append([
                    chauffeur, 
                    details['nb_courses'], 
                    f"{details['prix_unitaire']} €",
                    f"{details['montant_total']} €"
                ])
            
            donnees_rapport.append([])
            
            # Sociétés pour chauffeurs normaux
            donnees_rapport.append(["RÉPARTITION PAR SOCIÉTÉ - CHAUFFEURS NORMAUX"])
            donnees_rapport.append(["Société", "Nombre de personnes", "Pourcentage"])
            
            total_personnes_normaux = sum(stats['societes_normaux'].values())
            for societe, count in sorted(stats['societes_normaux'].items(), key=lambda x: x[1], reverse=True):
                pourcentage = (count / total_personnes_normaux * 100) if total_personnes_normaux > 0 else 0
                donnees_rapport.append([societe, count, f"{pourcentage:.1f}%"])
            
            donnees_rapport.append([])
        
        # Chauffeurs Taxi avec prix
        if paiements['chauffeurs_taxi']:
            donnees_rapport.append(["CHAUFFEURS TAXI"])
            donnees_rapport.append(["Chauffeur", "Nb courses", "Prix/unité", "Montant total"])
            
            for chauffeur, details in sorted(paiements['chauffeurs_taxi'].items(), 
                                           key=lambda x: x[1]['montant_total'], reverse=True):
                donnees_rapport.append([
                    chauffeur, 
                    details['nb_courses'], 
                    f"{details['prix_unitaire']} €",
                    f"{details['montant_total']} €"
                ])
            
            donnees_rapport.append([])
            
            # Sociétés pour Taxi
            donnees_rapport.append(["RÉPARTITION PAR SOCIÉTÉ - TAXI"])
            donnees_rapport.append(["Société", "Nombre de personnes", "Pourcentage"])
            
            total_personnes_taxi = sum(stats['societes_taxi'].values())
            for societe, count in sorted(stats['societes_taxi'].items(), key=lambda x: x[1], reverse=True):
                pourcentage = (count / total_personnes_taxi * 100) if total_personnes_taxi > 0 else 0
                donnees_rapport.append([societe, count, f"{pourcentage:.1f}%"])
        
        # Résumé financier
        donnees_rapport.append([])
        donnees_rapport.append(["RÉSUMÉ FINANCIER"])
        total_chauffeurs_normaux = sum(details['montant_total'] for details in paiements['chauffeurs_normaux'].values())
        total_taxi = sum(details['montant_total'] for details in paiements['chauffeurs_taxi'].values())
        
        donnees_rapport.append([f"Total chauffeurs normaux: {total_chauffeurs_normaux} €"])
        donnees_rapport.append([f"Total taxis: {total_taxi} €"])
        donnees_rapport.append([f"TOTAL GÉNÉRAL: {paiements['total_paiements']} €"])
        
        return pd.DataFrame(donnees_rapport)

    # Les autres méthodes restent similaires mais avec l'ajout du prix dans l'export
    def exporter_suivi_chauffeurs(self, jour_selectionne_export):
        """Exporte le suivi des chauffeurs avec statistiques complètes et prix"""
        if self.df_chauffeurs.empty:
            return None
        
        if jour_selectionne_export == "Tous":
            df_filtre = self.df_chauffeurs
        else:
            df_filtre = self.df_chauffeurs[self.df_chauffeurs['Jour'] == jour_selectionne_export]
        
        if df_filtre.empty:
            return None
        
        # Le reste de la méthode reste similaire mais avec l'ajout des colonnes de prix
        # ... (le code existant de la méthode)
        
        # Ajouter les informations de prix dans l'export
        donnees_export = []
        entete_style = ["Salarié", "HEURE", "CHAUFFEUR", "DESTINATION", "Plateau", "type", "date", "Prix"]
        donnees_export.append(entete_style)
        
        # ... (le reste du code d'export existant)
        
        return pd.DataFrame(donnees_export)

    # Les autres méthodes existantes (traiter_donnees, extraire_heures, etc.) restent inchangées
    # ... (inclure toutes les autres méthodes de la classe précédente)

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
        .warning-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
        }
        .info-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .price-config {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #28a745;
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
        
        # Configuration des prix
        st.header("💰 Configuration des Prix")
        with st.container():
            st.markdown('<div class="price-config">', unsafe_allow_html=True)
            gestion.prix_course_chauffeur = st.number_input(
                "Prix course chauffeur normal (€)", 
                min_value=0.0, 
                value=10.0, 
                step=0.5,
                help="Prix par course pour les chauffeurs normaux"
            )
            gestion.prix_course_taxi = st.number_input(
                "Prix course taxi (€)", 
                min_value=0.0, 
                value=15.0, 
                step=0.5,
                help="Prix par course pour les taxis"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Section gestion des affectations
        st.header("💾 Gestion des Données")
        st.markdown("---")
        
        # Afficher le nombre d'affectations actuelles
        nb_affectations = len(st.session_state.chauffeurs_data)
        st.write(f"**Affectations enregistrées :** {nb_affectations}")
        
        # Indicateur de sauvegarde automatique
        st.info("💾 **Sauvegarde automatique activée**")
        st.write("Les données sont sauvegardées automatiquement")
        
        # Sauvegarde des affectations
        st.subheader("💾 Sauvegarder")
        if nb_affectations > 0:
            if st.button("📥 Sauvegarder les affectations", type="primary"):
                data, nom_fichier = gestion.sauvegarder_affectations()
                st.download_button(
                    label="📥 Télécharger le fichier de sauvegarde",
                    data=data,
                    file_name=nom_fichier,
                    mime="application/vnd.ms-excel"
                )
                st.success(f"✅ {nb_affectations} affectations sauvegardées")
        else:
            st.warning("Aucune affectation à sauvegarder")
        
        # Chargement des affectations
        st.subheader("📂 Charger")
        fichier_sauvegarde = st.file_uploader("Charger une sauvegarde", type=['xlsx'], key="load_file")
        if fichier_sauvegarde:
            if st.button("📤 Charger les affectations", type="secondary"):
                if gestion.charger_affectations(fichier_sauvegarde):
                    st.success("✅ Affectations chargées avec succès")
                    st.rerun()
        
        # Bouton pour supprimer toutes les affectations
        st.subheader("🗑️ Supprimer")
        if nb_affectations > 0:
            if st.button("🗑️ Supprimer TOUTES les affectations", type="secondary"):
                gestion.supprimer_toutes_affectations()
                st.rerun()
        else:
            st.info("Aucune affectation à supprimer")
    
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
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚗 Liste de Ramassage", "🚙 Liste de Départ", "👨‍✈️ Gestion Chauffeurs", "💰 Rapport de Paie", "👤 Gestion Agents"])
        
        with tab1:
            # ... (contenu existant de l'onglet Ramassage)
            pass
        
        with tab2:
            # ... (contenu existant de l'onglet Départ)
            pass
        
        with tab3:
            st.markdown('<h2 class="section-header">👨‍✈️ Gestion des Chauffeurs</h2>', unsafe_allow_html=True)
            
            # Bannière d'information sur la persistance
            if len(st.session_state.chauffeurs_data) > 0:
                st.markdown(f"""
                <div class="info-box">
                💰 <strong>Système de paie des chauffeurs - DONNÉES PERMANENTES</strong><br>
                Les {len(st.session_state.chauffeurs_data)} affectations sont sauvegardées automatiquement.<br>
                <em>Les données restent même après actualisation de la page.</em>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="warning-box">
                💰 <strong>Système de paie des chauffeurs - DONNÉES PERMANENTES</strong><br>
                Les affectations que vous créez sont sauvegardées automatiquement.<br>
                <em>Les données restent même après actualisation de la page.</em>
                </div>
                """, unsafe_allow_html=True)
            
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
                
                # Afficher le prix automatique
                prix_auto = gestion.get_prix_course(chauffeur, type_transport)
                st.info(f"💰 Prix automatique: **{prix_auto} €**")
                
                # Option pour modifier le prix
                prix_personnalise = st.number_input(
                    "Prix personnalisé (optionnel)", 
                    min_value=0.0, 
                    value=prix_auto, 
                    step=0.5,
                    help="Laissez le prix automatique ou modifiez-le"
                )
                
                # Heures selon le type
                if type_transport == "Ramassage":
                    heure = st.selectbox("Heure", ['6h', '7h', '8h', '22h'])
                else:
                    heure = st.selectbox("Heure", ['22h', '23h', '00h', '01h', '02h', '03h'])
                
                jour = st.selectbox("Jour", ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'])
                
                # Afficher la date réelle
                date_reelle = gestion.get_date_du_jour(jour)
                st.info(f"📅 Date réelle de l'affectation: **{date_reelle}**")
                
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
                            # Utiliser le prix personnalisé s'il est différent du prix auto
                            prix_final = prix_personnalise if prix_personnalise != prix_auto else None
                            
                            gestion.ajouter_affectation(chauffeur, heure, agents_selectionnes, type_transport, jour, prix_final)
                            st.success(f"Affectation ajoutée pour {len(agents_selectionnes)} agent(s) avec {chauffeur}")
                            st.rerun()
                        else:
                            st.warning("Veuillez sélectionner un chauffeur, une heure et au moins un agent")
                else:
                    st.warning("Aucun agent disponible pour ces critères")
            
            with col2:
                st.subheader("📋 Affectations en cours")
                
                if not gestion.df_chauffeurs.empty:
                    # Afficher les affectations avec prix
                    for idx, ligne in gestion.df_chauffeurs.iterrows():
                        with st.container():
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                chauffeur_nom = ligne['Chauffeur']
                                badge = "🚕" if "taxi" in chauffeur_nom.lower() else "🚗"
                                st.write(f"{badge} **{chauffeur_nom}** - {ligne['Heure']} - {ligne['Type_Transport']} - {ligne['Jour']}")
                                st.write(f"👤 {ligne['Agent']} | 📍 {ligne['Adresse']} | 📞 {ligne['Telephone']} | 🏢 {ligne['Societe']}")
                                st.write(f"📅 **Date réelle:** {ligne['Date_Reelle']}")
                                st.write(f"💰 **Prix:** {ligne['Prix_Course']} € | **Statut:** {ligne['Statut_Paiement']}")
                                if 'Date_Ajout' in ligne and pd.notna(ligne['Date_Ajout']):
                                    st.caption(f"🕐 Ajouté le: {ligne['Date_Ajout']}")
                            with col_b:
                                if st.button("🗑️", key=f"del_{idx}"):
                                    gestion.supprimer_affectation(idx)
                                    st.rerun()
                            st.divider()
                    
                    # Bouton d'export avec prix
                    st.subheader("📊 Export avec Statistiques et Prix")
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
                        else:
                            st.warning("Aucune donnée à exporter pour les critères sélectionnés")
                
                else:
                    st.info("ℹ️ Aucune affectation de chauffeur enregistrée")
        
        with tab4:
            st.markdown('<h2 class="section-header">💰 Rapport de Paie Mensuel</h2>', unsafe_allow_html=True)
            
            # Sélection du mois et année
            col_mois, col_annee = st.columns(2)
            with col_mois:
                mois_selectionne = st.selectbox("Mois", 
                    list(range(1, 13)), 
                    format_func=lambda x: f"{x} - {['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'][x-1]}",
                    index=datetime.now().month-1)
            
            with col_annee:
                annee_selectionnee = st.selectbox("Année", 
                    list(range(2020, datetime.now().year + 3)),
                    index=datetime.now().year-2020)
            
            # Générer le rapport de paie
            if st.button("💰 Générer le rapport de paie", type="primary"):
                rapport_paie = gestion.generer_rapport_paie_mensuel(mois_selectionne, annee_selectionnee)
                
                if rapport_paie is not None:
                    # Afficher le rapport
                    st.subheader(f"📊 Rapport de Paie - {mois_selectionne}/{annee_selectionnee}")
                    st.dataframe(rapport_paie, use_container_width=True, hide_index=True)
                    
                    # Téléchargement
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        rapport_paie.to_excel(writer, sheet_name=f'Paie_{mois_selectionne}_{annee_selectionnee}', index=False, header=False)
                    
                    st.download_button(
                        label="📥 Télécharger le rapport de paie",
                        data=output.getvalue(),
                        file_name=f"Rapport_Paie_Transport_{mois_selectionne}_{annee_selectionnee}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
                    
                    # Statistiques financières détaillées
                    paiements = gestion.calculer_paiements_mensuels(mois_selectionne, annee_selectionnee)
                    if paiements:
                        st.subheader("💰 Détail des Paiements")
                        
                        col_fin1, col_fin2 = st.columns(2)
                        with col_fin1:
                            st.metric("Total à payer", f"{paiements['total_paiements']} €")
                            st.write("**Chauffeurs normaux:**")
                            for chauffeur, details in sorted(paiements['chauffeurs_normaux'].items(), 
                                                           key=lambda x: x[1]['montant_total'], reverse=True):
                                st.write(f"- {chauffeur}: {details['nb_courses']} courses = {details['montant_total']} €")
                        
                        with col_fin2:
                            total_chauffeurs = sum(details['montant_total'] for details in paiements['chauffeurs_normaux'].values())
                            total_taxis = sum(details['montant_total'] for details in paiements['chauffeurs_taxi'].values())
                            st.metric("Chauffeurs normaux", f"{total_chauffeurs} €")
                            st.metric("Taxis", f"{total_taxis} €")
                            
                            if paiements['chauffeurs_taxi']:
                                st.write("**Taxis:**")
                                for chauffeur, details in sorted(paiements['chauffeurs_taxi'].items(), 
                                                               key=lambda x: x[1]['montant_total'], reverse=True):
                                    st.write(f"- {chauffeur}: {details['nb_courses']} courses = {details['montant_total']} €")
                else:
                    st.warning("Aucune donnée trouvée pour la période sélectionnée")
            
            # Affichage des statistiques globales avec prix
            st.subheader("📊 Statistiques Globales avec Prix")
            if not gestion.df_chauffeurs.empty:
                paiements_globaux = gestion.calculer_paiements_mensuels()
                if paiements_globaux:
                    col_glob1, col_glob2 = st.columns(2)
                    
                    with col_glob1:
                        st.metric("Total courses toutes périodes", paiements_globaux.get('total_courses', 0))
                        st.metric("Chauffeurs normaux", len(paiements_globaux['chauffeurs_normaux']))
                        st.metric("Chauffeurs Taxi", len(paiements_globaux['chauffeurs_taxi']))
                    
                    with col_glob2:
                        st.metric("Total à payer", f"{paiements_globaux['total_paiements']} €")
                        total_chauffeurs_glob = sum(details['montant_total'] for details in paiements_globaux['chauffeurs_normaux'].values())
                        total_taxi_glob = sum(details['montant_total'] for details in paiements_globaux['chauffeurs_taxi'].values())
                        st.metric("Dont chauffeurs normaux", f"{total_chauffeurs_glob} €")
                        st.metric("Dont taxis", f"{total_taxi_glob} €")
            else:
                st.info("Aucune statistique disponible - Ajoutez des affectations d'abord")
        
        with tab5:
            st.markdown('<h2 class="section-header">👤 Gestion des Informations Agents</h2>', unsafe_allow_html=True)
            
            st.info("ℹ️ Ajoutez ou modifiez les informations des agents manquantes dans info.xlsx")
            
            col_ajout, col_liste = st.columns([1, 2])
            
            with col_ajout:
                st.subheader("➕ Ajouter/Modifier un Agent")
                
                # Liste des agents disponibles
                tous_agents = sorted(list(set(gestion.df['Salarie'].tolist()))) if gestion.df is not None else []
                agent_selectionne = st.selectbox("Sélectionner un agent", tous_agents)
                
                if agent_selectionne:
                    # Charger les informations existantes
                    info_existant = gestion.get_info_agent(agent_selectionne)
                    
                    adresse = st.text_input("Adresse", value=info_existant['adresse'] if info_existant['adresse'] != "Adresse non renseignée" else "")
                    telephone = st.text_input("Téléphone", value=info_existant['tel'] if info_existant['tel'] != "Tél non renseigné" else "")
                    societe = st.text_input("Société/Plateau", value=info_existant['societe'] if info_existant['societe'] != "Société non renseignée" else "")
                    
                    if st.button("💾 Sauvegarder les informations", type="primary"):
                        if agent_selectionne:
                            gestion.ajouter_info_agent(agent_selectionne, adresse, telephone, societe)
                            st.success(f"✅ Informations sauvegardées pour {agent_selectionne}")
                            st.rerun()
            
            with col_liste:
                st.subheader("📋 Agents avec informations manquantes")
                
                if gestion.df is not None:
                    agents_manquants = []
                    for agent in gestion.df['Salarie'].unique():
                        info = gestion.get_info_agent(agent)
                        if any([info['adresse'] == "Adresse non renseignée", 
                               info['tel'] == "Tél non renseigné", 
                               info['societe'] == "Société non renseignée"]):
                            agents_manquants.append({
                                'Agent': agent,
                                'Adresse': info['adresse'],
                                'Telephone': info['tel'],
                                'Societe': info['societe']
                            })
                    
                    if agents_manquants:
                        st.write(f"**{len(agents_manquants)} agents avec des informations manquantes:**")
                        df_manquants = pd.DataFrame(agents_manquants)
                        st.dataframe(df_manquants, use_container_width=True)
                    else:
                        st.success("✅ Tous les agents ont des informations complètes")
    
    else:
        st.info("👈 Veuillez sélectionner un fichier Excel dans la barre latérale pour commencer")

if __name__ == "__main__":
    main()
