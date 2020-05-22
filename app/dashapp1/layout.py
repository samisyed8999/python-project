import dash
import dash_html_components as html
import dash_core_components as dcc
import pandas as pd
import simfin as sf
from simfin.names import *
import dash_table
from dash.dependencies import Output, Input, State
from flask import Flask
from flask.helpers import get_root_path
from flask_login import login_required

tabtitle='Financial Statements'
sf.set_data_dir('~/simfin_data/')
api_key="ZxGEGRnaTpxMF0pbGQ3JLThgqY2HBL17"

df_income = sf.load(dataset='income', variant='annual', market='us',index=[TICKER])
df_income = df_income.drop(['Currency', 'SimFinId', 'Fiscal Period','Publish Date', 'Shares (Basic)',
                            'Abnormal Gains (Losses)','Abnormal Gains (Losses)','Net Extraordinary Gains (Losses)',
                            'Income (Loss) from Continuing Operations',
                            'Net Income (Common)','Pretax Income (Loss), Adj.','Report Date'], axis = 1)
df_income=df_income.fillna(0)

df_income[['Shares (Diluted)','Revenue','Cost of Revenue','Gross Profit','Operating Expenses',
           'Selling, General & Administrative','Research & Development','Operating Income (Loss)',
           'Non-Operating Income (Loss)','Pretax Income (Loss)','Income Tax (Expense) Benefit, Net','Net Income','Interest Expense, Net', 'Depreciation & Amortization']]= df_income[['Shares (Diluted)','Revenue','Cost of Revenue','Gross Profit','Operating Expenses',
             'Selling, General & Administrative','Research & Development','Operating Income (Loss)',
             'Non-Operating Income (Loss)','Pretax Income (Loss)','Income Tax (Expense) Benefit, Net',
             'Net Income','Interest Expense, Net', 'Depreciation & Amortization']].apply(lambda x: x / 1000000)

ticker="AAPL"
df1=df_income.loc[ticker]

df_negative = df_income
df_negative[['Cost of Revenue', 'Research & Development','Operating Expenses', 'Selling, General & Administrative', 'Income Tax (Expense) Benefit, Net', 'Depreciation & Amortization','Interest Expense, Net']] = df_negative[['Cost of Revenue', 'Research & Development','Operating Expenses', 'Selling, General & Administrative','Income Tax (Expense) Benefit, Net', 'Depreciation & Amortization', 'Interest Expense, Net']].apply(lambda x: x * -1)
df_signals = pd.DataFrame(index=df_negative.index)
df_signals['Fiscal Year']=df_negative['Fiscal Year']
df_signals['Gross Profit Margin %']=round((df_negative['Gross Profit'] / df_negative['Revenue']) *100,2)
df_signals['SGA Of Gross Profit']=round((df_negative['Selling, General & Administrative'] / df_negative['Gross Profit']) *100,2)
df_signals['R&D Of Gross Profit']=round((df_negative['Research & Development'] / df_negative['Gross Profit']) *100,2)
df_signals['Operating margin ratio']=round((df_negative['Operating Income (Loss)'] / df_negative['Revenue']) *100,2)
df_signals['Interest Coverage']=round((df_negative['Operating Income (Loss)'] / df_negative['Interest Expense, Net']) ,2)
df_signals['Taxes paid']=round((df_negative['Income Tax (Expense) Benefit, Net'] / df_negative['Pretax Income (Loss)']) *100,2)
df_signals['Net income margin']=round((df_negative['Net Income'] / df_negative['Revenue']) *100,2)
#df_signals.replace(0, np.nan, inplace=True)
#df_signals.replace(-0, 0, inplace=True)

df2=df_signals.loc[ticker]

df_balance = sf.load_balance(variant='annual', market='us', index=[TICKER])
df_balance = df_balance.drop(['Currency', 'SimFinId', 'Fiscal Period','Publish Date', 'Shares (Basic)','Report Date'], axis = 1)
df_balance=df_balance.fillna(0)
df_balance=df_balance.apply(lambda x: x / 1000000)
decimals = 0
df_balance['Fiscal Year']=df_balance['Fiscal Year'].apply(lambda x: x * 1000000)
df_balance['Fiscal Year']=df_balance['Fiscal Year'].apply(lambda x: round(x, decimals))
df3 = df_balance.loc[ticker]


dashapp1 = dash.Dash(__name__,
                         url_base_pathname='/dashboard/',
                         assets_folder=get_root_path(__name__) + '/dashapp1/assets/')
                         

dashapp1.layout = html.Div([
    html.Div([
        html.H2('Fundemental Analysis'),
        html.Img(src= dashapp1.get_asset_url('stock-image.png'))
    ], className="banner"),

    html.Div([
        dcc.Input(id="stock-input", value=ticker, type="text"),
        html.Button(id="submit-button", n_clicks=0, children="Submit", className="ticker2")
    ], className="ticker1"),


    dcc.Tabs(id="tabs", value='Tab1', className='custom-tabs-container', children=[
        dcc.Tab(label='Income Statement', id='tab1', value= 'Tab1', selected_className='custom-tab--selected', children=[

            html.Div(
                html.H3('Income statement (m)')
            ),
            dash_table.DataTable(
                id='table',
                columns=[{"name": i, "id": i} for i in df1.columns],
                data=df1.to_dict('records'),
            ),

            html.Div(
                html.H3('Key Ratios %')
            ),
            dash_table.DataTable(
                id='table2',
                columns=[{"name": i, "id": i} for i in df2.columns],
                data=df2.to_dict('records'),
            )

        ]),
        dcc.Tab(label='Balance Sheet', id='tab2', value= 'Tab2', selected_className='custom-tab--selected' ,children=[

            html.Div(
                html.H3('Balance Sheet (m)')
            ),
            dash_table.DataTable(
                id='table3',
                columns=[{"name": i, "id": i} for i in df3.columns],
                data=df3.to_dict('records'),
            ),
        ]),
        dcc.Tab(label='Cash Flow Statement', id='tab3', value= 'Tab3',selected_className='custom-tab--selected',  children=["yo"]),
        dcc.Tab(label='Intrinsic Value estimations', id='tab4', value= 'Tab4', selected_className='custom-tab--selected',  children=["yo"]),

    ])
])

