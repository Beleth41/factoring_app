import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns


st.title("Analyse par tiré")

mois_fr = {
    'January':'janvier','February':'février','March':'mars','April':'avril',
    'May':'mai','June':'juin','July':'juillet','August':'août',
    'September':'septembre','October':'octobre','November':'novembre','December':'décembre'
}

# --- Vérification session ---
if "df" not in st.session_state or st.session_state.df is None:
    st.warning("Veuillez charger un fichier depuis la page d'accueil.")
    st.stop()
 
client_data = st.session_state.df



if 'TIRES' in client_data.columns and 'Debtor Number' in client_data.columns and 'Legal Client Name' in client_data.columns:
    st.subheader("Liste des tirés / Mouvements / Adhérents")

    # Comptage des occurrences + nombre unique de clients
    tires_count = (
        client_data.groupby(['TIRES', 'Debtor Number'])
        .agg(
            Nb_mouvements=('TIRES', 'size'),
            Nombre_clients_uniques=('Legal Client Name', 'nunique')
        )
        .reset_index()
        .sort_values(by='Nb_mouvements', ascending=False)
        .reset_index(drop=True)
    )

    st.dataframe(tires_count, use_container_width=True, hide_index=True)


    st.markdown("---")
    st.subheader("Recherche et analyse d'un tiré")

    # debtor_input = st.text_input("Saisir un Debtor Number exact")

    
    
    # Initialiser la valeur dans session_state si elle n'existe pas
    if "debtor_input" not in st.session_state:
        st.session_state.debtor_input = ""

    # Champ texte avec sauvegarde
    debtor_input = st.text_input(
        "Entrer le Debtor Number",
        value=st.session_state.debtor_input,
        key="debtor_input_box"
    )

    # Mettre à jour session_state à chaque changement
    st.session_state.debtor_input = debtor_input.strip()

    # Bouton ou appui sur Entrer
    if st.button("Analyser ce tiré") or st.session_state.debtor_input != "":
        if debtor_input.strip() == "":
            st.warning("Veuillez entrer un Debtor Number.")
        else:
            # Convertir en string propre sans .0
            debtor_series = (
                client_data['Debtor Number']
                .astype(str)
                .str.strip()
                .str.replace(r'\.0$', '', regex=True)
            )
            tire_data = client_data[debtor_series == debtor_input]

            ### vars
            EntryAmount = tire_data.get('EntryAmount', pd.Series(dtype='float'))
            EntryAmountSAC = tire_data.get('EntryAmountSAC', pd.Series(dtype='float'))

            ###vars start

            if tire_data.empty:
                st.error(f"Aucune donnée trouvée pour le Debtor Number {debtor_input}.")
            else:
                tire_name = tire_data['TIRES'].iloc[0]
                st.success(f"{len(tire_data)} transactions trouvées pour le tire '{tire_name}' avec le Debtor Number {debtor_input}")
                st.dataframe(tire_data, use_container_width=True, hide_index=True)




                

                # --- Préparation pour analyse ---
        if 'EntryAmount' in tire_data.columns and 'EntryAmountSAC' in tire_data.columns:
            tire_data['EntryAmount'] = pd.to_numeric(tire_data['EntryAmount'], errors='coerce').fillna(0)
            tire_data['EntryAmountSAC'] = pd.to_numeric(tire_data['EntryAmountSAC'], errors='coerce').fillna(0)

            # --- Résumé DR/CR ---
            total_dr = tire_data['EntryAmount'].sum()
            total_cr = tire_data['EntryAmountSAC'].sum()
            solde = total_dr - total_cr

            st.markdown("### Résumé financier")

            # Calcul du solde d'ouverture
            opening_balance = 0
            if 'Transaction' in tire_data.columns:
                opening_balance = tire_data.loc[
                    tire_data['Transaction'].astype(str).str.contains("Solde Ouverture", na=False),
                    'EntryAmount'
                ].sum() 

            st.write(f"**Nombre de mouvements** : {len(tire_data)}".replace(",", " "))
            st.write(f"**Solde d'ouverture** : {opening_balance:,.0f}".replace(",", " "))
            st.write(f"**Total Débits (DR)** : {total_dr:,.0f}".replace(",", " "))
            st.write(f"**Total Crédits (CR)** : {total_cr:,.0f}".replace(",", " "))
            st.write(f"**Solde final (DR-CR)** : {solde:,.0f}".replace(",", " "))


            # --- Histogramme des transactions dans le temps ---
            # --- Séparation du solde d'ouverture ---
            opening_balance = 0
            if 'Transaction' in tire_data.columns:
                opening_rows = tire_data['Transaction'].str.contains("Solde Ouverture", na=False)
                opening_balance = tire_data.loc[opening_rows, 'EntryAmount'].sum()
                tire_data = tire_data.loc[~opening_rows]

            # --- Conversion et tri ---
            tire_data['EntryDate'] = pd.to_datetime(tire_data['EntryDate'], dayfirst=True, errors='coerce')
            tire_data = tire_data.dropna(subset=['EntryDate']).sort_values('EntryDate')
            tire_data['YearMonth'] = tire_data['EntryDate'].dt.to_period('M').dt.to_timestamp()

            # --- Période fixe : janvier à juin 2025 ---
            start_date = pd.Timestamp('2025-01-01')
            end_date = pd.Timestamp('2025-06-01')
            all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
            base_months_df = pd.DataFrame({'YearMonth': all_months})

            # --- Regroupement des montants réels par mois ---
            grouped = (
                tire_data.groupby('YearMonth')[['EntryAmount', 'EntryAmountSAC']].sum()
                .rename(columns={'EntryAmount': 'DR', 'EntryAmountSAC': 'CR'})
                .reset_index()
            )

            # --- Fusion avec tous les mois ---
            monthly_summary = base_months_df.merge(grouped, on='YearMonth', how='left').fillna(0)

            # --- Calcul du Solde du mois (progressif) ---
            monthly_summary['SoldeMois'] = 0.0
            if len(monthly_summary) > 0:
                monthly_summary.loc[0, 'SoldeMois'] = opening_balance + monthly_summary.loc[0, 'DR'] - monthly_summary.loc[0, 'CR']
                for i in range(1, len(monthly_summary)):
                    monthly_summary.loc[i, 'SoldeMois'] = (
                        monthly_summary.loc[i - 1, 'SoldeMois']
                        + monthly_summary.loc[i, 'DR']
                        - monthly_summary.loc[i, 'CR']
                    )

            # --- Calcul du Solde cumulé (DR + CR cumulés) ---
            monthly_summary['SoldeCumulatif'] = 0.0
            if len(monthly_summary) > 0:
                monthly_summary.loc[0, 'SoldeCumulatif'] = opening_balance + monthly_summary.loc[0, 'DR'] + monthly_summary.loc[0, 'CR']
                for i in range(1, len(monthly_summary)):
                    monthly_summary.loc[i, 'SoldeCumulatif'] = (
                        monthly_summary.loc[i - 1, 'SoldeCumulatif']
                        + monthly_summary.loc[i, 'DR']
                        + monthly_summary.loc[i, 'CR']
                    )

            # --- Ajouter ligne initiale "Solde d'ouverture" ---
            monthly_balance = pd.concat([
                pd.DataFrame([{
                    'YearMonth': pd.NaT,
                    'DR': opening_balance,
                    'CR': 0,
                    'SoldeMois': 0,
                    'SoldeCumulatif': opening_balance
                }]),
                monthly_summary[['YearMonth', 'DR', 'CR', 'SoldeMois', 'SoldeCumulatif']]
            ], ignore_index=True)

            # --- Format du tableau ---
            mois_fr = {
                'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril', 'May': 'mai', 'June': 'juin',
                'July': 'juillet', 'August': 'août', 'September': 'septembre', 'October': 'octobre',
                'November': 'novembre', 'December': 'décembre'
            }

            display_table = monthly_balance.copy()
            display_table['YearMonth'] = display_table['YearMonth'].dt.strftime('%B - %Y')
            display_table['YearMonth'] = display_table['YearMonth'].replace(mois_fr, regex=True).str.lower()
            display_table['YearMonth'] = display_table['YearMonth'].fillna("solde d'ouverture")
            display_table.rename(columns={
                'YearMonth': 'Date',
                'SoldeMois': 'Solde du mois',
                'SoldeCumulatif': 'Solde cumulé'
            }, inplace=True)

            # --- Formater les colonnes en "10 000" ---
            for col in ['DR', 'CR', 'Solde du mois', 'Solde cumulé']:
                display_table[col] = display_table[col].round(0).astype(int).apply(lambda x: f"{x:,}".replace(",", " "))

            st.markdown("---")
            st.subheader("Résumé mensuel des mouvements")
            st.dataframe(display_table, use_container_width=True, hide_index=True)




            # --- Création des colonnes pour l'histogramme empilé ---
            monthly_summary['OpeningDR'] = 0
            monthly_summary['ActualDR'] = monthly_summary['DR']

            if len(monthly_summary) > 0:
                # On place le solde d'ouverture uniquement dans le premier mois
                monthly_summary.loc[0, 'OpeningDR'] = opening_balance
                monthly_summary.loc[0, 'ActualDR'] = max(monthly_summary.loc[0, 'DR'], 0)

            # Colonne formatée pour l’axe X
            monthly_summary['YearMonthStr'] = monthly_summary['YearMonth'].dt.strftime('%m - %Y')

            # --- Histogramme DR/CR ---
            st.markdown("### Histogramme mensuel des mouvements")
            fig, ax = plt.subplots(figsize=(12, 5))
            width = 0.35  # largeur des barres

            # DR ouverture (vert clair)
            ax.bar(
                monthly_summary['YearMonthStr'],
                monthly_summary['OpeningDR'],
                width,
                label='Solde Ouverture',
                color='lightgreen'
            )

            # DR normal (vert foncé, empilé sur le SO)
            ax.bar(
                monthly_summary['YearMonthStr'],
                monthly_summary['ActualDR'],
                width,
                bottom=monthly_summary['OpeningDR'],
                color='green',
                label='Débits (DR)'
            )

            # CR négatif (bleu)
            ax.bar(
                monthly_summary['YearMonthStr'],
                -monthly_summary['CR'],
                width,
                label='Crédits (CR)',
                color='blue',
                alpha=0.7
            )

            ax.set_title("Histogramme mensuel des mouvements", fontsize=14)
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

            # Axe Y formaté avec séparateurs de milliers
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

            st.pyplot(fig)




            # --- Graphique linéaire Solde Mensuel & Cumulatif ---
            st.markdown("### Évolution mensuelle du solde")
            monthly_plot = monthly_balance[monthly_balance['YearMonth'].notna()].reset_index(drop=True)
            monthly_plot['YearMonthStr'] = monthly_plot['YearMonth'].dt.strftime('%m-%Y')

            fig, ax = plt.subplots(figsize=(10, 5))

            sns.lineplot(
                data=monthly_plot,
                x='YearMonthStr',
                y='SoldeMois',
                marker='o',
                linewidth=2,
                color='green',
                label='Solde du mois',
                ax=ax
            )

            sns.lineplot(
                data=monthly_plot,
                x='YearMonthStr',
                y='SoldeCumulatif',
                marker='o',
                linewidth=2,
                color='blue',
                label='Solde cumulé',
                ax=ax
            )

            # Ajouter les valeurs sur le graphique
            for i, val in enumerate(monthly_plot['SoldeCumulatif']):
                ax.text(i, val, f"{int(val):,}".replace(",", " "), ha='center', va='bottom', fontsize=9, color='blue')

            for i, val in enumerate(monthly_plot['SoldeMois']):
                ax.text(i, val, f"{int(val):,}".replace(",", " "), ha='center', va='bottom', fontsize=9, color='green')

            ax.set_title("Évolution mensuelle du solde (mois et cumulé)", fontsize=14)
            ax.set_xlabel("Mois")
            ax.set_ylabel("Solde (Dt)")
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.legend(
                loc='upper left',
                bbox_to_anchor=(1.02, 1),
                borderaxespad=0
            )
            plt.xticks(rotation=45)

            # Axe Y formaté
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

            st.pyplot(fig)


# --- Ici tu peux insérer le bloc Tableau + Histogramme + Graphique linéaire ---



                ###
        else:
            st.warning("Colonnes de montants absentes pour l'analyse financière.")

        ###clients
        if not tire_data.empty:
            if all(col in tire_data.columns for col in ['Client Number', 'Legal Client Name', 'EntryAmount', 'EntryAmountSAC']):
                st.markdown("---")
                st.markdown("### Liste d'adhérents associés à ce tiré")

                # Agréger nombre d'occurrences, total DR et total CR par client
                clients_summary = (
                    tire_data.groupby(['Client Number', 'Legal Client Name'])
                    .agg(
                        Nb_mouvements=('Client Number', 'size'),
                        Total_DR=('EntryAmount', 'sum'),
                        Total_CR=('EntryAmountSAC', 'sum')
                    )
                    .reset_index()
                    .sort_values(by='Nb_mouvements', ascending=False)
                )

                # Formater les valeurs numériques avec espace comme séparateur de milliers
                clients_summary['Nb_mouvements'] = clients_summary['Nb_mouvements'].apply(lambda x: f"{x:,}".replace(",", " "))
                clients_summary['Total_DR'] = clients_summary['Total_DR'].apply(lambda x: f"{int(x):,}".replace(",", " "))
                clients_summary['Total_CR'] = clients_summary['Total_CR'].apply(lambda x: f"{int(x):,}".replace(",", " "))

                st.dataframe(clients_summary, use_container_width=True, hide_index=True)
            else:
                st.info("Colonnes nécessaires (Client Number, Legal Client Name, EntryAmount, EntryAmountSAC) absentes pour afficher les clients associés.")

        
        # Graphique DR/CR par client
        st.markdown("### Histogramme DR/CR par adhérent")

        # Reconvertir en numérique pour le graphique
        clients_summary_plot = tire_data.groupby(['Client Number', 'Legal Client Name']) \
            .agg(Total_DR=('EntryAmount', 'sum'), Total_CR=('EntryAmountSAC', 'sum')) \
            .reset_index() \
            .sort_values(by='Total_DR', ascending=False)

        fig, ax = plt.subplots(figsize=(12, max(4, len(clients_summary_plot) * 0.4)))

        y = range(len(clients_summary_plot))
        height = 0.35

        bars_dr = ax.barh(y, clients_summary_plot['Total_DR'], height,
                        label='Débits (DR)', color='darkgreen', edgecolor='black')
        bars_cr = ax.barh([i + height for i in y], clients_summary_plot['Total_CR'], height,
                        label='Crédits (CR)', color='darkblue', alpha=0.8, edgecolor='black')

        # Ajouter les valeurs sur les barres
        for bar in bars_dr:
            width = bar.get_width()
            ax.text(width + (clients_summary_plot['Total_DR'].max() * 0.01),
                    bar.get_y() + bar.get_height() / 2,
                    f"{int(width):,}".replace(",", " "),
                    va='center', fontsize=9, color='black')

        for bar in bars_cr:
            width = bar.get_width()
            ax.text(width + (clients_summary_plot['Total_DR'].max() * 0.01),
                    bar.get_y() + bar.get_height() / 2,
                    f"{int(width):,}".replace(",", " "),
                    va='center', fontsize=9, color='black')

        ax.set_yticks([i + height / 2 for i in y])
        ax.set_yticklabels(clients_summary_plot['Legal Client Name'])
        ax.set_xlabel("Montant total (Dt)")
        ax.set_ylabel("adhérents")
        ax.set_title("Montants DR et CR par adhérent")

        # Format des nombres de l'axe X avec espaces
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

        ax.legend(
            loc='upper left',
            bbox_to_anchor=(1.02, 1),
            borderaxespad=0
        )
        ax.grid(axis='x', linestyle='--', alpha=0.5)

        plt.tight_layout()
        st.pyplot(fig)


        ### Analyse RUB (transactions RUB)
        if 'Debtor Number' in client_data.columns and 'RUB' in client_data.columns:
            # Récupérer les données originales du tiré (non modifiées)
            debtor_series_clean = (
                client_data['Debtor Number']
                .astype(str)
                .str.strip()
                .str.replace(r'\.0$', '', regex=True)
            )
            tire_data_original = client_data[debtor_series_clean == debtor_input].copy()

            # Nettoyage des colonnes clés
            tire_data_original['Transaction'] = tire_data_original['Transaction'].astype(str).str.strip().fillna("")
            tire_data_original['RUB'] = tire_data_original['RUB'].astype(str).str.strip().fillna("")
            tire_data_original['EntryAmount'] = pd.to_numeric(tire_data_original['EntryAmount'], errors='coerce').fillna(0)
            tire_data_original['EntryAmountSAC'] = pd.to_numeric(tire_data_original['EntryAmountSAC'], errors='coerce').fillna(0)

            # Identifier la ligne de "Solde Ouverture"
            so_mask = tire_data_original['Transaction'].str.lower().str.contains("solde ouverture", na=False)

            # Séparer les lignes SO
            opening_dr = tire_data_original.loc[so_mask, 'EntryAmount'].sum()
            opening_cr = tire_data_original.loc[so_mask, 'EntryAmountSAC'].sum()

            # Nettoyer pour groupby
            tire_data_clean = tire_data_original.loc[~so_mask].copy()

            # Grouper par RUB
            rub_stats = tire_data_clean.groupby('RUB').agg(
                Nombre=('RUB', 'count'),
                Total_DR=('EntryAmount', 'sum'),
                Total_CR=('EntryAmountSAC', 'sum')
            ).reset_index()

            # Ajouter la ligne SO
            rub_stats = pd.concat([
                pd.DataFrame([{
                    'RUB': 'SO',
                    'Nombre': so_mask.sum(),
                    'Total_DR': opening_dr,
                    'Total_CR': opening_cr
                }]),
                rub_stats
            ], ignore_index=True)

            # Trier : SO en premier
            rub_stats['ordre'] = rub_stats['RUB'].apply(lambda x: 0 if x == "SO" else 1)
            rub_stats = rub_stats.sort_values(by=['ordre', 'Total_DR'], ascending=[True, False]).drop(columns=['ordre'])

            # Formater pour affichage
            rub_stats_fmt = rub_stats.copy()
            rub_stats_fmt['Total_DR'] = rub_stats_fmt['Total_DR'].round(0).astype(int).apply(lambda x: f"{x:,}".replace(",", " "))
            rub_stats_fmt['Total_CR'] = rub_stats_fmt['Total_CR'].round(0).astype(int).apply(lambda x: f"{x:,}".replace(",", " "))

            # --- Affichage du tableau ---
            st.markdown("---")
            st.subheader("Quotas par transaction (RUB)")
            st.dataframe(rub_stats_fmt, use_container_width=True, hide_index=True)

            # --- Création du graphique ---
            rub_stats_plot = rub_stats.copy()
            fig, ax = plt.subplots(figsize=(12, 5))
            width = 0.35

            so_row = rub_stats_plot.iloc[0]
            rub_stats_others = rub_stats_plot.iloc[1:]
            x = range(1, len(rub_stats_plot))

            # Barres SO
            ax.bar([0], [so_row['Total_DR']], width, label='Solde Ouverture (SO)', color='lightgreen', edgecolor='black', linewidth=0.8)

            # Barres DR et CR
            ax.bar(x, rub_stats_others['Total_DR'], width, label='Débits (DR)', color='darkgreen', edgecolor='black', linewidth=0.8)
            ax.bar([i + width for i in x], rub_stats_others['Total_CR'], width, label='Crédits (CR)', color='blue', alpha=0.8, edgecolor='black', linewidth=0.8)

            # Axe X
            ax.set_xticks([0 + width/2] + [i + width/2 for i in x])
            ax.set_xticklabels(rub_stats_plot['RUB'], rotation=0)
            ax.set_xlabel("Type de RUB")
            ax.set_ylabel("Montant total (Dt)")
            ax.set_title("Histogramme Quotas par transaction (RUB)")

            # Légende à l'extérieur
            ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))

            # Montants au-dessus des barres
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
            




else:
    st.error("Les colonnes 'TIRES' et/ou 'Debtor Number' sont introuvables dans votre fichier.")
