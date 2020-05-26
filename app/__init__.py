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
python()

def graphs():
    global fig1
    global fig2
    global fig3
    global fig4
    global fig5
    global fig6
    global fig7
    global fig8
    global fig9
    global fig10
    global fig11
    global fig12
    fig1=make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Revenue']), name="Revenue"))
    fig1.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Cost of Revenue']), name="Cost of Revenue"))
    fig1.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Gross Profit']), name="Gross Profit"))
    fig1.update_layout(legend=dict(x=0, y=1,
                       traceorder="normal",
                       font=dict(family="sans-serif", size=12, color="black"),
                       bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    #fig1.update_xaxes(title_text="Year")
    fig1.update_layout(title={'text': "Sales", 'y':0.96, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig1.update_layout(margin={'t': 25, 'b': 0, 'l':0, 'r':0})
    fig1.update_yaxes(rangemode="tozero")

    fig2=make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Expenses']), name="Operating Expenses"))
    fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['SGA']), name="SGA"))
    fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['R&D']), name="R&D"))
    fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['D&A']), name="D&A"))
    fig2.update_layout(legend=dict(x=0, y=1,
                       traceorder="normal",
                       font=dict(family="sans-serif", size=12, color="black"),
                       bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig2.update_layout(title={'text': "Costs", 'y':0.96, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig2.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig2.update_yaxes(rangemode="tozero")

    fig3=make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Expenses']), name="Expenses"))
    fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Income']), name="Operating Income"))
    fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Gross Profit']), name="Gross Profit"))
    fig3.update_layout(legend=dict(x=0, y=1,
                       traceorder="normal",
                       font=dict(family="sans-serif", size=12, color="black"),
                       bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig3.update_layout(title={'text': "Gross Profit to Operating Income", 'y':0.96, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig3.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig3.update_yaxes(rangemode="tozero")

    fig4 = make_subplots(specs=[[{"secondary_y": True}]])
    fig4.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Income']), name="Operating Income"))
    fig4.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Non Operating Income']), name="Non Operating Income"))
    fig4.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Pretax Income']), name="Pretax Income"))
    fig4.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Interest Expense']), name="Interest Expense"))
    fig4.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig4.update_layout(title={'text': "Measuring Interest Expense", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig4.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig4.update_yaxes(rangemode="tozero")

    fig5 = make_subplots(specs=[[{"secondary_y": True}]])
    fig5.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Net Income']), name="Net Income"))
    fig5.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Income Tax']), name="Income Tax"))
    fig5.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Pretax Income']), name="Pretax Income"))
    fig5.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig5.update_layout(title={'text': "Measuring Tax", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig5.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig5.update_yaxes(rangemode="tozero")

    fig6 = make_subplots()
    fig6.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Shares']), name="Shares"))
    fig6.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig6.update_layout(title={'text': "Shares", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig6.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig6.update_yaxes(rangemode="tozero")

    fig7 = make_subplots()
    fig7.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['Gross Profit Margin %']), name="proft-maergin"))
    fig7.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig7.update_layout(title={'text': "Gross Profit Margin %", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig7.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig7.update_yaxes(rangemode="tozero")


    fig8 = make_subplots()
    fig8.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['SGA Of Gross Profit']), name="SGA", line=dict(color="#EF553B")))
    fig8.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig8.update_layout(title={'text': "SGA of Gross Profit % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig8.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig8.update_yaxes(rangemode="tozero")

    fig9 = make_subplots()
    fig9.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['R&D Of Gross Profit']), name="R&D", line=dict(color='#00cc96')))
    fig9.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig9.update_layout(
        title={'text': "R&D of Gross Profit % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig9.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig9.update_yaxes(rangemode="tozero")

    fig10 = make_subplots(specs=[[{"secondary_y": True}]])
    fig10.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['Operating margin ratio']), name="Oparting Margin"))
    fig10.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['Net income margin']), name="Net Income"))
    fig10.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig10.update_layout(title={'text': "Margin ratio % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig10.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig10.update_yaxes(rangemode="tozero")

    fig11 = make_subplots()
    fig11.add_trace(
        go.Scatter(x=list(df2['Year']), y=list(df2['Interest Coverage']), name="interest-coverage", line=dict(color='#00cc96')))
    fig11.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig11.update_layout(
        title={'text': "Interest Coverage ratio % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig11.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig11.update_yaxes(rangemode="tozero")

    fig12 = make_subplots()
    fig12.add_trace(
        go.Scatter(x=list(df2['Year']), y=list(df2['Taxes paid']), name="taxes", line=dict(color='#00cc96')))
    fig12.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig12.update_layout(
        title={'text': "Taxes % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig12.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig12.update_yaxes(rangemode="tozero")
graphs()

def create_app():
    server = Flask(__name__)
    server.config.from_object(BaseConfig)

    register_dashapps(server)
    register_extensions(server)
    register_blueprints(server)

    return server


def register_dashapps(app):
    # Meta tags for viewport responsiveness
    meta_viewport = {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

    dashapp1 = dash.Dash(__name__,
                         server=app,
                         url_base_pathname='/dashboard/',
                         assets_folder=get_root_path(__name__) + '/assets/',
                         meta_tags=[meta_viewport])
    #html.Img(src= dashapp1.get_asset_url('stock-icon.png')) 
    dashapp1.title = 'Financial Statements'

    dashapp1.layout = html.Div([
        html.Div([
            html.H2('Fundemental Analysis'),
            html.A(html.Button(id="logout-button", n_clicks=0, children="Log Out", className="logout2"),
                        href = 'https://testsami999.herokudashapp1.com/logout/'),
            html.Img(src="/assets/stock-icon.png"),
        ], className="banner"),

        html.Div([
            dcc.Dropdown(id='drop-down', options=[
                {'label': i, 'value': i} for i in df_names
            ], multi=False, placeholder='Enter a ticker'),
        ], className='drops'),

        dcc.Tabs(id="tabs", value='Tab2', className='custom-tabs-container', children=[
            dcc.Tab(label='Portfolio tracker', id='tab1', value= 'Tab1', selected_className='custom-tab--selected', children=[



            ]),
            dcc.Tab(label='Financial Statements', id='tab2', value= 'Tab2', selected_className='custom-tab--selected', children=[
                dcc.Tabs( className ='sub-tab-container', children=[
                    dcc.Tab(label='Income Statement', selected_className='sub-tab', children=[
                        dash_table.DataTable(
                            style_cell={
                                    'whiteSpace': 'normal',
                                    'height': 'auto',
                                },
                            style_table={
                                'width': '95%',
                                'margin': '20px 20px 0px'

                            },
                            id='table',
                            columns=[{"name": i, "id": i} for i in df1.columns],
                            data=df1.to_dict('records'),
                        ),

                        html.Div([
                           dcc.Graph(id='sales', config={'displayModeBar':False}, figure=fig1, style={

                                "height": "40vh",
                                "width": "32vw",
                                "float": "left",
                                'display': 'inline-block',
                                "margin-left":"20px"
                           }),

                            dcc.Graph(id='costs', config={'displayModeBar':False}, figure=fig2, style={

                                "height": "40vh",
                                "width": "32vw",
                                "float": "left",
                                'display': 'inline-block',
                                #"margin-left":"-100px"
                            }),

                            dcc.Graph(id='operating', config={'displayModeBar':False}, figure=fig3, style={

                                "height": "40vh",
                                "width": "32vw",
                                "float": "left",
                                "display": "inline-block",
                                #"margin-left":"-100px"
                            }),


                        ], style={"height" : "50vh", "width" : "95vw", "margin-top":"20px"}),
                        html.Div([
                           dcc.Graph(id='interest', config={'displayModeBar':False}, figure=fig4, style={

                                "height": "40vh",
                                "width": "32vw",
                                "float": "left",
                                'display': 'inline-block',
                                "margin-left":"20px"

                           }),

                            dcc.Graph(id='tax', config={'displayModeBar':False}, figure=fig5, style={

                                "height": "40vh",
                                "width": "32vw",
                                "float": "left",
                                'display': 'inline-block'


                            }),

                            dcc.Graph(id='shares', config={'displayModeBar':False}, figure=fig6, style={

                                "height": "40vh",
                                "width": "30vw",
                                "float": "left",
                                'display': 'inline-block'


                            }),


                        ], style={"height" : "50vh", "width" : "95vw", "margin-top":"-20px"}),


                        # html.Div([
                        #     html.H6('Key Ratios %')
                        # ], className='text1'),

                        dash_table.DataTable(
                            style_table={
                                'width': '95%',
                                'margin': '0px 20px 0px'
                            },
                            id='table2',
                            columns=[{"name": i, "id": i} for i in df2.columns],
                            data=df2.to_dict('records'),
                        ),

                        html.Div([
                           dcc.Graph(id='profit-margin', config={'displayModeBar':False}, figure=fig7, style={

                                "height": "40vh",
                                "width": "31vw",
                                "float": "left",
                                'display': 'inline-block',
                                "margin-left":"20px"
                           }),

                            dcc.Graph(id='SGA', config={'displayModeBar':False}, figure=fig8, style={

                                "height": "40vh",
                                "width": "31vw",
                                "float": "left",
                                'display': 'inline-block',
                                "margin-left":"20px"
                            }),

                            dcc.Graph(id='R&D', config={'displayModeBar':False}, figure=fig9, style={

                                "height": "40vh",
                                "width": "30vw",
                                "float": "left",
                                "display": "inline-block",
                                "margin-left":"20px"
                            }),


                        ], style={"height" : "50vh", "width" : "95vw", "margin-top":"20px"}),
                        html.Div([
                           dcc.Graph(id='operating-margin-ratio', config={'displayModeBar':False}, figure=fig10, style={

                                "height": "40vh",
                                "width": "32vw",
                                "float": "left",
                                'display': 'inline-block',
                                "margin-left":"20px"

                           }),

                            dcc.Graph(id='interest-coverage', config={'displayModeBar':False}, figure=fig11, style={

                                "height": "40vh",
                                "width": "32vw",
                                "float": "left",
                                'display': 'inline-block'


                            }),

                            dcc.Graph(id='taxes-paid', config={'displayModeBar':False}, figure=fig12, style={

                                "height": "40vh",
                                "width": "30vw",
                                "float": "left",
                                'display': 'inline-block'


                            }),


                        ], style={"height" : "50vh", "width" : "95vw", "margin-top":"-20px"}),

                    ]),
                    dcc.Tab(label='Balance Sheet', selected_className='sub-tab', children=[
                            dash_table.DataTable(
                                style_cell={
                                    'whiteSpace': 'normal',
                                    'height': 'auto',
                                },
                                style_table={
                                'width': '10%',
                                'margin': '20px 20px 0px'
                                },
                                id='table3',
                                columns=[{"name": i, "id": i} for i in df3.columns],
                                data=df3.to_dict('records'),
                            ),


                    ]),
                    dcc.Tab(label='Cash Flow statement ', selected_className='sub-tab', children=[]),
                ])
            ]),
            dcc.Tab(label='Intrinsic value estimations', id='tab3', value= 'Tab3',selected_className='custom-tab--selected',  children=["yo"]),
            dcc.Tab(label='Machine learning', id='tab4', value= 'Tab4', selected_className='custom-tab--selected',  children=["yo"]),

        ])
    ])


    def callbacks():
        @dashapp1.callback(
            Output('table', 'data'),
            [Input("drop-down", "value")])
        def update_data(input_value):
            df1 = df_income.loc[input_value]
            data = df1.to_dict("records")
            return data

        @dashapp1.callback(
            Output('table', 'columns'),
            [Input("drop-down", "value")])
        def update_columns(input_value):
            df1 = df_income.loc[input_value]
            columns = [{"name": i, "id": i} for i in df1.columns]
            return columns

        @dashapp1.callback(
            Output('table2', 'data'),
            [Input("drop-down", "value")])
        def update_data(input_value):
            df2 = df_signals.loc[input_value]
            data = df2.to_dict("records")
            return data

        @dashapp1.callback(
            Output('table2', 'columns'),
            [Input("drop-down", "value")])
        def update_columns(input_value):
            df2 = df_signals.loc[input_value]
            columns = [{"name": i, "id": i} for i in df2.columns]
            return columns

        @dashapp1.callback(
            Output('table3', 'data'),
            [Input("drop-down", "value")])
        def update_data(input_value):
            df3 = df_balance.loc[input_value]
            data = df3.to_dict("records")
            return data

        @dashapp1.callback(
            Output('table3', 'columns'),
            [Input("drop-down", "value")])
        def update_columns(input_value):
            df3 = df_balance.loc[input_value]
            columns = [{"name": i, "id": i} for i in df3.columns]
            return columns






        @dashapp1.callback(
            Output('sales', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df11 = df_negative.loc[input_value]
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Revenue']), name="Revenue"))
            fig1.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Cost of Revenue']), name="Cost of Revenue"))
            fig1.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Gross Profit']), name="Gross Profit"))
            fig1.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            # fig1.update_xaxes(title_text="Year")
            fig1.update_layout(title={'text': "Sales", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig1.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig1.update_yaxes(rangemode="tozero")
            return fig1

        @dashapp1.callback(
            Output('costs', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df11 = df_negative.loc[input_value]
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Expenses']), name="Operating Expenses"))
            fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['SGA']), name="SGA"))
            fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['R&D']), name="R&D"))
            fig2.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['D&A']), name="D&A"))
            fig2.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig2.update_layout(title={'text': "Costs", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig2.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig2.update_yaxes(rangemode="tozero")
            return fig2

        @dashapp1.callback(
            Output('operating', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df11 = df_negative.loc[input_value]
            fig3 = make_subplots(specs=[[{"secondary_y": True}]])
            fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Expenses']), name="Expenses"))
            fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Income']), name="Operating Income"))
            fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Gross Profit']), name="Gross Profit"))
            fig3.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig3.update_layout(title={'text': "Gross Profit to Operating Income", 'y': 0.96, 'x': 0.5, 'xanchor': 'center',
                                      'yanchor': 'top'})
            fig3.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig3.update_yaxes(rangemode="tozero")
            return fig3

        @dashapp1.callback(
            Output('interest', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df11 = df_negative.loc[input_value]
            fig4 = make_subplots(specs=[[{"secondary_y": True}]])
            fig4.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Income']), name="Operating Income"))
            fig4.add_trace(
                go.Scatter(x=list(df11['Year']), y=list(df11['Non Operating Income']), name="Non Operating Income"))
            fig4.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Pretax Income']), name="Pretax Income"))
            fig4.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Interest Expense']), name="Interest Expense"))
            fig4.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig4.update_layout(
                title={'text': "Measuring Interest Expense", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig4.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig4.update_yaxes(rangemode="tozero")
            return fig4

        @dashapp1.callback(
            Output('tax', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df11 = df_negative.loc[input_value]
            fig5 = make_subplots(specs=[[{"secondary_y": True}]])
            fig5.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Net Income']), name="Net Income"))
            fig5.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Income Tax']), name="Income Tax"))
            fig5.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Pretax Income']), name="Pretax Income"))
            fig5.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig5.update_layout(title={'text': "Measuring Tax", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig5.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig5.update_yaxes(rangemode="tozero")
            return fig5

        @dashapp1.callback(
            Output('shares', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df11 = df_negative.loc[input_value]
            fig6 = make_subplots()
            fig6.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Shares']), name="Shares"))
            fig6.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig6.update_layout(title={'text': "Shares", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig6.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig6.update_yaxes(rangemode="tozero")
            return fig6

        @dashapp1.callback(
            Output('profit-margin', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df2 = df_signals.loc[input_value]
            fig7 = make_subplots()
            fig7.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['Gross Profit Margin %']), name="proft-maergin"))
            fig7.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig7.update_layout(
                title={'text': "Gross Profit Margin %", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig7.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig7.update_yaxes(rangemode="tozero")
            return fig7

        @dashapp1.callback(
            Output('SGA', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df2 = df_signals.loc[input_value]
            fig8 = make_subplots()
            fig8.add_trace(
                go.Scatter(x=list(df2['Year']), y=list(df2['SGA Of Gross Profit']), name="SGA", line=dict(color="#EF553B")))
            fig8.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig8.update_layout(
                title={'text': "SGA of Gross Profit % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig8.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig8.update_yaxes(rangemode="tozero")
            return fig8

        @dashapp1.callback(
            Output('R&D', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df2 = df_signals.loc[input_value]
            fig9 = make_subplots()
            fig9.add_trace(
                go.Scatter(x=list(df2['Year']), y=list(df2['R&D Of Gross Profit']), name="R&D", line=dict(color='#00cc96')))
            fig9.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig9.update_layout(
                title={'text': "R&D of Gross Profit % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig9.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig9.update_yaxes(rangemode="tozero")
            return fig9

        @dashapp1.callback(
            Output('operating-margin-ratio', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df2 = df_signals.loc[input_value]
            fig10 = make_subplots(specs=[[{"secondary_y": True}]])
            fig10.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['Operating margin ratio']), name="Operating Margin"))
            fig10.add_trace(go.Scatter(x=list(df2['Year']), y=list(df2['Net income margin']), name="Net Income"))
            fig10.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig10.update_layout(
                title={'text': "Margin ratio % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig10.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig10.update_yaxes(rangemode="tozero")
            return fig10

        @dashapp1.callback(
            Output('interest-coverage', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df2 = df_signals.loc[input_value]
            fig11 = make_subplots()
            fig11.add_trace(
                go.Scatter(x=list(df2['Year']), y=list(df2['Interest Coverage']), name="interest-coverage",
                           line=dict(color='#00cc96')))
            fig11.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig11.update_layout(
                title={'text': "Interest Coverage ratio % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig11.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig11.update_yaxes(rangemode="tozero")
            return fig11

        @dashapp1.callback(
            Output('taxes-paid', 'figure'),
            [Input("drop-down", "value")])
        def update_fig(input_value):
            df2 = df_signals.loc[input_value]
            fig12 = make_subplots()
            fig12.add_trace(
                go.Scatter(x=list(df2['Year']), y=list(df2['Taxes paid']), name="taxes", line=dict(color='#00cc96')))
            fig12.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig12.update_layout(
                title={'text': "Taxes % ", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig12.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig12.update_yaxes(rangemode="tozero")
            return fig12
    callbacks()


    
    
    

        
        
        
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
