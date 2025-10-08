import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime, timedelta
import tempfile
from io import BytesIO
import base64

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
            return {"adresse": "Non renseigné", "tel": "Non renseigné", "societe": "Non renseigné", "voiture": "Non"}
        
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
                        "adresse": str(row.iloc[1]) if len(row) > 1 else "Non renseigné",
                        "tel": str(row.iloc[2]) if len(row) > 2 else "Non renseigné",
                        "societe": str(row.iloc[3]) if len(row) > 3 else "Non renseigné",
                        "voiture": a_voiture
                    }
            
            return {"adresse": "Non renseigné", "tel": "Non renseigné", "societe": "Non renseigné", "voiture": "Non"}
            
        except Exception as e:
            return {"adresse": "Non renseigné", "tel": "Non renseigné", "societe": "Non renseigné", "voiture": "Non"}
    
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
        """Extrait les dates depuis les en-têtes du fichier Excel"""
        try:
            df_entetes = pd.read_excel(file, nrows=2, header=None)
            dates_par_jour = {}
            
            positions_jours = {
                1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 
                5: 'Samedi', 6: 'Dimanche', 7: 'Lundi'
            }
            
            for col_index, jour_nom in positions_jours.items():
                if col_index < len(df_entetes.columns):
                    nom_colonne = str(df_entetes.iloc[0, col_index]) if len(df_entetes) > 0 else ""
                    
                    match = re.search(r'(\d{1,2})/(\d{1,2})', nom_colonne)
                    if match:
                        jour = match.group(1)
                        mois = match.group(2)
                        date_trouvee = self.formater_date_complete(jour, mois)
                        dates_par_jour[jour_nom] = date_trouvee
                    else:
                        dates_par_jour[jour_nom] = self.calculer_date_par_defaut(jour_nom)
            
            return dates_par_jour
            
        except Exception as e:
            return self.generer_dates_par_defaut()
    
    def formater_date_complete(self, jour, mois):
        annee_courante = datetime.now().year
        mois_actuel = datetime.now().month
        
        if int(mois) < mois_actuel:
            annee_courante += 1
        
        jour_format = jour.zfill(2)
        mois_format = mois.zfill(2)
        date_complete = f"{jour_format}/{mois_format}/{annee_courante}"
        
        try:
            datetime.strptime(date_complete, '%d/%m/%Y')
            return date_complete
        except ValueError:
            return self.calculer_date_par_defaut()
    
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
        if pd.isna(planning_str) or planning_str in ['REPOS', 'ABSENCE', 'OFF', 'MALADIE', 'CONGÉ PAYÉ', 'CONGÉ MATERNITÉ']:
            return None, None
        
        texte = str(planning_str)
        heures = re.findall(r'(\d{1,2})h(\d{0,2})', texte)
        
        if len(heures) >= 2:
            heure_debut = int(heures[0][0])
            heure_fin = int(heures[-1][0])
            
            if heure_fin < heure_debut and heure_fin < 12:
                heure_fin += 24
            
            return heure_debut, heure_fin
        
        return None, None
    
    def traiter_donnees(self, heure_ete_active, jour_selectionne, heures_ramassage_selectionnees, heures_depart_selectionnees):
        """Traite les données du fichier Excel"""
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
                    if heure_ete_active:
                        heure_debut_ajustee = self.ajuster_heure_ete(heure_debut, heure_ete_active)
                        heure_fin_ajustee = self.ajuster_heure_ete(heure_fin, heure_ete_active)
                    else:
                        heure_debut_ajustee = heure_debut
                        heure_fin_ajustee = heure_fin
                    
                    # RAMASSAGE
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
                    
                    # DÉPART
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
        
        self.liste_ramassage_actuelle.sort(key=lambda x: (x['Jour'], x['Heure']))
        self.liste_depart_actuelle.sort(key=lambda x: (x['Jour'], x['Heure']))
    
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
    
    def exporter_suivi_chauffeurs(self, jour_selectionne_export):
        """Exporte le suivi des chauffeurs avec le nouveau format"""
        if self.df_chauffeurs.empty:
            return None
        
        if jour_selectionne_export == "Tous":
            df_filtre = self.df_chauffeurs
        else:
            df_filtre = self.df_chauffeurs[self.df_chauffeurs['Jour'] == jour_selectionne_export]
        
        if df_filtre.empty:
            return None
        
        donnees_export = []
        entete = ["Salarié", "HEURE", "CHAUFFEUR", "DESTINATION", "Plateau", "type", "date"]
        donnees_export.append(entete)
        donnees_export.append(["", "", "", "", "", "", ""])
        
        groupes = df_filtre.groupby(['Jour', 'Chauffeur', 'Heure', 'Type_Transport'])
        total_courses = 0
        statistiques_societes = {}
        
        groupes_tries = sorted(groupes, key=lambda x: (
            datetime.strptime(self.get_date_du_jour(x[0][0]), '%d/%m/%Y'),
            x[0][0], x[0][1], x[0][2]
        ))
        
        for (jour, chauffeur, heure, type_transport), groupe in groupes_tries:
            date_groupe = self.get_date_du_jour(jour)
            nb_personnes_course = len(groupe)
            societes_course = {}
            
            for idx, (_, ligne) in enumerate(groupe.iterrows()):
                societe = ligne['Societe']
                if societe not in societes_course:
                    societes_course[societe] = 0
                societes_course[societe] += 1
                
                if societe not in statistiques_societes:
                    statistiques_societes[societe] = 0
                statistiques_societes[societe] += 1
                
                donnees_export.append([
                    ligne['Agent'], f"{heure}", chauffeur, ligne['Adresse'],
                    societe, type_transport.lower(), date_groupe
                ])
            
            if societes_course:
                pourcentages = []
                for societe, count in societes_course.items():
                    pourcentage = (count / nb_personnes_course) * 100
                    pourcentages.append(f"{pourcentage:.0f}% {societe}")
                
                texte_pourcentages = " + ".join(pourcentages)
                donnees_export.append([
                    f"RÉPARTITION COURSE", "", "", texte_pourcentages, "", "", ""
                ])
            
            total_courses += 1
            donnees_export.append(["", "", "", "", "", "", ""])
        
        # Ajouter les statistiques globales
        total_personnes = sum(statistiques_societes.values())
        if total_personnes > 0:
            donnees_export.append(["STATISTIQUES GLOBALES PAR SOCIÉTÉ", "", "", "", "", "", ""])
            for societe, count in sorted(statistiques_societes.items(), key=lambda x: x[1], reverse=True):
                pourcentage_global = (count / total_personnes) * 100
                donnees_export.append([
                    "", "", "", f"{societe}: {count} personnes ({pourcentage_global:.1f}%)", "", "", ""
                ])
        
        return pd.DataFrame(donnees_export)

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
                gestion.df = pd.read_excel(uploaded_file, skiprows=2)
                gestion.df.columns = ['Salarie', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Lundi', 'Qualification']
                gestion.dates_par_jour = gestion.extraire_dates_des_entetes(uploaded_file)
                
                st.success(f"✅ {uploaded_file.name} chargé")
                
                # Afficher les dates détectées
                with st.expander("📅 Dates détectées"):
                    for jour, date in gestion.dates_par_jour.items():
                        st.write(f"**{jour}**: {date}")
                        
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
            heure_6h = st.checkbox("6h", value=True)
            heure_7h = st.checkbox("7h", value=True)
            heure_8h = st.checkbox("8h", value=True)
            heure_22h = st.checkbox("22h", value=True)
        
        with col2:
            st.subheader("🚙 Départ")
            heure_22h_d = st.checkbox("22h ", value=True)
            heure_23h = st.checkbox("23h", value=True)
            heure_00h = st.checkbox("00h", value=True)
            heure_01h = st.checkbox("01h", value=True)
            heure_02h = st.checkbox("02h", value=True)
            heure_03h = st.checkbox("03h", value=True)
    
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
            
            if gestion.liste_ramassage_actuelle:
                mode_heure = "HEURE D'ÉTÉ" if heure_ete_active else "HEURE NORMALE"
                st.write(f"**Mode:** {mode_heure} | **Jours:** {jour_selectionne} | **Heures:** {', '.join([f'{h}h' for h in heures_ramassage])}")
                
                # Afficher par jour
                jours_affiches = set()
                for agent in gestion.liste_ramassage_actuelle:
                    if agent['Jour'] not in jours_affiches:
                        jours_affiches.add(agent['Jour'])
                        date_jour = gestion.get_date_du_jour(agent['Jour'])
                        st.subheader(f"📅 {agent['Jour']} ({date_jour})")
                        
                        # Créer un DataFrame pour ce jour
                        agents_du_jour = [a for a in gestion.liste_ramassage_actuelle if a['Jour'] == agent['Jour']]
                        df_affiche = pd.DataFrame(agents_du_jour)[['Agent', 'Heure_affichage', 'Adresse', 'Telephone', 'Societe']]
                        st.dataframe(df_affiche, use_container_width=True)
            else:
                st.info("ℹ️ Aucun agent trouvé avec les filtres sélectionnés")
        
        with tab2:
            st.markdown('<h2 class="section-header">📋 Liste de Départ</h2>', unsafe_allow_html=True)
            
            if gestion.liste_depart_actuelle:
                mode_heure = "HEURE D'ÉTÉ" if heure_ete_active else "HEURE NORMALE"
                st.write(f"**Mode:** {mode_heure} | **Jours:** {jour_selectionne} | **Heures:** {', '.join([f'{h}h' for h in heures_depart])}")
                
                # Afficher par jour
                jours_affiches = set()
                for agent in gestion.liste_depart_actuelle:
                    if agent['Jour'] not in jours_affiches:
                        jours_affiches.add(agent['Jour'])
                        date_jour = gestion.get_date_du_jour(agent['Jour'])
                        st.subheader(f"📅 {agent['Jour']} ({date_jour})")
                        
                        # Créer un DataFrame pour ce jour
                        agents_du_jour = [a for a in gestion.liste_depart_actuelle if a['Jour'] == agent['Jour']]
                        df_affiche = pd.DataFrame(agents_du_jour)[['Agent', 'Heure_affichage', 'Adresse', 'Telephone', 'Societe']]
                        st.dataframe(df_affiche, use_container_width=True)
            else:
                st.info("ℹ️ Aucun agent trouvé avec les filtres sélectionnés")
        
        with tab3:
            st.markdown('<h2 class="section-header">👨‍✈️ Gestion des Chauffeurs</h2>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("➕ Ajouter une affectation")
                
                # Liste des chauffeurs
                chauffeurs_liste = gestion.get_liste_chauffeurs_voitures()
                noms_chauffeurs = [ch['chauffeur'] for ch in chauffeurs_liste] if chauffeurs_liste else ["Aucun chauffeur trouvé"]
                
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
                                st.write(f"**{ligne['Chauffeur']}** - {ligne['Heure']} - {ligne['Type_Transport']} - {ligne['Jour']}")
                                st.write(f"👤 {ligne['Agent']} | 📍 {ligne['Adresse']} | 📞 {ligne['Telephone']} | 🏢 {ligne['Societe']}")
                            with col_b:
                                if st.button("🗑️", key=f"del_{idx}"):
                                    gestion.supprimer_affectation(idx)
                                    st.rerun()
                            st.divider()
                    
                    # Bouton d'export
                    st.subheader("📊 Export")
                    jour_export = st.selectbox("Jour à exporter", ['Tous', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'])
                    
                    if st.button("💾 Exporter le suivi des chauffeurs"):
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
                                file_name=f"Suivi_Chauffeurs_{datetime.now().strftime('%d%m%Y')}.xlsx",
                                mime="application/vnd.ms-excel"
                            )
                        else:
                            st.warning("Aucune donnée à exporter pour les critères sélectionnés")
                
                else:
                    st.info("ℹ️ Aucune affectation de chauffeur enregistrée")
    
    else:
        st.info("👈 Veuillez sélectionner un fichier Excel dans la barre latérale pour commencer")

if __name__ == "__main__":
    main()