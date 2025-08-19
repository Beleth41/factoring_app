import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mticker

st.title("Analyse par Adhérent")

mois_fr = {
    'January':'janvier','February':'février','March':'mars','April':'avril',
    'May':'mai','June':'juin','July':'juillet','August':'août',
    'September':'septembre','October':'octobre','November':'novembre','December':'décembre'
}

# Vérifier que les données sont disponibles
if 'df' not in st.session_state or st.session_state.df is None:
    st.warning("Veuillez charger un fichier depuis la page d'accueil.")
    st.stop()

df = st.session_state.df  # Récupérer le DataFrame chargé


# Initialiser la variable
if "client_input" not in st.session_state:
    st.session_state.client_input = ""
if "error_message" not in st.session_state:
    st.session_state.error_message = ""


if st.session_state.df is not None:
    df = st.session_state.df

    ###

if 'Client Number' in df.columns and 'Legal Client Name' in df.columns and 'TIRES' in df.columns:
# Tableau résumé clients avant saisie
    st.subheader("Liste des adhérents")
    clients_summary = (
        df.groupby(['Client Number', 'Legal Client Name'])
        .agg(
            Nb_mouvements=('Client Number', 'size'),
            Nb_Tires_Uniques=('TIRES', 'nunique')
        )
        .reset_index()
        .sort_values(by='Nb_mouvements', ascending=False)
    )
    st.dataframe(clients_summary, use_container_width=True, hide_index=True)

    ###
    ###

    #st.write("Colonnes lues :", df.columns.tolist())

if 'Client Number' in df.columns and 'Legal Client Name' in df.columns:
    # Saisie du numéro de client
    client_input = st.text_input(
        "Entrer le numéro d'adhérent",
        value=st.session_state.client_input,
        key="client_input_box"
    )
        # Stocker la saisie
    st.session_state.client_input = client_input
    if st.button("Afficher les informations de l'adhérent") or client_input:
        
        client_input = st.session_state.client_input.strip()
        if client_input:
            client_number_series = (
                df['Client Number']
                .astype(str)
                .str.strip()
                .str.replace(r'\.0$', '', regex=True)
            )
  
            client_data = df[client_number_series == client_input]
            EntryAmount = client_data.get('EntryAmount', pd.Series(dtype='float'))
            EntryAmountSAC = client_data.get('EntryAmountSAC', pd.Series(dtype='float'))

            if not client_data.empty:
                st.markdown("---")
                st.session_state.error_message = ""
                client_name = client_data['Legal Client Name'].iloc[0]
                st.subheader(f"Adhérent sélectionné : {client_name} (#{client_input})")
                
                # Supprimer l'ancienne colonne d'index
                client_data = client_data.reset_index(drop=True)

                # Afficher sans l'index inutile
                st.dataframe(client_data, use_container_width=True)
###

                if 'EntryAmount' in client_data.columns:
                    # Calculs principaux
                    total_dr = client_data['EntryAmount'].sum()
                    total_cr = client_data['EntryAmountSAC'].sum()
                    total_tx = len(client_data)

                    # Solde d'ouverture
                    opening_balance = client_data.loc[
                        client_data['Transaction'].str.contains("Solde Ouverture", na=False), 
                        'EntryAmount'
                    ].sum()

                    # Solde final
                    final_balance = client_data['solde'].sum()

                    # Creation d'un tableau récapitulatif
                    summary_table = pd.DataFrame({
                        "Rubrique": [
                            "Nombre de mouvements",
                            "Solde d'ouverture",
                            "Total Débits (DR)",
                            "Total Crédits (CR)",
                            "Solde final du client"
                        ],
                        "Valeur": [
                            total_tx,
                            opening_balance,
                            total_dr,
                            total_cr,
                            final_balance
                        ]
                    })

                    # Arrondir et formater comme Excel (espaces pour milliers)
                    summary_table['Valeur'] = summary_table['Valeur'].round(0).astype(int).astype(str)
                    summary_table['Valeur'] = summary_table['Valeur'].str.replace(r"(\d)(?=(\d{3})+$)", r"\1 ", regex=True)

                    # Affichage dans Streamlit
                    st.markdown("---")
                    st.subheader("Résumé des mouvements")
                    st.dataframe(summary_table, use_container_width=True, hide_index=True)




                    # Création du tableau résumé mensuel


                    # Séparation du solde d'ouverture
                    opening_balance = 0
                    if 'Transaction' in client_data.columns:
                        opening_rows = client_data['Transaction'].str.contains("Solde Ouverture", na=False)
                        opening_balance = client_data.loc[opening_rows, 'EntryAmount'].sum()
                        client_data = client_data.loc[~opening_rows]  # Retirer les lignes de solde d'ouverture

                    # Conversion et tri
                    client_data['EntryDate'] = pd.to_datetime(client_data['EntryDate'], dayfirst=True, errors='coerce')
                    client_data = client_data.dropna(subset=['EntryDate']).sort_values('EntryDate')
                    client_data['YearMonth'] = client_data['EntryDate'].dt.to_period('M').dt.to_timestamp()

                    # Période fixe: janvier à juin (2025)
                    start_date = pd.Timestamp('2025-01-01')
                    end_date = pd.Timestamp('2025-06-01')
                    all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
                    base_months_df = pd.DataFrame({'YearMonth': all_months})

                    # Regrouper les montants réels par mois
                    grouped = (
                        client_data.groupby('YearMonth')[['EntryAmount', 'EntryAmountSAC']].sum()
                        .rename(columns={'EntryAmount': 'DR', 'EntryAmountSAC': 'CR'})
                        .reset_index()
                    )

                    # Fusion avec les mois fixes
                    monthly_summary = base_months_df.merge(grouped, on='YearMonth', how='left').fillna(0)

                    # Calcul du solde du mois
                    monthly_summary['SoldeMois'] = 0.0
                    for i in range(len(monthly_summary)):
                        if i == 0:
                            monthly_summary.loc[i, 'SoldeMois'] = opening_balance + monthly_summary.loc[i, 'DR'] - monthly_summary.loc[i, 'CR']
                        else:
                            monthly_summary.loc[i, 'SoldeMois'] = (
                                monthly_summary.loc[i - 1, 'SoldeMois']
                                + monthly_summary.loc[i, 'DR']
                                - monthly_summary.loc[i, 'CR']
                            )

                    # Calcul du Solde cumulé (DR+CR cumulés)
                    monthly_summary['SoldeCumulatif'] = 0.0
                    for i in range(len(monthly_summary)):
                        if i == 0:
                            monthly_summary.loc[i, 'SoldeCumulatif'] = opening_balance + monthly_summary.loc[i, 'DR'] + monthly_summary.loc[i, 'CR']
                        else:
                            monthly_summary.loc[i, 'SoldeCumulatif'] = (
                                monthly_summary.loc[i - 1, 'SoldeCumulatif']
                                + monthly_summary.loc[i, 'DR']
                                + monthly_summary.loc[i, 'CR']
                            )

                    # Ajouter la colonne "Solde initial" (valeur de SoldeMois du mois précédent)
                    monthly_summary['SoldeInitial'] = 0.0
                    for i in range(1, len(monthly_summary)):
                        monthly_summary.loc[i, 'SoldeInitial'] = monthly_summary.loc[i - 1, 'SoldeMois']
                    monthly_summary.loc[0, 'SoldeInitial'] = 0  # ou = opening_balance si voulu

                    # Réorganiser les colonnes pour insérer SoldeInitial avant DR
                    monthly_summary = monthly_summary[['YearMonth', 'SoldeInitial', 'DR', 'CR', 'SoldeMois', 'SoldeCumulatif']]

                    # Ajouter ligne initiale "Solde d'ouverture"
                    monthly_balance = pd.concat([
                        pd.DataFrame([{
                            'YearMonth': pd.NaT,
                            'SoldeInitial': '',
                            'DR': opening_balance,
                            'CR': 0,
                            'SoldeMois': 0,
                            'SoldeCumulatif': opening_balance
                        }]),
                        monthly_summary
                    ], ignore_index=True)

                    # Format affichage
                    mois_fr = {
                        'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril', 'May': 'mai', 'June': 'juin',
                        'July': 'juillet', 'August': 'août', 'September': 'septembre', 'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
                    }

                    display_table = monthly_balance.copy()
                    display_table['YearMonth'] = display_table['YearMonth'].dt.strftime('%B - %Y')
                    display_table['YearMonth'] = display_table['YearMonth'].replace(mois_fr, regex=True).str.lower()
                    display_table['YearMonth'] = display_table['YearMonth'].fillna("solde d'ouverture")
                    display_table.rename(columns={
                        'YearMonth': 'Date',
                        'SoldeInitial': 'Solde initial',
                        'SoldeMois': 'Solde du mois',
                        'SoldeCumulatif': 'Solde cumulé'
                    }, inplace=True)

                    # Formater les montants
                    for col in ['Solde initial', 'DR', 'CR', 'Solde du mois', 'Solde cumulé']:
                        display_table[col] = pd.to_numeric(display_table[col], errors='coerce').fillna(0)
                        display_table[col] = display_table[col].round(0).astype(int).apply(lambda x: f"{x:,}".replace(",", " "))

                    # Affichage final
                    st.markdown("---")
                    st.subheader("Résumé mensuel des mouvements")
                    st.dataframe(display_table, use_container_width=True, hide_index=True)



                    # Préparation des données pour les graphes
                    monthly_balance_plot = monthly_balance.copy()

                    # Ignorer la ligne de solde d'ouverture pour les courbes mensuelles, 
                    # avec récupéreration de sa valeur pour l'afficher dans la première barre
                    opening_balance = monthly_balance_plot.loc[monthly_balance_plot['YearMonth'].isna(), 'DR'].sum()

                    # On ne garde que les mois réels
                    monthly_balance_plot = monthly_balance_plot[monthly_balance_plot['YearMonth'].notna()].reset_index(drop=True)

                    # Conversion pour affichage
                    monthly_balance_plot['YearMonthStr'] = monthly_balance_plot['YearMonth'].dt.strftime('%m-%Y')

                    # Colonnes pour barres empilées
                    monthly_balance_plot['OpeningDR'] = 0
                    monthly_balance_plot['ActualDR'] = monthly_balance_plot['DR']

                    if not monthly_balance_plot.empty:
                        # Ajouter l'ouverture uniquement sur la première barre pour le graphique
                        monthly_balance_plot.loc[0, 'OpeningDR'] = opening_balance

                        # Largeur des barres
                        width = 0.35  

                        # Histogramme DR/CR
                        fig, ax = plt.subplots(figsize=(10, 5))

                        # DR ouverture (vert clair)
                        ax.bar(
                            monthly_balance_plot['YearMonthStr'], 
                            monthly_balance_plot['OpeningDR'], 
                            width, label='Solde Ouverture', color='lightgreen'
                        )
                        # DR normal (vert)
                        ax.bar(
                            monthly_balance_plot['YearMonthStr'], 
                            monthly_balance_plot['ActualDR'], 
                            width, bottom=monthly_balance_plot['OpeningDR'], color='green', label='Débits (DR)'
                        )
                        # CR négatifs (bleu)
                        ax.bar(
                            monthly_balance_plot['YearMonthStr'], 
                            -monthly_balance_plot['CR'], 
                            width, label='Crédits (CR)', color='blue', alpha=0.7
                        )

                        ax.set_title("Histogramme mensuel des mouvements")
                        ax.set_xlabel("Mois")
                        ax.set_ylabel("Montants (Dt)")
                        ax.axhline(0, color='black', linewidth=1.2)
                        ax.legend(
                            loc='upper left',
                            bbox_to_anchor=(1.02, 1),
                            borderaxespad=0
                        )

                        plt.xticks(rotation=45)
                        ax.grid(axis='y', linestyle='--', alpha=0.5)

                        # Formater l’axe Y
                        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

                        st.pyplot(fig)



                        # Graphique linéaire : évolution du solde mensuel et cumulé
                        fig, ax = plt.subplots(figsize=(10, 5))

                        sns.lineplot(
                            data=monthly_balance_plot,
                            x='YearMonthStr',
                            y='SoldeMois',
                            marker='o',
                            linewidth=2,
                            color='green',
                            label='Solde du mois',
                            ax=ax
                        )

                        sns.lineplot(
                            data=monthly_balance_plot,
                            x='YearMonthStr',
                            y='SoldeCumulatif',
                            marker='o',
                            linewidth=2,
                            color='blue',
                            label='Solde cumulé',
                            ax=ax
                        )

                        # Ajouter les valeurs formatées sur les points
                        for i, val in enumerate(monthly_balance_plot['SoldeCumulatif']):
                            ax.text(i, val, f"{int(val):,}".replace(",", " "), ha='center', va='bottom', fontsize=9, color='blue')

                        for i, val in enumerate(monthly_balance_plot['SoldeMois']):
                            ax.text(i, val, f"{int(val):,}".replace(",", " "), ha='center', va='bottom', fontsize=9, color='green')

                        ax.set_title("Évolution mensuelle du solde (mois et cumulé)", fontsize=14)
                        ax.set_xlabel("Mois")
                        ax.set_ylabel("Solde (Dt)")
                        ax.grid(True, linestyle='--', alpha=0.5)

                        # Réduire l’espace avant la première date
                        ax.margins(x=0)             # supprime la marge à gauche/droite
                        ax.set_xlim(-0.1, len(monthly_balance_plot['YearMonthStr'])-1 + 0.1)  # colle la première valeur à l'axe Y

                        ax.legend(
                            loc='upper left',
                            bbox_to_anchor=(1.02, 1),
                            borderaxespad=0
                        )
                        plt.xticks(rotation=45)

                        # Formater l’axe Y avec espaces pour milliers
                        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

                        st.pyplot(fig)


                ####


###
                # Analyse des TIRES
                if 'TIRES' in df.columns and 'Debtor Number' in df.columns:
                    # Récupéreration des données originales du client (non modifiées) pour inclure les SO
                    client_number_series_tires = (
                        df['Client Number']
                        .astype(str)
                        .str.strip()
                        .str.replace(r'\.0$', '', regex=True)
                    )
                    client_data_original_tires = df[client_number_series_tires == client_input].copy()
                    
                    st.markdown("---")
                    st.subheader("Analyse des tirés / Adhérent")

                    # Calcul des stats avec Debtor Number sur les données complètes
                    tires_stats = client_data_original_tires.groupby(['TIRES', 'Debtor Number']).agg(
                        Nombre=('TIRES', 'count'),
                        Total_DR=('EntryAmount', 'sum'),
                        Total_CR=('EntryAmountSAC', 'sum')
                    ).reset_index()

                    tires_stats['Debtor Number'] = tires_stats['Debtor Number'].astype(int).astype(str)

                    # Calculer le Solde Period (Total_DR - Total_CR)
                    tires_stats['Solde_Period'] = tires_stats['Total_DR'] - tires_stats['Total_CR']

                    # Ajouter les pourcentages DR et CR
                    total_dr = tires_stats['Total_DR'].sum()
                    total_cr = tires_stats['Total_CR'].sum()
                    tires_stats['% DR'] = (tires_stats['Total_DR'] / total_dr * 100).round(2)
                    tires_stats['% CR'] = (tires_stats['Total_CR'] / total_cr * 100).round(2)

                    # Calculer le % Solde Period
                    total_solde_period = tires_stats['Solde_Period'].sum()
                    if total_solde_period != 0:
                        tires_stats['% Solde_Period'] = (tires_stats['Solde_Period'] / total_solde_period * 100).round(2)
                    else:
                        tires_stats['% Solde_Period'] = 0

                    # Remplacer NaN par 0
                    tires_stats[['% DR', '% CR', '% Solde_Period']] = tires_stats[['% DR', '% CR', '% Solde_Period']].fillna(0)

                    # Trier par Total_DR + Total_CR décroissant
                    tires_stats['Total'] = tires_stats['Total_DR'] + tires_stats['Total_CR']
                    tires_stats = tires_stats.sort_values(by='Total', ascending=False)

                    # Préparer le tableau final
                    final_tires_table = tires_stats.drop(columns=['Total']).reset_index(drop=True)

                    # Formater les colonnes numériques
                    for col in ['Total_DR', 'Total_CR', 'Solde_Period']:
                        final_tires_table[col] = final_tires_table[col].apply(lambda x: f"{int(x):,}".replace(",", " "))
                    for col in ['% DR', '% CR', '% Solde_Period']:
                        final_tires_table[col] = final_tires_table[col].astype(str) + ' %'

                    # Renommer les colonnes pour l'affichage
                    final_tires_table.rename(columns={
                        'Solde_Period': 'Solde Period',
                        '% Solde_Period': '% Solde Period'
                    }, inplace=True)

                    # Fonction de surlignage : %DR, %CR ou % Solde Period > 25
                    def highlight_over_25(row):
                        try:
                            percent_dr = float(row['% DR'].replace(' %', ''))
                            percent_cr = float(row['% CR'].replace(' %', ''))
                            percent_solde = float(row['% Solde Period'].replace(' %', ''))
                        except:
                            percent_dr, percent_cr, percent_solde = 0, 0, 0

                        colors = [''] * len(row)
                        # Couleur sur la colonne % DR
                        if percent_dr > 25:
                            colors[list(final_tires_table.columns).index('% DR')] = 'background-color: #CF9280'
                        # Couleur sur la colonne % CR
                        if percent_cr > 25:
                            colors[list(final_tires_table.columns).index('% CR')] = 'background-color: #CF9280'
                        # Couleur sur la colonne % Solde Period
                        if abs(percent_solde) > 25:  # Utiliser abs() car le solde peut être négatif
                            colors[list(final_tires_table.columns).index('% Solde Period')] = 'background-color: #CF9280'
                        return colors

                    styled_table = final_tires_table.style.apply(highlight_over_25, axis=1)

                    # Affichage du tableau stylé
                    st.dataframe(styled_table, use_container_width=True, hide_index=True)

                    # Préparation des données pour le graphique
                    tires_stats['Total'] = tires_stats['Total_DR'] + tires_stats['Total_CR']

                    # Trier en ordre décroissant
                    tires_stats = tires_stats.sort_values(by='Total', ascending=False).reset_index(drop=True)

                    # Histogramme horizontal
                    fig, ax = plt.subplots(figsize=(12, max(4, len(tires_stats)*0.5)))  # Hauteur dynamique

                    y = range(len(tires_stats))
                    height = 0.35  # épaisseur des barres

                    # Définir les couleurs en fonction du type de TIRES
                    tires_stats['TIRES'] = tires_stats['TIRES'].astype(str).str.strip().str.upper().str.replace(r'\s+', '', regex=True)


                    dr_colors = ['lightgreen' if tire == 'SO' else 'darkgreen' for tire in tires_stats['TIRES']]
                    cr_colors = ['lightgreen' if tire == 'SO' else 'darkblue' for tire in tires_stats['TIRES']]

                    bars_dr = ax.barh(y, tires_stats['Total_DR'], height, 
                                    label='Débits (DR)', color=dr_colors, edgecolor='black')
                    bars_cr = ax.barh([i + height for i in y], tires_stats['Total_CR'], height, 
                                    label='Crédits (CR)', color=cr_colors, alpha=0.8, edgecolor='black')

                    # Calcul du max pour définir les marges
                    max_val = max(tires_stats['Total_DR'].max(), tires_stats['Total_CR'].max())

                    # Ajouter valeurs formatées sur les barres
                    for bar in bars_dr:
                        width = bar.get_width()
                        ax.text(width + max_val*0.01, 
                                bar.get_y() + bar.get_height()/2,
                                f"{int(width):,}".replace(",", " "),  # Format 10 000
                                va='center', fontsize=9, color='black')

                    for bar in bars_cr:
                        width = bar.get_width()
                        ax.text(width + max_val*0.01, 
                                bar.get_y() + bar.get_height()/2,
                                f"{int(width):,}".replace(",", " "),  # Format 10 000
                                va='center', fontsize=9, color='black')

                    # Ajuster la limite X pour éviter les coupures
                    ax.set_xlim(0, max_val * 1.15)  # 15% de marge à droite pour les labels

                    # Labels et axes
                    ax.set_yticks([i + height/2 for i in y])
                    ax.set_yticklabels(tires_stats['TIRES'])
                    ax.set_xlabel("Montant total (Dt)")
                    ax.set_ylabel("Type de TIRES")
                    ax.set_title("Montants DR et CR par TIRES (incluant SO)")

                    # Légende avec distinction SO
                    from matplotlib.patches import Patch
                    legend_elements = [
                        Patch(facecolor='darkgreen', label='Débits (DR) - Normal'),
                        Patch(facecolor='darkblue', alpha=0.8, label='Crédits (CR) - Normal'),
                        #Patch(facecolor='lightgreen', label='SO (Solde Ouverture)')
                    ]
                    ax.legend(
                        loc='upper left',
                        bbox_to_anchor=(1.02, 1),
                        borderaxespad=0
                    )

                    # Grille verticale
                    ax.grid(axis='x', linestyle='--', alpha=0.5)

                    plt.tight_layout()
                    st.pyplot(fig)




                ### Analyse des catégories RUB
                if 'Client Number' in df.columns and 'Legal Client Name' in df.columns:
                    # Récupérer les données originales du client (non modifiées)
                    client_number_series_rub = (
                        df['Client Number']
                        .astype(str)
                        .str.strip()
                        .str.replace(r'\.0$', '', regex=True)
                    )
                    client_data_original = df[client_number_series_rub == client_input].copy()
                    
                    # Nettoyage des colonnes clés
                    client_data_original['Transaction'] = client_data_original['Transaction'].astype(str).str.strip().fillna("")
                    client_data_original['RUB'] = client_data_original['RUB'].astype(str).str.strip().fillna("")
                    client_data_original['EntryAmount'] = pd.to_numeric(client_data_original['EntryAmount'], errors='coerce').fillna(0)
                    client_data_original['EntryAmountSAC'] = pd.to_numeric(client_data_original['EntryAmountSAC'], errors='coerce').fillna(0)

                    # Identifier la ligne de "Solde Ouverture" (insensible à la casse et nettoyé)
                    so_mask = client_data_original['Transaction'].str.lower().str.contains("solde ouverture", na=False)

                    # Séparer les lignes SO
                    opening_dr = client_data_original.loc[so_mask, 'EntryAmount'].sum()
                    opening_cr = client_data_original.loc[so_mask, 'EntryAmountSAC'].sum()

                    # Nettoyer les données pour le groupby
                    client_data_clean = client_data_original.loc[~so_mask].copy()

                    # Grouper par RUB
                    rub_stats = client_data_clean.groupby('RUB').agg(
                        Nombre=('RUB', 'count'),
                        Total_DR=('EntryAmount', 'sum'),
                        Total_CR=('EntryAmountSAC', 'sum')
                    ).reset_index()

                    # Ajouter la ligne SO en haut
                    rub_stats = pd.concat([
                        pd.DataFrame([{
                            'RUB': 'SO',
                            'Nombre': so_mask.sum(),
                            'Total_DR': opening_dr,
                            'Total_CR': opening_cr
                        }]),
                        rub_stats
                    ], ignore_index=True)

                    # Ordonner la ligne SO en premier
                    rub_stats['ordre'] = rub_stats['RUB'].apply(lambda x: 0 if x == "SO" else 1)
                    rub_stats = rub_stats.sort_values(by=['ordre', 'Total_DR'], ascending=[True, False]).drop(columns=['ordre'])

                    # Formater les valeurs
                    rub_stats_fmt = rub_stats.copy()
                    rub_stats_fmt['Total_DR'] = rub_stats_fmt['Total_DR'].round(0).astype(int).apply(lambda x: f"{x:,}".replace(",", " "))
                    rub_stats_fmt['Total_CR'] = rub_stats_fmt['Total_CR'].round(0).astype(int).apply(lambda x: f"{x:,}".replace(",", " "))

                    # Affichage du tableau
                    st.subheader("Quotas par transaction (RUB)")
                    st.dataframe(rub_stats_fmt, use_container_width=True, hide_index=True)

                    # --- Création du graphique ---
                    rub_stats_plot = rub_stats.copy()  # Pour valeurs numériques
                    fig, ax = plt.subplots(figsize=(12, 5))
                    width = 0.35

                    so_row = rub_stats_plot.iloc[0]
                    rub_stats_others = rub_stats_plot.iloc[1:]

                    x = range(1, len(rub_stats_plot))  # Positions X pour les autres RUB

                    # Barres SO
                    ax.bar([0], [so_row['Total_DR']], width, label='Solde Ouverture (SO)', color='lightgreen', edgecolor='black', linewidth=0.8)

                    # Barres DR/CR
                    bars_dr = ax.bar(x, rub_stats_others['Total_DR'], width, label='Débits (DR)', color='darkgreen', edgecolor='black', linewidth=0.8)
                    bars_cr = ax.bar([i + width for i in x], rub_stats_others['Total_CR'], width, label='Crédits (CR)', color='blue', alpha=0.8, edgecolor='black', linewidth=0.8)

                    # Axe X
                    ax.set_xticks([0 + width/2] + [i + width/2 for i in x])
                    ax.set_xticklabels(rub_stats_plot['RUB'], rotation=0)
                    ax.set_xlabel("Type de RUB")
                    ax.set_ylabel("Montant total (Dt)")
                    ax.set_title("Histogramme Quotas par transaction (RUB)")

                    # Légende
                    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))

                    # Affichage des montants
                    max_val = max(rub_stats_plot['Total_DR'].max(), rub_stats_plot['Total_CR'].max())
                    for bar in ax.containers:
                        for rect in bar:
                            height = rect.get_height()
                            if height > 0:
                                ax.text(rect.get_x() + rect.get_width() / 2, height + 0.01 * max_val,
                                        f"{int(height):,}".replace(",", " "), ha='center', va='bottom', fontsize=9)

                    # Grille
                    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
                    for i in range(len(rub_stats_plot)):
                        ax.axvline(i + 1 - width/2, color='gray', linestyle='--', alpha=0.5)
                    ax.grid(axis='y', linestyle='--', alpha=0.5)

                    plt.tight_layout()
                    st.pyplot(fig)











                ######





            else:
                st.session_state.error_message = "Aucun client trouvé avec ce numéro."
        else:
            st.session_state.error_message = "Veuillez entrer un numéro de client."

    # Affichage des erreurs sans réinitialisation
    if st.session_state.error_message:
        st.error(st.session_state.error_message)

else:
    st.error("Le fichier doit contenir les colonnes 'Client Number' et 'Legal Client Name'.")


