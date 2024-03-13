import csv
import pandas as pd

locals = ['LEE','DELUZIO','RESCHENTHALER','KELLY']

filename_1 = 'congress_expenses/JAN-MAR-2023-SOD-DETAIL-GRID-FINAL.csv'
filename_2 = 'congress_expenses/APRIL-JUNE 2023 SOD DETAIL GRID-FINAL.csv'
filename_3 = 'congress_expenses/JULY-SEPTEMBER-2023-SOD-DETAIL-GRID-FINAL.csv'
filename_4 = 'congress_expenses/OCT-DEC-2023-SOD-DETAIL-GRID-FINAL.csv'

#open csv file
with open(filename_1) as infile:

    #read in the file
    data = csv.reader(infile, delimiter=',')

    #create dataframe from data
    df = pd.DataFrame(data, index=None)
    df = df.rename(columns=df.iloc[0]).drop(df.index[0]).reset_index(drop=True)
    print(df.head(4))
    print('Columns:',df.columns.tolist())

    print(df['ORGANIZATION'].unique().str.contains('|'.join(locals)))

    print('###')
