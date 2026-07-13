import pandas as pd
import psycopg
#Extraction: extract what you need from world_cups_recdb schema
#Transformation: 
# Add the correct Federation to each nation
# Create the Date -> Year -> Decade -> Century hierarchy for Date Dimension
# Compute the n_measures
#Load: Load everything to world_cups_star_schema