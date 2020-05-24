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
from config import BaseConfig



df_income = sf.load(dataset='income', variant='annual', market='us',index=[TICKER])
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
# check call backs
df_negative =df_income.copy()
df_negative[['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']] =df_negative[['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']].apply(lambda x: x * -1)
df_signals = pd.DataFrame(index=df_negative.index)
df_signals['Year']=df_negative['Year'].copy()
df_signals['Gross Profit Margin %']=round((df_negative['Gross Profit'] / df_negative['Revenue']) *100,2).copy()
df_signals['SGA Of Gross Profit']=round((df_negative['SGA'] / df_negative['Gross Profit']) *100,2).copy()
df_signals['R&D Of Gross Profit']=round((df_negative['R&D'] / df_negative['Gross Profit']) *100,2).copy()
df_signals['Operating margin ratio']=round((df_negative['Operating Income'] / df_negative['Revenue']) *100,2).copy()
df_signals['Interest Coverage']=round((df_negative['Operating Income'] / df_negative['Interest Expense']) ,2).copy()
df_signals['Taxes paid']=round((df_negative['Income Tax'] / df_negative['Pretax Income']) *100,2).copy()
df_signals['Net income margin']=round((df_negative['Net Income'] / df_negative['Revenue']) *100,2).copy()
df2=df_signals.loc[ticker]
df_balance = sf.load_balance(variant='annual', market='us', index=[TICKER])
df_balance = df_balance.drop(['Currency', 'SimFinId', 'Fiscal Period','Publish Date', 'Shares (Basic)','Report Date'], axis = 1)
df_balance=df_balance.fillna(0)
df_balance=df_balance.apply(lambda x: x / 1000000)
decimals = 0
df_balance['Fiscal Year']=df_balance['Fiscal Year'].apply(lambda x: x * 1000000)
df_balance['Fiscal Year']=df_balance['Fiscal Year'].apply(lambda x: round(x, decimals))
df3 = df_balance.loc[ticker]


def create_app():
    server = Flask(__name__)
    server.config.from_object(BaseConfig)

    register_dashapps(server)
    register_extensions(server)
    register_blueprints(server)

    return server


def register_dashapps(app):

    meta_viewport = {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

    dashapp1 = dash.Dash(__name__,
                         server=app,
                         url_base_pathname='/dashboard/',
                         assets_folder=get_root_path(__name__) + '/assets/',
                         meta_tags=[meta_viewport])
    #dashapp1.title = 'Financial Statements'
    dashapp1.layout = html.Div([
        html.Div([
            html.H2('Fundemental Analysis'),
            html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
        ], className="banner"),

        html.Div([
            dcc.Input(id="stock-input", value=ticker, type="text"),
            html.Button(id="submit-button", n_clicks=0, children="Submit", className="ticker2")
        ], className="ticker1"),

        html.Div([
            html.A(html.Button(id="logout-button", n_clicks=0, children="Log Out", className="logout2"),
                href = 'https://testsami999.herokuapp.com/logout/')
        ], className="logout1"),


        dcc.Tabs(id="tabs", value='Tab1', className='custom-tabs-container', children=[
            dcc.Tab(label='Income Statement', id='tab1', value= 'Tab1', selected_className='custom-tab--selected', children=[

                html.Div(
                    html.H3('Income statement (m)')
                ),
                dash_table.DataTable(
                    style_cell={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
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
    
    @dashapp1.callback(
        Output('table', 'data'),
        [Input("submit-button", "n_clicks")],
        [State("stock-input", "value")])
    def update_data(n_click, input_value):
        df1 = df_income.loc[input_value]
        data = df1.to_dict("records")
        return data

    @dashapp1.callback(
        Output('table', 'columns'),
        [Input("submit-button", "n_clicks")],
        [State("stock-input", "value")])
    def update_columns(n_click, input_value):
        df1 = df_income.loc[input_value]
        columns = [{"name": i, "id": i} for i in df1.columns]
        return columns

    @dashapp1.callback(
        Output('table2', 'data'),
        [Input("submit-button", "n_clicks")],
        [State("stock-input", "value")])
    def update_data(n_click, input_value):
        df2 = df_signals.loc[input_value]
        data = df2.to_dict("records")
        return data

    @dashapp1.callback(
        Output('table2', 'columns'),
        [Input("submit-button", "n_clicks")],
        [State("stock-input", "value")])
    def update_columns(n_click, input_value):
        df2 = df_signals.loc[input_value]
        columns = [{"name": i, "id": i} for i in df2.columns]
        return columns

    @dashapp1.callback(
        Output('table3', 'data'),
        [Input("submit-button", "n_clicks")],
        [State("stock-input", "value")])
    def update_data(n_click, input_value):
        df3 = df_balance.loc[input_value]
        data = df3.to_dict("records")
        return data

    @dashapp1.callback(
        Output('table3', 'columns'),
        [Input("submit-button", "n_clicks")],
        [State("stock-input", "value")])
    def update_columns(n_click, input_value):
        df3 = df_balance.loc[input_value]
        columns = [{"name": i, "id": i} for i in df3.columns]
        return columns
    
    
    

        
        
        
    _protect_dashviews(dashapp1)
def _protect_dashviews(dashapp):
    for view_func in dashapp.server.view_functions:
        if view_func.startswith(dashapp.config.url_base_pathname):
            dashapp.server.view_functions[view_func] = login_required(dashapp.server.view_functions[view_func])


def register_extensions(server):
    from app.extensions import db
    from app.extensions import login
    from app.extensions import migrate

    db.init_app(server)
    login.init_app(server)
    login.login_view = 'main.login'
    migrate.init_app(server, db)


def register_blueprints(server):
    from app.webapp import server_bp

    server.register_blueprint(server_bp)
