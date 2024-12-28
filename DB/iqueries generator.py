import pandas as pd

# Fonction pour générer les requêtes SQL d'insertion et les écrire dans un fichier
def generate_insert_queries(df, table_name, columns_order, columns_order_df,output_file):
    with open(output_file, 'a', encoding='utf-8') as f:  # Utilisation de l'encodage UTF-8
        # Vérifier que les colonnes attendues sont présentes dans le DataFrame
        missing_columns = [col for col in columns_order_df if col not in df.columns]
        if missing_columns:
            print(f"Colonnes manquantes pour la table {table_name}: {missing_columns}")
            return
        if missing_columns:
            print(f"Colonnes manquantes pour la table {table_name}: {missing_columns}")
            return
        
        # Réorganiser le DataFrame selon l'ordre des colonnes dans table_columns
        df = df[columns_order_df]

        # Construction de la requête d'insertion
        for index, row in df.iterrows():
            # Rejoindre les noms des colonnes pour la partie colonne
            columns = ', '.join(columns_order)

            # Préparer les valeurs des colonnes
            placeholders = []
            for val in row:
                if pd.isna(val):  # Si la valeur est manquante, ajouter 'NULL'
                    placeholders.append('NULL')
                elif isinstance(val, (int, float)):  # Si la valeur est un numéro (int ou float)
                    placeholders.append(str(val))  # Utiliser la valeur telle quelle
                elif isinstance(val, str):  # Si la valeur est une chaîne de caractères
                    # Remplacer les apostrophes par deux guillemets simples pour éviter les erreurs de syntaxe
                    val = val.replace("'", "''")  # Échapper les apostrophes
                    # Ajouter des guillemets simples autour des valeurs de type texte
                    placeholders.append(f"'{val}'")
                elif isinstance(val, str) and len(val) == 10 and val.count('-') == 2:  # Vérification d'une date au format 'YYYY-MM-DD'
                    # Ajouter des guillemets simples autour de la date
                    placeholders.append(f"'{val}'")
                else:
                    # Si ce n'est pas un numéro, une date, ou une valeur manquante, on les entoure de guillemets simples
                    placeholders.append(f"'{val}'")
            # Joindre les valeurs sans crochets, séparées par des virgules
            placeholders = ', '.join(placeholders)

            # Générer la requête SQL
            sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});\n"
            f.write(sql)

        print(f"Requêtes d'insertion générées pour la table {table_name}.")


table_columns_DF = {
    # "authors": ["AuthorID", "FullName", "Country", "University"],
    # "publishers": ["ISSN", "Name", "Quartile"],
    "articles": ["DOI", "Title", "Abstract", "Citations", "ISSN", "DateID","Website","TopicID"],
    # "keywords": ["KeywordID", "Keyword"],
    # "author_article_mapping": ["DOI", "AuthorID"],
    # "keywords_articles_mapping": ["DOI", "KeywordID"],
    # "topic": ["TopicID", "Topic"],
    # "date": ["DateID","PublicationDate", "Year", "Month", "Day"]
}
# Dictionnaire des colonnes attendues pour chaque table
table_columns = {
#    "authors": ["AuthorID", "FullName", "Country", "University"],
    # "publishers": ["ISSN", "Name", "Quartile"],
    "articles": ["DOI", "Title", "Abstract", "Citations", "ISSN", "DateID","Website","TopicID"],
    # "keywords": ["KeywordID", "Keyword"],
    # "author_article_mapping": ["DOI", "AuthorID"],
    # "keywords_articles_mapping": ["DOI", "KeywordID"],
    # "topic": ["TopicID", "Topic"],
    # "date": ["DateID","PublicationDate", "Year", "Month", "Day"]
}

# Dictionnaire des fichiers CSV et des tables SQL correspondantes
file_mapping = {
    # "authors": "DB/Tables/authors.csv",
    # "publishers": "DB/Tables/publishers.csv",
    "articles": "DB/Tables/articles.csv",
    # "keywords": "DB/Tables/keywords.csv",
    # "author_article_mapping": "DB/Tables/author_article_map.csv",
    # "keywords_articles_mapping": "DB/Tables/keywords_articles_mapping.csv",
    # "topic": "DB/Tables/topics.csv",
    # "date": "DB/Tables/dates.csv"
}

# Chemin du fichier de sortie pour les requêtes SQL
output_file = "DB/queries/article_queries.sql"

# Réinitialiser le fichier de sortie (au cas où il existe déjà)
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("-- Requêtes SQL d'insertion générées à partir des fichiers CSV\n\n")

# Générer les requêtes SQL pour chaque fichier
for table_name, file_path in file_mapping.items():
    print(f"Traitement de la table : {table_name}")
    
    # Lire le fichier CSV en ignorant la première ligne (en-tête)
    df = pd.read_csv(file_path)
    
    # Vérifier que les colonnes du DataFrame correspondent à celles attendues
    print(f"Colonnes présentes dans {file_path}: {df.columns.tolist()}")
    
    # Vérifier si le DataFrame est vide
    if df.empty:
        print(f"Le fichier {file_path} est vide. Aucune requête générée pour la table {table_name}.")
        continue
    
    # Générer et écrire les requêtes SQL dans le fichier
    generate_insert_queries(df, table_name, table_columns[table_name],table_columns_DF[table_name], output_file)

print("Toutes les requêtes d'insertion ont été générées.")
