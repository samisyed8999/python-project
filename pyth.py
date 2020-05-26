import dash
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd
import simfin as sf
from simfin.names import *
import dash_table
from dash.dependencies import Output, Input, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

sf.set_data_dir('~/simfin_data/')
api_key="ZxGEGRnaTpxMF0pbGQ3JLThgqY2HBL17"

def python():
    def income_statements():

        global df_income
        global ticker
        global df1
        global df_names

        df_income = sf.load(dataset='income', variant='annual', market='us',index=[TICKER,])
        df_income = df_income.drop(['Currency', 'SimFinId', 'Fiscal Period','Publish Date', 'Shares (Basic)',
                                    'Abnormal Gains (Losses)','Abnormal Gains (Losses)','Net Extraordinary Gains (Losses)',
                                    'Income (Loss) from Continuing Operations',
                                    'Net Income (Common)','Pretax Income (Loss), Adj.','Report Date'], axis = 1)
        df_income=df_income.fillna(0)
        df_income= df_income.apply(lambda x: x / 1000000)
        decimals = 0
        df_income['Fiscal Year']=df_income['Fiscal Year'].apply(lambda x: x * 1000000)
        df_income['Fiscal Year']=df_income['Fiscal Year'].apply(lambda x: round(x, decimals))
        ticker = ("AAPL")
        df_income.rename(columns={FISCAL_YEAR : 'Year', SHARES_DILUTED : 'Shares' , SGA : 'SGA' , RD : 'R&D' , DEPR_AMOR: 'D&A' , OP_INCOME : 'Operating Income' , NON_OP_INCOME : 'Non Operating Income' , INTEREST_EXP_NET :'Interest Expense' , PRETAX_INCOME_LOSS:'Pretax Income' , INCOME_TAX: 'Income Tax'}, inplace=True)
        df1 = df_income.loc[ticker].copy()
        df_names = df_income.index.copy()
        df_names = df_names.drop_duplicates()
    def income_signals():
        global df2
        global df11
        global df_signals
        global df_negative
        df_negative =df_income.copy()
        df_negative[['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']] =df_negative[['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']].apply(lambda x: x * -1)
        df_negative['Expenses'] = df_negative['Operating Expenses'] + df_negative['SGA'] + df_negative['R&D'] + df_negative['D&A']
        df11 = df_negative.loc[ticker]
        df_signals = pd.DataFrame(index=df_negative.index)
        df_signals['Year']=df_negative['Year'].copy()
        df_signals['Gross Profit Margin %']=round((df_negative['Gross Profit'] / df_negative['Revenue']) *100,2).copy()
        df_signals['SGA Of Gross Profit']=round((df_negative['SGA'] / df_negative['Gross Profit']) *100,2).copy()
        df_signals['R&D Of Gross Profit']=round((df_negative['R&D'] / df_negative['Gross Profit']) *100,2).copy()
        df_signals['Operating margin ratio']=round((df_negative['Operating Income'] / df_negative['Revenue']) *100,2).copy()
        df_signals['Interest Coverage']=round((df_negative['Operating Income'] / df_negative['Interest Expense']) ,2).copy()
        df_signals['Taxes paid']=round((df_negative['Income Tax'] / df_negative['Pretax Income']) *100,2).copy()
        df_signals['Net income margin']=round((df_negative['Net Income'] / df_negative['Revenue']) *100,2).copy()
        df_signals['Interest Coverage'] = df_signals['Interest Coverage'].replace(-np.inf, 0)
        df2=df_signals.loc[ticker]
    def balance_sheets():
        global df3
        global df_balance
        df_balance = sf.load_balance(variant='annual', market='us', index=[TICKER])
        df_balance = df_balance.drop(['Currency', 'SimFinId', 'Fiscal Period','Publish Date', 'Shares (Basic)','Report Date'], axis = 1)
        df_balance=df_balance.fillna(0)
        df_balance=df_balance.apply(lambda x: x / 1000000)
        decimals = 0
        df_balance['Fiscal Year']=df_balance['Fiscal Year'].apply(lambda x: x * 1000000)
        df_balance['Fiscal Year']=df_balance['Fiscal Year'].apply(lambda x: round(x, decimals))
        df3 = df_balance.loc[ticker]
    income_statements()
    income_signals()
    balance_sheets()
