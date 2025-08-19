import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mticker

st.title("Analyse Générale")

if 'df' not in st.session_state or st.session_state.df is None:
    st.warning("Veuillez charger un fichier depuis la page d'accueil.")
    st.stop()

df = st.session_state.df

# --- SECTION 0: APERCU DE LA BASE ---
st.header("Base de données complète")

st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")


# Nettoyage approfondi des noms de colonnes
df.columns = [str(col).strip().replace('\n', '').replace('\r', '') if col is not None else f"Unnamed_{i}" for i, col in enumerate(df.columns)]

# Déterminer le type de base - avec valeur par défaut "alternative" si non défini
base_type = st.session_state.get("base_type", "alternative")

# Debug : afficher les colonnes détectées
with st.expander("Colonnes détectées dans le fichier (cliquez pour voir)"):
    st.write("**Colonnes trouvées :**")
    st.write(df.columns.tolist())
    st.write(f"**Nombre total de colonnes :** {len(df.columns)}")

# Vérification des colonnes pour la base alternative
required_columns = [
    'Transaction Id', 'Accounting Transaction ID', 'AccountTypeBSCode', 'GroupingReference',
    'TransactionType', 'TRANSACTION', 'EntryDate', 'Month No', 'Cal Month Name', 'Year No',
    'Entry Type', 'Entry Amount', 'Entry Amount SAC', 'Solde', 'Service Agreement ID',
    'Client Number', 'Legal Client Name', 'DueDate', 'Document Number', 'Rubrique', 'MVT', 'ledger item id'
]

# Vérification des colonnes - plus flexible
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.warning(f"Certaines colonnes sont manquantes : {', '.join(missing_columns)}")
    st.info("L'analyse continuera avec les colonnes disponibles.")

# Vérifier les colonnes essentielles
essential_columns = ['Entry Amount', 'Entry Amount SAC', 'Client Number', 'Legal Client Name', 'Rubrique']
missing_essential = [col for col in essential_columns if col not in df.columns]

if missing_essential:
    st.error(f"Les colonnes essentielles suivantes sont manquantes : {', '.join(missing_essential)}")
    st.stop()

# --- Conversion des montants ---
df['Entry Amount'] = pd.to_numeric(df['Entry Amount'], errors='coerce').fillna(0)
df['Entry Amount SAC'] = pd.to_numeric(df['Entry Amount SAC'], errors='coerce').fillna(0)

# --- SECTION 1: VUE D'ENSEMBLE ---
st.header("Vue d'ensemble")

# Appliquer du style CSS pour réduire la taille du texte
st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 16px; /* Taille de la valeur */
    }
    [data-testid="stMetricLabel"] {
        font-size: 13px; /* Taille du label */
    }
    </style>
    """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Nombre de clients", f"{df['Client Number'].nunique():,}".replace(",", " "))
col2.metric("Nombre de transactions", f"{len(df):,}".replace(",", " "))
col3.metric("Total Débits", f"{df['Entry Amount'].sum():,.0f}".replace(",", " "))
col4.metric("Total Crédits", f"{df['Entry Amount SAC'].sum():,.0f}".replace(",", " "))


st.markdown("---")

# --- SECTION 2: ANALYSE PAR RUBRIQUE ---
st.header("Analyse par Rubrique")
df['Rubrique'] = df['Rubrique'].astype(str).str.strip().fillna("Non définie")

rubrique_stats = df.groupby('Rubrique').agg(
    Nombre_transactions=('Rubrique', 'count'),
    Total_DR=('Entry Amount', 'sum'),
    Total_CR=('Entry Amount SAC', 'sum'),
    Nombre_clients=('Client Number', 'nunique')
).reset_index()

rubrique_stats['Solde_Net'] = rubrique_stats['Total_DR'] - rubrique_stats['Total_CR']
rubrique_stats = rubrique_stats.sort_values(by='Total_DR', ascending=False)

# Tableau formaté
rubrique_display = rubrique_stats.copy()
for col in ['Total_DR', 'Total_CR', 'Solde_Net']:
    rubrique_display[col] = rubrique_display[col].apply(lambda x: f"{int(x):,}".replace(",", " "))

st.subheader("Statistiques par Rubrique")
st.dataframe(rubrique_display, use_container_width=True, hide_index=True)

# Graphique des rubriques

if len(rubrique_stats) > 0:
    fig, ax = plt.subplots(figsize=(12, max(5, len(rubrique_stats)*0.6)))

    # Position des barres
    x = range(len(rubrique_stats))
    width = 0.4  # largeur des barres

    # Histogramme groupé
    ax.bar([i - width/2 for i in x], rubrique_stats['Total_DR'], 
           width=width, label='Débits (DR)', color='darkgreen', edgecolor='black', alpha=0.8)
    ax.bar([i + width/2 for i in x], rubrique_stats['Total_CR'], 
           width=width, label='Crédits (CR)', color='darkblue', edgecolor='black', alpha=0.8)

    # Titre et labels
    ax.set_xlabel("Rubrique", fontsize=12)
    ax.set_ylabel("Montant (Dt)", fontsize=12)
    ax.set_title("Histogramme Débits vs Crédits par Rubrique", fontsize=14, weight="bold")
    ax.legend()

    # Axe X avec noms des rubriques
    ax.set_xticks(x)
    ax.set_xticklabels(rubrique_stats['Rubrique'], rotation=45, ha='right')

    # Formatter pour espacer les milliers
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda val, _: f"{int(val):,}".replace(",", " "))
    )

    ax.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    st.pyplot(fig)






# --- SECTION 4: ANALYSE PAR TRANSACTION ---
st.markdown("---")
st.header("Analyse par Type de Transaction")

# Vérification que la colonne 'TRANSACTION' existe
if 'TRANSACTION' in df.columns:
    transaction_stats = df.groupby('TRANSACTION').agg(
        Nombre_transactions=('TRANSACTION', 'count'),
        Total_DR=('Entry Amount', 'sum'),
        Total_CR=('Entry Amount SAC', 'sum'),
        Nombre_clients=('Client Number', 'nunique')
    ).reset_index()

    transaction_stats['Solde_Net'] = transaction_stats['Total_DR'] - transaction_stats['Total_CR']
    transaction_stats = transaction_stats.sort_values(by='Total_DR', ascending=False)

    # Tableau formaté
    transaction_display = transaction_stats.copy()
    for col in ['Total_DR', 'Total_CR', 'Solde_Net']:
        transaction_display[col] = transaction_display[col].apply(lambda x: f"{int(x):,}".replace(",", " "))

    st.subheader("Statistiques par Transaction")
    st.dataframe(transaction_display, use_container_width=True, hide_index=True)

    # Graphique
    # Graphique transaction avec échelle log
    # Préparer les données
    transaction_stats['Total_DR_log'] = transaction_stats['Total_DR'].apply(lambda x: x if x>0 else 1)
    transaction_stats['Total_CR_log'] = transaction_stats['Total_CR'].apply(lambda x: x if x>0 else 1)

    fig, ax = plt.subplots(figsize=(14, max(6, len(transaction_stats)*0.5)))
    y = range(len(transaction_stats))
    height = 0.35

    # Barres séparées pour DR et CR
    bars_dr = ax.barh([i + height/2 for i in y], transaction_stats['Total_DR_log'], height=height, color='darkgreen', label='Débits (DR)', edgecolor='black')
    bars_cr = ax.barh([i - height/2 for i in y], transaction_stats['Total_CR_log'], height=height, color='darkblue', alpha=0.8, label='Crédits (CR)', edgecolor='black')

    # Labels à l’extérieur des barres et taille plus grande
    for bar in bars_dr:
        width = bar.get_width()
        ax.text(width*1.05, bar.get_y() + bar.get_height()/2, f"{int(width):,}".replace(",", " "), va='center', fontsize=10)
    for bar in bars_cr:
        width = bar.get_width()
        ax.text(width*1.05, bar.get_y() + bar.get_height()/2, f"{int(width):,}".replace(",", " "), va='center', fontsize=10)

    ax.set_yticks(y)
    ax.set_yticklabels(transaction_stats['TRANSACTION'])
    ax.set_xlabel("Montant (Dt, échelle log)")
    ax.set_title("Montants Débits et Crédits par Type de Transaction")
    ax.set_xscale('log')
    ax.legend()
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    st.pyplot(fig)



else:
    st.warning("Colonne 'TRANSACTION' non trouvée dans le fichier, impossible de faire l'analyse par type de transaction.")


# --- SECTION 4: ANALYSE TEMPORELLE ---
# --- ANALYSE TEMPORELLE (robuste) ---
st.markdown("---")
st.header("Analyse Temporelle")

if 'EntryDate' in df.columns:
    # 1) Nettoyage MONTANTS (gère "33 989", nbsp, virgule décimale)
    for col in ['Entry Amount', 'Entry Amount SAC']:
        df[col] = pd.to_numeric(
            df[col].astype(str)
                  .str.replace('\u00A0', '', regex=False)  # nbsp
                  .str.replace(' ', '')                    # espaces milliers
                  .str.replace(',', '.'),                  # virgule -> point
            errors='coerce'
        ).fillna(0)

    # 2) Conversion DATES (texte + numéro Excel)
    d = pd.to_datetime(df['EntryDate'], dayfirst=True, errors='coerce')

    as_num = pd.to_numeric(df['EntryDate'], errors='coerce')
    mask_excel_serial = d.isna() & as_num.notna()
    # Convertir les "séries Excel" en dates (origine Excel)
    d.loc[mask_excel_serial] = pd.to_datetime(as_num.loc[mask_excel_serial], unit='D', origin='1899-12-30')

    # Filtrer dates aberrantes
    d = d.where((d.dt.year >= 2000) & (d.dt.year <= 2100))

    df_dates = df.copy()
    df_dates['EntryDate'] = d
    df_dates = df_dates.dropna(subset=['EntryDate'])

    if not df_dates.empty:
        # 3) Agrégation mensuelle
        df_dates['YearMonth'] = df_dates['EntryDate'].dt.to_period('M').dt.to_timestamp()
        monthly_stats = (df_dates.groupby('YearMonth', as_index=False)
                                .agg(Nombre_transactions=('EntryDate', 'count'),
                                     Total_DR=('Entry Amount', 'sum'),
                                     Total_CR=('Entry Amount SAC', 'sum')))
        monthly_stats['Solde_Net'] = monthly_stats['Total_DR'] - monthly_stats['Total_CR']
        monthly_stats['YearMonthStr'] = monthly_stats['YearMonth'].dt.strftime('%m-%Y')
        monthly_stats = monthly_stats.sort_values('YearMonth')

        # 4) Graphiques
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Barres DR / CR (CR en négatif pour la lisibilité)
        ax1.bar(monthly_stats['YearMonthStr'], monthly_stats['Total_DR'],
                width=0.4, label='Débits (DR)', color='darkgreen', edgecolor='black')
        ax1.bar(monthly_stats['YearMonthStr'], -monthly_stats['Total_CR'],
                width=0.4, label='Crédits (CR)', color='darkblue', alpha=0.8, edgecolor='black')

        ax1.set_title("Évolution mensuelle des montants")
        ax1.set_ylabel("Montant (Dt)")
        ax1.legend(loc='upper left')
        ax1.grid(axis='y', linestyle='--', alpha=0.5)
        ax1.tick_params(axis='x', rotation=45)
        ax1.axhline(0, color='black', linewidth=1)

        # Courbe du nombre de transactions
        ax2.plot(monthly_stats['YearMonthStr'], monthly_stats['Nombre_transactions'],
                 marker='o', linewidth=2, color='orange', label='Nombre de transactions')
        ax2.set_title("Évolution du nombre de transactions")
        ax2.set_ylabel("Nombre de transactions")
        ax2.set_xlabel("Mois")
        ax2.legend(loc='upper left')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.tick_params(axis='x', rotation=45)

        # Format Y avec séparateur de milliers
        from matplotlib.ticker import FuncFormatter
        ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))

        plt.tight_layout()
        st.pyplot(fig)

        # 5) Tableau mensuel formaté
        monthly_display = monthly_stats[['YearMonthStr', 'Nombre_transactions', 'Total_DR', 'Total_CR', 'Solde_Net']].copy()
        monthly_display.rename(columns={'YearMonthStr': 'Mois'}, inplace=True)
        for col in ['Total_DR', 'Total_CR', 'Solde_Net']:
            monthly_display[col] = (monthly_display[col]
                                    .round(0).astype(int)
                                    .apply(lambda v: f"{v:,}".replace(",", " ")))
        st.subheader("Détail mensuel")
        st.dataframe(monthly_display, use_container_width=True, hide_index=True)
    else:
        st.warning("Aucune date valide après conversion (format texte/Excel).")
else:
    st.warning("Colonne 'EntryDate' non trouvée pour l'analyse temporelle.")


# --- SECTION 3: TOP CLIENTS ---
st.markdown("---")
st.header("Top adhérents")
top_clients = df.groupby(['Client Number', 'Legal Client Name']).agg(
    Nombre_transactions=('Client Number', 'size'),
    Total_DR=('Entry Amount', 'sum'),
    Total_CR=('Entry Amount SAC', 'sum')
).reset_index()

top_clients['Solde_Net'] = top_clients['Total_DR'] - top_clients['Total_CR']
top_clients['Total_Volume'] = top_clients['Total_DR'] + top_clients['Total_CR']
top_clients = top_clients.sort_values(by='Total_Volume', ascending=False).head(15)

top_clients_display = top_clients.copy()
for col in ['Total_DR', 'Total_CR', 'Solde_Net', 'Total_Volume']:
    top_clients_display[col] = top_clients_display[col].apply(lambda x: f"{int(x):,}".replace(",", " "))

st.subheader("Top 15 adhérents par Volume Total")
st.dataframe(top_clients_display, use_container_width=True, hide_index=True)

# Graphique top clients
if len(top_clients) > 0:
    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(top_clients))
    width = 0.35
    bars1 = ax.bar([i - width/2 for i in x], top_clients['Total_DR'], width, label='Débits (DR)', color='darkgreen', edgecolor='black')
    bars2 = ax.bar([i + width/2 for i in x], top_clients['Total_CR'], width, label='Crédits (CR)', color='darkblue', alpha=0.8, edgecolor='black')
    ax.set_xticks(x)
    ax.set_xticklabels([f"{name[:20]}..." if len(name) > 20 else name for name in top_clients['Legal Client Name']], rotation=45, ha='right')
    ax.set_xlabel("Clients")
    ax.set_ylabel("Montant (Dt)")
    ax.set_title("Top 15 Clients - Débits vs Crédits")
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", " ")))
    plt.tight_layout()
    st.pyplot(fig)




# --- SECTION 5: RECHERCHE CLIENT ---
st.markdown("---")
st.header("Recherche Adhérent")
client_input = st.text_input("Entrer le numéro de l'adhérent")

if st.button("Rechercher"):
    if client_input.strip():
        client_series = df['Client Number'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        client_data = df[client_series == client_input.strip()]
        if not client_data.empty:
            client_name = client_data['Legal Client Name'].iloc[0]
            st.success(f"Adhérent trouvé : **{client_name}** (#{client_input.strip()})")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Transactions", len(client_data))
            col2.metric("Total DR", f"{client_data['Entry Amount'].sum():,.0f}".replace(",", " "))
            col3.metric("Total CR", f"{client_data['Entry Amount SAC'].sum():,.0f}".replace(",", " "))
            col4.metric("Solde Net", f"{(client_data['Entry Amount'].sum() - client_data['Entry Amount SAC'].sum()):,.0f}".replace(",", " "))

            st.subheader("Détail des transactions")
            st.dataframe(client_data, use_container_width=True, hide_index=True)

            # --- Analyse par Transaction ---
            st.markdown("---")
            st.subheader("Analyse par Type de Transaction")
            transaction_stats = client_data.groupby('TRANSACTION').agg(
                Total_DR=('Entry Amount', 'sum'),
                Total_CR=('Entry Amount SAC', 'sum')
            ).reset_index()
            transaction_stats['Solde_Net'] = transaction_stats['Total_DR'] - transaction_stats['Total_CR']
            transaction_stats = transaction_stats.sort_values(by='Total_DR', ascending=False)

            # Tableau résumé avec Solde Net
            st.write("Résumé par Transaction")
            transaction_display = transaction_stats.copy()
            for col in ['Total_DR', 'Total_CR', 'Solde_Net']:
                transaction_display[col] = transaction_display[col].apply(lambda x: f"{int(x):,}".replace(",", " "))
            st.dataframe(transaction_display, use_container_width=True, hide_index=True)

            # Graphique log pour équilibrer les valeurs
            transaction_stats['Total_DR_log'] = transaction_stats['Total_DR'].apply(lambda x: x if x>0 else 1)
            transaction_stats['Total_CR_log'] = transaction_stats['Total_CR'].apply(lambda x: x if x>0 else 1)

            fig, ax = plt.subplots(figsize=(12, max(4, len(transaction_stats)*0.5)))
            y = range(len(transaction_stats))
            height = 0.35
            bars_dr = ax.barh([i + height/2 for i in y], transaction_stats['Total_DR_log'], height=height, color='darkgreen', label='Débits (DR)', edgecolor='black')
            bars_cr = ax.barh([i - height/2 for i in y], transaction_stats['Total_CR_log'], height=height, color='darkblue', alpha=0.8, label='Crédits (CR)', edgecolor='black')

            for bar in bars_dr:
                width = bar.get_width()
                ax.text(width*1.05, bar.get_y() + bar.get_height()/2, f"{int(width):,}", va='center', fontsize=10)
            for bar in bars_cr:
                width = bar.get_width()
                ax.text(width*1.05, bar.get_y() + bar.get_height()/2, f"{int(width):,}", va='center', fontsize=10)

            ax.set_yticks(y)
            ax.set_yticklabels(transaction_stats['TRANSACTION'])
            ax.set_xlabel("Montant (Dt, échelle log)")
            ax.set_title("Montants Débits et Crédits par Type de Transaction")
            ax.set_xscale('log')
            ax.legend()
            ax.grid(axis='x', linestyle='--', alpha=0.5)
            plt.tight_layout()
            st.pyplot(fig)


            # --- Analyse par Rubrique ---
            st.markdown("---")
            st.subheader("Analyse par Rubrique")
            client_data['Rubrique'] = client_data['Rubrique'].astype(str).str.strip().fillna("Non définie")
            rubrique_stats = client_data.groupby('Rubrique').agg(
                Total_DR=('Entry Amount', 'sum'),
                Total_CR=('Entry Amount SAC', 'sum')
            ).reset_index()
            rubrique_stats['Solde_Net'] = rubrique_stats['Total_DR'] - rubrique_stats['Total_CR']
            rubrique_stats = rubrique_stats.sort_values(by='Total_DR', ascending=False)

            # Tableau résumé avec Solde Net
            st.write("Résumé par Rubrique")
            rubrique_display = rubrique_stats.copy()
            for col in ['Total_DR', 'Total_CR', 'Solde_Net']:
                rubrique_display[col] = rubrique_display[col].apply(lambda x: f"{int(x):,}".replace(",", " "))
            st.dataframe(rubrique_display, use_container_width=True, hide_index=True)

            fig, ax = plt.subplots(figsize=(12, max(4, len(rubrique_stats)*0.5)))
            y = range(len(rubrique_stats))
            height = 0.35
            bars_dr = ax.barh([i + height/2 for i in y], rubrique_stats['Total_DR'], height=height, color='darkgreen', label='Débits (DR)', edgecolor='black')
            bars_cr = ax.barh([i - height/2 for i in y], rubrique_stats['Total_CR'], height=height, color='darkblue', alpha=0.8, label='Crédits (CR)', edgecolor='black')

            for bar in bars_dr:
                width = bar.get_width()
                ax.text(width*1.05, bar.get_y() + bar.get_height()/2, f"{int(width):,}", va='center', fontsize=10)
            for bar in bars_cr:
                width = bar.get_width()
                ax.text(width*1.05, bar.get_y() + bar.get_height()/2, f"{int(width):,}", va='center', fontsize=10)

            ax.set_yticks(y)
            ax.set_yticklabels(rubrique_stats['Rubrique'])
            ax.set_xlabel("Montant (Dt)")
            ax.set_title("Montants Débits et Crédits par Rubrique")
            ax.legend()
            ax.grid(axis='x', linestyle='--', alpha=0.5)
            plt.tight_layout()
            st.pyplot(fig)


        else:
            st.error("Aucun Adhérent trouvé avec ce numéro.")
    else:
        st.warning("Veuillez entrer un numéro de l'adhérent.")

