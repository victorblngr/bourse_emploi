# Ensure required libraries are installed
try:
    import plotly.express as px
except ImportError:
    subprocess.check_call(["pip", "install", "streamlit", "pandas", "altair", "plotly"])

# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="Bourse à l'emploi Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load data
file_name = "stats_evenements_2025-04-17_11-25-16.csv"
df = pd.read_csv(file_name, encoding="ISO-8859-1", sep=";")

# %% EDA analysis
# Convert Date Événement to datetime
df["Date Événement"] = pd.to_datetime(df["Date Événement"])

# Extract month and year from the 'Date Événement' column and create a new columns 'Month' and 'Year'
df["month"] = df["Date Événement"].dt.month
df["year"] = df["Date Événement"].dt.year
df["date"] = df["Date Événement"].dt.date

# Map month numbers to month names
month_names = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}

df["month_names"] = df["month"].map(month_names)
# %% Streamlit app
with st.sidebar:
    st.title("Tableau de bord Bourse à l'emploi")

    # Select a year
    year_list = list(df.year.unique())

    selected_year = st.selectbox("Sélectionner une année", year_list)
    df_selected_year = df[df.year == selected_year]

# Display file name
st.subheader("Nom du fichier")
st.write(file_name)

# Display the dataframe
st.subheader(
    f"Données du {df_selected_year['date'].min()} au {df_selected_year['date'].max()}"
)
st.dataframe(df_selected_year.sort_values("Événement ID", ascending=True))

# %% Nombre d'annonces diffusées par opérateur par mois
df_temp = df_selected_year.loc[
    df_selected_year["Libellé Événement"] == "Publication offre d'emploi"
]

grouped = (
    df_temp.groupby(["month", "month_names", "Code Opérateur"])
    .size()
    .reset_index(name="count")
)

st.subheader(f"Nombre d'annonces diffusées par opérateur par mois en {selected_year}")

fig = px.bar(
    grouped,
    x="month",
    y="count",
    color="Code Opérateur",
    barmode="group",
    labels={
        "month_names": "Mois",
        "count": "Nombre d'annonces",
        "Code Opérateur": "Opérateur",
    },
)
fig.update_layout(xaxis_title="Mois", yaxis_title=None, xaxis=dict(tickmode="linear"))

fig

# %% Durée moyenne de publication des annonces par opérateur
# Date de début de publication
df_temp = df_selected_year.loc[
    df_selected_year["Libellé Événement"] == "Publication offre d'emploi"
]
df_temp["debut_publication"] = pd.to_datetime(df_temp["Date Événement"])

# Date de fin de publication
df_temp2 = df_selected_year.loc[
    df_selected_year["Libellé Événement"] == "Dépublication offre d'emploi"
]
df_temp2["fin_publication"] = pd.to_datetime(df_temp2["Date Événement"])

# Ensure 'Code Opérateur' exists in both DataFrames before merging
if "Code Opérateur" in df_temp.columns and "Code Opérateur" in df_temp2.columns:
    # Merge the two DataFrames on 'Id Offre' to align the publication and depublication dates
    merged_df = pd.merge(
        df_temp[["Code Opérateur", "Id Offre", "debut_publication"]],
        df_temp2[["Code Opérateur", "Id Offre", "fin_publication"]],
        on=[
            "Id Offre",
            "Code Opérateur",
        ],  # Merge on both 'Id Offre' and 'Code Opérateur'
        how="inner",
    )
else:
    raise KeyError("The column 'Code Opérateur' is missing in one of the DataFrames.")

# Calculate the duration of publication
merged_df["duree_publication"] = (
    merged_df["fin_publication"] - merged_df["debut_publication"]
)

# calculate the average duration of publication for each operator
avg_duration = (
    merged_df.groupby("Code Opérateur")["duree_publication"].mean().reset_index()
)

# Format the 'duree_publication' column as a string
avg_duration["duree_publication"] = avg_duration["duree_publication"].apply(
    lambda x: f"{x.days} jours {x.seconds // 3600}h{x.seconds % 3600 // 60}"
)

# rename the columns
avg_duration.rename(
    columns={
        "Code Opérateur": "Opérateur",
        "duree_publication": "Durée de publication",
    },
    inplace=True,
)

st.subheader(
    f"Durée moyenne de publication des annonces par opérateur en {selected_year}"
)

st.dataframe(
    avg_duration.sort_values("Durée de publication", ascending=False).reset_index(
        drop=True
    )
)

# %% Nombre de candidatures reçues par opérateur par mois
df_temp = df_selected_year.loc[df_selected_year["Libellé Événement"] == "Candidature"]

grouped = (
    df_temp.groupby(["month", "month_names", "Code Opérateur"])
    .size()
    .reset_index(name="count")
)

st.subheader(f"Nombre de candidatures reçues par opérateur par mois en {selected_year}")

fig = px.bar(
    grouped,
    x="month",
    y="count",
    color="Code Opérateur",
    barmode="group",
    labels={
        "month_names": "Mois",
        "count": "Nombre de candidatures",
        "Code Opérateur": "Opérateur",
    },
)

fig.update_layout(xaxis_title="Mois", yaxis_title=None, xaxis=dict(tickmode="linear"))

fig

# %% Taux de candidature par annonce diffusée par opérateur par mois

# Calculer le taux de candidatures par code domaine
domain_candidature_rates = {}

# Obtenir les codes domaines uniques
unique_domains = df_selected_year["Code Opérateur"].unique()

for domain in unique_domains:
    domain_data = df[df["Code Opérateur"] == domain]
    # Calculer le nombre de consultations (CST) et de candidatures (CDT) pour le domaine
    num_consultations = domain_data[domain_data["Code Événement"] == "CST"].shape[0]
    num_candidatures = domain_data[domain_data["Code Événement"] == "CDT"].shape[0]
    # Calculer le taux de candidatures en fonction du nombre de consultations pour le domaine
    if num_consultations > 0:
        candidature_rate = (num_candidatures / num_consultations) * 100
    else:
        candidature_rate = 0

    domain_candidature_rates[domain] = candidature_rate

# Visualize the candidature rates by domain
st.subheader(
    f"Taux de candidatures par annonce diffusée par opérateur en {selected_year}"
)

fig = px.bar(
    x=domain_candidature_rates.keys(),
    y=domain_candidature_rates.values(),
    labels={"x": "Code Opérateur", "y": "Taux de candidature (%)"},
)
fig.update_layout(yaxis_title="Taux de candidature (%)", xaxis_title="Opérateur")
fig

#  %% Bijection des candidatures

# Mapping des Tenant ID vers les courriels
tenant_courriel_mapping = {
    "b87cc266-09c4-40cc-8dfa-c92e08bf9cb4": "anonyme@ratpdev.com",
    "7124e463-2734-41bf-bddb-3e475374f94c": "anonyme@keolis-lyon.fr",
    "6b23e274-b621-4690-a6c9-bf8828efd33e": "anonyme@mobilites-lyonnaises.fr",
    "846ece69-a6d3-4892-83ca-a966df6f640e": "anonyme@sytral.fr",
    "fa41821e-c12a-4f5a-9a6c-8a85b6d803bc": "admin@admin",
}

# Créer une nouvelle colonne 'Courriel' dans le DataFrame df_temp
df_temp = df_selected_year.loc[df_selected_year["Libellé Événement"] == "Candidature"]
df_temp["courriel"] = df_temp["Tenant ID"].map(tenant_courriel_mapping)

# Count grouped by "Code Opérateur" and "courriel"
grouped = (
    df_temp.groupby(["courriel", "Code Opérateur"]).size().reset_index(name="count")
)

# Create a bar plot
st.subheader(f"Origine/Destination des candidatures en {selected_year}")

fig = px.bar(
    grouped,
    x="courriel",
    y="count",
    color="Code Opérateur",
    barmode="group",
    labels={
        "courriel": "Courriel",
        "count": "Nombre de candidatures",
        "Code Opérateur": "Opérateur",
    },
)

fig.update_layout(
    xaxis_title="Courriel",
    yaxis_title="Nombre de candidatures",
    xaxis=dict(tickmode="linear"),
)

fig

st.write(
    f"**Lecture du graphique :** en {selected_year}, parmi les agents RATP Dev Lyon qui ont candidaté sur le site de la bourse à l'emploi "
    f"**{grouped.loc[(grouped['Code Opérateur'] == 'RATPLY') & (grouped['courriel'] == 'anonyme@ratpdev.com'), 'count'].sum()}** l'ont fait chez RATP Dev Lyon, "
    f"**{grouped.loc[(grouped['Code Opérateur'] == 'RATPLY') & (grouped['courriel'] == 'anonyme@mobilites-lyonnaises.fr'), 'count'].sum()}** chez la SPLRU et "
    f"**{grouped.loc[(grouped['Code Opérateur'] == 'RATPLY') & (grouped['courriel'] == 'anonyme@keolis-lyon.fr'), 'count'].sum()}** chez Keolis Bus Lyon."
)
