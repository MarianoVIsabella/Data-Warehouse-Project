# Data-Warehouse-Project

This repo contains all the code utilized for the Data Warehouse Final Project for AI & CS - Data Science Course in UniCal held in A.Y. 2025/26.

## Structure

### Dataset
In the dataset folder there are both the starting csv file and the output of the cleaning phase of the dataset.

### colabs_DQ_DC
This folder contains two Jupyter Notebooks files, realized in Google Colab: the Data Quality Assessment file and the Data Cleaning file.

### scripts
This folder contains the SQL scripts to create the Reconciled Database Schema and the Star Schema.
It contains also the script used to populate the Reconciled Database and the ETL pipeline from Reconciled to Star Schema.

### prompts.txt
It's a text file containing the full prompts given to LLM and its complete answers.

### env file
Note that in order to work, there should be at root level also a .env file with the following structure:  
POSTGRES_PASSWORD = ...  
POSTGRES_PORT = ...

### csvTableau
This folder contains each table of the star schema exported in csv, in order to be read by Tableau Public.

### Diagrams
This folder contains all the diagrams realized for the report of the project with Draw.io.

## Workflow
The workflow followed (and the one that I suggest to replicate the project) is:
1. Download the matches_1930_2022.csv file from either Dataset folder or its Kaggle link
2. Run the DataQuality Notebook
3. Run the DataCleaning Notebook, its output should be matches_clean.csv
4. Run reconciled_database_schema.sql on your DBMS
5. Run star_schema.sql on your DBMS
6. Run populate_rec_db.py
7. Run etl_pipeline.py

## Related links
The starting dataset is available on Kaggle at the following link [Kaggle link](https://www.kaggle.com/datasets/piterfm/fifa-football-world-cup)  
COLAB LINKS  
[Data Quality](https://colab.research.google.com/drive/1C0EAH8nBJBAqM_1rZJRXmzm-UYcUTuA9#scrollTo=qtrQLDyg5SQS)  
[Data Cleaning](https://colab.research.google.com/drive/1z2CcDoZiHxm5hBfsPPBYhosdOzjjshLw#scrollTo=TQVDVQ7_V8Qd)
