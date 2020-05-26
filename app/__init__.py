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
from pyth import python
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

#sf.set_data_dir('~/simfin_data/')
#api_key="ZxGEGRnaTpxMF0pbGQ3JLThgqY2HBL17"

python()

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
                    href = 'https://testsami999.herokuapp.com/logout/'),
        html.Img(src= dashapp1.get_asset_url('stock-icon.png')),
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


                    ], style={"height" : "50vh", "width" : "98vw", "margin-top":"20px"}),
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


                    ], style={"height" : "50vh", "width" : "98vw", "margin-top":"-20px"}),


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


                    ], style={"height" : "50vh", "width" : "98vw", "margin-top":"20px"}),
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


                    ], style={"height" : "50vh", "width" : "98vw", "margin-top":"-20px"}),

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
