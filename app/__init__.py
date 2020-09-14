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
from flask_migrate import Migrate
from textwrap import dedent

def create_app():
    server = Flask(__name__)
    server.config.from_object(BaseConfig)

    register_dashapps(server)
    register_extensions(server)
    register_blueprints(server)

    return server

def register_dashapps(app):
    sf.set_data_dir('~/simfin_data/')
    api_key = "ZxGEGRnaTpxMF0pbGQ3JLThgqY2HBL17"
    df_income = sf.load(dataset='income', variant='annual', market='us', index=[TICKER])
    df_income = df_income.drop(['Currency', 'SimFinId', 'Fiscal Period', 'Publish Date', 'Shares (Basic)',
                                'Abnormal Gains (Losses)', 'Net Extraordinary Gains (Losses)',
                                'Income (Loss) from Continuing Operations',
                                'Net Income (Common)', 'Pretax Income (Loss), Adj.', 'Report Date', 'Restated Date'],
                               axis=1)
    df_income = df_income.fillna(0)
    df_income = df_income.apply(lambda x: x / 1000000)
    decimals = 0
    df_income['Fiscal Year'] = df_income['Fiscal Year'].apply(lambda x: x * 1000000)
    df_income['Fiscal Year'] = df_income['Fiscal Year'].apply(lambda x: round(x, decimals))
    ticker = "AAPL"
    df_income.rename(
        columns={FISCAL_YEAR: 'Year', SHARES_DILUTED: 'Shares', SGA: 'SGA', RD: 'R&D', DEPR_AMOR: 'D&A',
                 OP_INCOME: 'Operating Income', NON_OP_INCOME: 'Non Operating Income',
                 INTEREST_EXP_NET: 'Interest Expense', PRETAX_INCOME_LOSS: 'Pretax Income',
                 INCOME_TAX: 'Income Tax'}, inplace=True)
    # restated date
    df_names = df_income.index.copy()
    df_names = df_names.drop_duplicates()

    # income signals
    df_negative = df_income.copy()
    df_negative[['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']] = \
        df_negative[
            ['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']].apply(
            lambda x: x * -1)
    df_negative['Expenses'] = df_negative['Operating Expenses'] + df_negative['SGA'] + df_negative['R&D'] + df_negative[
        'D&A']
    df_signals = pd.DataFrame(index=df_negative.index)
    df_signals['Year'] = df_negative['Year'].copy()
    df_signals['Gross Profit Margin %'] = round((df_negative['Gross Profit'] / df_negative['Revenue']) * 100,
                                                2).copy()
    df_signals['SGA Of Gross Profit'] = round((df_negative['SGA'] / df_negative['Gross Profit']) * 100, 2).copy()
    df_signals['R&D Of Gross Profit'] = round((df_negative['R&D'] / df_negative['Gross Profit']) * 100, 2).copy()
    df_signals['D&A Of Gross Profit'] = round((df_negative['D&A'] / df_negative['Gross Profit']) * 100, 2).copy()
    df_signals['Operating margin ratio'] = round((df_negative['Operating Income'] / df_negative['Revenue']) * 100,
                                                 2).copy()
    df_signals['Interest to Operating Income %'] = round((df_negative['Interest Expense'] / df_negative['Operating Income'])
                                                         * 100, 2).copy()
    df_signals['Taxes paid'] = round((df_negative['Income Tax'] / df_negative['Pretax Income']) * 100, 2).copy()
    df_signals['Net income margin'] = round((df_negative['Net Income'] / df_negative['Revenue']) * 100, 2).copy()
    df_signals['Interest to Operating Income %'] = df_signals['Interest to Operating Income %'].replace(-np.inf, 0)
    df2_original = df_signals.loc[ticker]

    # income growth per year
    df1_growth = pd.DataFrame(index=df_income.index)
    df1_growth['Year'] = df_income['Year'].copy()
    df1_growth['Revenue Growth'] = df_income['Revenue'].pct_change().mul(100).round(2).copy()
    df1_growth['Profit Growth'] = df_income['Gross Profit'].pct_change().mul(100).round(2).copy()
    df1_growth['Operating Income Growth'] = df_income['Operating Income'].pct_change().mul(100).round(2).copy()
    df1_growth['Pretax Income Growth'] = df_income['Pretax Income'].pct_change().mul(100).round(2).copy()
    df1_growth['Net Income Growth'] = df_income['Net Income'].pct_change().mul(100).round(2).copy()
    df1_growth = df1_growth.fillna(0)

    # compounded income growth
    df_income_compound_original = pd.DataFrame()
    df_income_compound_original['Revenue %'] = []
    df_income_compound_original['Inventory %'] = []
    df_income_compound_original['Gross Profit %'] = []
    df_income_compound_original['Operating Income %'] = []
    df_income_compound_original['Pre tax %'] = []
    df_income_compound_original['Net Income %'] = []

    # balance sheet
    df_balance = sf.load_balance(variant='annual', market='us', index=[TICKER])
    df_balance = df_balance.drop(
        ['Currency', 'SimFinId', 'Fiscal Period', 'Publish Date', 'Shares (Basic)', 'Report Date',
         'Shares (Diluted)', 'Total Liabilities & Equity', 'Restated Date'], axis=1)
    df_balance = df_balance.fillna(0)
    df_balance = df_balance.apply(lambda x: x / 1000000)
    df_balance['Fiscal Year'] = df_balance['Fiscal Year'].apply(lambda x: x * 1000000)
    df_balance['Fiscal Year'] = df_balance['Fiscal Year'].apply(lambda x: round(x, 0))
    df_balance.rename(columns={FISCAL_YEAR: 'Year', CASH_EQUIV_ST_INVEST: 'Cash & Equivalent',
                               ACC_NOTES_RECV: 'Accounts Receivable', TOTAL_CUR_ASSETS: 'Current Assets',
                               PPE_NET: 'Prop Plant & Equipment', LT_INVEST_RECV: 'Long Term Investments',
                               OTHER_LT_ASSETS: 'Other Long Term Assets', TOTAL_NONCUR_ASSETS: 'Noncurrent assets',
                               PAYABLES_ACCRUALS: 'Accounts Payable', TOTAL_CUR_LIAB: 'Current Liabilities',
                               TOTAL_NONCUR_LIAB: 'Noncurrent Liabilities', SHARE_CAPITAL_ADD: 'C&APIC Stock',
                               ST_DEBT: 'ShortTerm debts', LT_DEBT: 'LongTerm Debts',
                               INVENTORIES: 'Inventory & Stock'}, inplace=True)

    df3_original = df_balance.loc[ticker]

    # balance signals
    df_balance_signals = pd.DataFrame(index=df_balance.index)
    df_balance_signals['Year'] = df_balance['Year'].copy()
    df_balance_signals['Return on EquityT'] = round(
        (df_income['Net Income'] / (df_balance['Total Equity'] + (-1 * df_balance['Treasury Stock']))), 2).copy()
    df_balance_signals['Liabilities to EquityT'] = round(
        (df_balance['Total Liabilities'] / (df_balance['Total Equity'] + (-1 * df_balance['Treasury Stock']))),
        2).copy()
    df_balance_signals['Debt (LS) to EquityT'] = round(
        ((df_balance['LongTerm Debts'] + df_balance['ShortTerm debts']) / (df_balance['Total Equity'] +
                                                                           (-1 * df_balance['Treasury Stock']))), 2).copy()
    df_balance_signals['Long Term Debt Coverage'] = round((df_income['Net Income'] / df_balance['LongTerm Debts']),
                                                          2).copy()
    df_balance_signals['Long Term Debt Coverage'] = df_balance_signals['Long Term Debt Coverage'].replace([np.inf, -np.inf],
                                                                                                          0)
    df_balance_signals['Current Ratio'] = round((df_balance['Current Assets'] / df_balance['Current Liabilities']),
                                                2).copy()
    df_balance_signals['Return on Assets%'] = round((df_income['Net Income'] / df_balance['Total Assets']) * 100, 2).copy()
    df_balance_signals['Retained Earning to Equity%'] = round(
        (df_balance['Retained Earnings'] / df_balance['Total Equity']) * 100, 2).copy()
    df_balance_signals['Receivables of Revenue%'] = round((df_balance['Accounts Receivable'] / df_income['Revenue']) * 100,
                                                          2).copy()
    df_balance_signals['PP&E of Assets%'] = round((df_balance['Prop Plant & Equipment'] / df_balance['Total Assets']) * 100,
                                                  2).copy()
    df_balance_signals['Inventory of Assets%'] = round((df_balance['Inventory & Stock'] / df_balance['Total Assets']) * 100,
                                                       2).copy()
    df4_original = df_balance_signals.loc[ticker]

    # balance growth per year
    balance_growth = pd.DataFrame(index=df_balance.index)
    balance_growth['Year'] = df_balance['Year'].copy()
    balance_growth['Cash Growth'] = df_balance['Cash & Equivalent'].pct_change().mul(100).round(2).copy()
    balance_growth['Inventory Growth'] = df_balance['Inventory & Stock'].pct_change().mul(100).round(2).copy()
    balance_growth['Current Assets Growth'] = df_balance['Current Assets'].pct_change().mul(100).round(2).copy()
    balance_growth['PP&E Growth'] = df_balance['Prop Plant & Equipment'].pct_change().mul(100).round(2).copy()
    balance_growth['Investment Growth'] = df_balance['Long Term Investments'].pct_change().mul(100).round(2).copy()
    balance_growth['Asset Growth'] = df_balance['Total Assets'].pct_change().mul(100).round(2).copy()
    balance_growth['Liability Growth'] = df_balance['Total Liabilities'].pct_change().mul(100).round(2).copy()
    balance_growth['Retained Earnings Growth'] = df_balance['Retained Earnings'].pct_change().mul(100).round(2).copy()
    balance_growth['Equity Growth'] = df_balance['Total Equity'].pct_change().mul(100).round(2).copy()
    balance_growth = balance_growth.fillna(0)

    # balance compound growth
    df_balance_compound_original = pd.DataFrame()
    df_balance_compound_original['Cash %'] = []
    df_balance_compound_original['Inventory %'] = []
    df_balance_compound_original['Current Assets %'] = []
    df_balance_compound_original['PP&E %'] = []
    df_balance_compound_original['Long Term Investment%'] = []
    df_balance_compound_original['Assets %'] = []
    df_balance_compound_original['Liability %'] = []
    df_balance_compound_original['Retained Earnings %'] = []
    df_balance_compound_original['Equity %'] = []
    

    # Meta tags for viewport responsiveness
    meta_viewport = {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

    dashapp1 = dash.Dash(__name__,
                     server=app,
                     url_base_pathname='/dashboard/',
                     assets_folder=get_root_path(__name__) + '/assets/',
                     meta_tags=[meta_viewport])
    #html.Img(src= dashapp1.get_asset_url('stock-icon.png')) 
    dashapp1.title = 'Financial Statements'
    dashapp1.config['suppress_callback_exceptions'] = True
    dashapp1.layout = html.Div([
    html.Div([
        html.H2('Fundemental Analysis'),  
        html.A(html.Button(id="logout-button", n_clicks=0, children="Log Out", className="logout2"),
               href='https://financial8999.herokuapp.com/logout/'),
        html.Img(src= dashapp1.get_asset_url('stock-icon.png')),
        # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
    ], className="banner"),
    html.Div([
        dcc.Dropdown(id='drop-down', options=[
            {'label': i, 'value': i} for i in df_names
        ], value=ticker, multi=False, placeholder='Enter a ticker'),
    ], className='drops'),
    dcc.Tabs(id="tabs", value='Tab2', className='custom-tabs-container', children=[
        dcc.Tab(label='Portfolio tracker', id='tab1', value='Tab1', selected_className='custom-tab--selected',
                children=[]),
        dcc.Tab(label='Financial Statements', id='tab2', value='Tab2', selected_className='custom-tab--selected',
                children=[
                    dcc.Tabs(className='sub-tab-container', id='sub-tabs', value='tab-1', children=[
                        dcc.Tab(label='Income Statement', selected_className='sub-tab', value='tab-1'),
                        dcc.Tab(label='Balance Sheet', selected_className='sub-tab', value='tab-2'),
                        dcc.Tab(label='Cash Flow statement ', selected_className='sub-tab', value='tab-3'),
                    ]),
                    html.Div(id='tabs-content')
                ]),
        dcc.Tab(label='Intrinsic value estimations', id='tab3', value='Tab3', selected_className='custom-tab--selected',
                children=["yo"]),
        dcc.Tab(label='Machine learning', id='tab4', value='Tab4', selected_className='custom-tab--selected',
                children=["yo"]),
    ]),
    html.Div([  # modal div
        html.Div([  # content div
            html.Img(
                id='modal-close-button',
                src= dashapp1.get_asset_url('times-circle-solid.svg'),
                # html.Img(src= dashapp1.get_asset_url('times-circle-solid.svg'))
                n_clicks=0,
                className='info-icon2',
                style={'margin': 0},
            ),
            html.Div(
                children=[
                    dcc.Markdown(dedent('''
                        The Income Statement has been simplified by dividing by 1,000,000.

                        _**SGA**_ - Companies that do not have competitive advantage suffer from intense competition 
                        showing wild variation in SGA (selling, general and administrative) costs as a percentage of 
                        gross profit. 

                        _**R&D**_ - Companies that spend heavily on R&D have an inherent flaw in their competitive 
                        advantage that will always put their long term economics at risk since what seems like long 
                        term competitive advantage is bestowed by a patent or technological advancement that will 
                        expire or be replaced by newer technologies. Furthermore, since they constantly have to 
                        invest in new products they must also redesign and update sales programs increasing 
                        administrative costs. 

                        _**A&D**_ – Machinery and equipment eventually wear out over time with the amount they 
                        depreciate each year deducted from gross profit. Depreciation is a real cost of doing 
                        business because at some point in the future the printing press will need to be replaced. 

                        _**Interest Expense**_ – Interest paid out during the year is reflective of the total debt that 
                        a company is carrying on its books. It can be very informative as to the level of economic 
                        danger a company is in. Generally speaking, in any given industry, the company with the 
                        lowest ratio of interest payments to operating income has some kind of competitive advantage. 

                         _**Pre Tax Income**_ – This is the number Warren Buffet uses when calculating the return 
                         he’ll be getting from a business as all investments are marketed on a pre tax basis. Since 
                         all investments compete with each other, it is easier to think about them on equal terms. 

                         _**Net Income**_ – Must have a historical uptrend with consistent earnings. Share 
                         repurchasing increase per share earnings by decreasing the shares outstanding – while a lot 
                         of analysts look at per share earnings, Warren Buffet looks at the business as a whole and 
                         its net earnings to see what is actually happening. 


                    '''))]
            ),

        ],
            style={'textAlign': 'center', },
            className='modal-content',
        ),
    ], id='modal', className='modal', style={"display": "none"}),
    html.Div([  # modal div
        html.Div([  # content div
            html.Img(
                id='modal-close-button2',
                src= dashapp1.get_asset_url('times-circle-solid.svg'),
                # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
                n_clicks=0,
                className='info-icon2',
                style={'margin': 0},
            ),
            html.Div(
                children=[
                    dcc.Markdown(dedent('''

                    _**Gross Profit Margin**_ - Companies with excellent economics and high profit margins tend to 
                    have a durable competitive advantage as they have the freedom to price their products well in 
                    excess of costs of goods sold. Without competitive advantage companies have too compete by 
                    lowering their prices of products or service they are selling. As a general rule 40% or better 
                    tend to have durable competitive advantage 

                    _**SGA of Gross Profit**_ – Anything under 30% of gross profit is considered fantastic. However, 
                    there are lots of companies with durable competitive advantage that have SGA expenses in 30-80%. 

                    _**D&A of Gross Profit**_ – Companies with durable competitive advantage have low depreciation 
                    costs e.g. Coca Cola at 6% compared to GM at 22-57%. 

                    _**Interest of Operating Income**_ – Warren Buffet’s favourite durable competitive advantage 
                    holders in the consumer products category have interest pay-outs of less than 15% of operating 
                    income. This changes from industry to industry e.g Wells Fargo has 30% of operating income on 
                    interest because it’s a bank. 

                    _**Tax**_ – Check how much a company pays in taxes. Businesses that are busy misleading the IRS 
                    are usually hard at work misleading their shareholders as well. Companies with long term 
                    competitive advantage make so much money it doesn’t have to mislead anyone to look good. 

                    _**Net Income to Revenue**_ – A company showing net earnings history of more than 20% of revenue 
                    is likely to be benefitting from durable competitive advantage long term. If under 10% it may not 
                    have competitive advantage but 10-20% are lots of good businesses ripe for the mining long term 
                    investment gold. E.g Coca Cola with 21%, Moody’s with 31% compared with Southwest Airlines with a 
                    meagre 7% which reflects the highly competitive nature of the airline business. 

                    Although an exception to this is banks and financial institutions where abnormally high ratios is 
                    seen as a slacking off for the risk management department and acceptance of greater risk for 
                    easier money. 

                    '''))]
            ),

        ],
            style={'textAlign': 'center', },
            className='modal-content',
        ),
    ], id='modal2', className='modal', style={"display": "none"}),
    html.Div([  # modal div
        html.Div([  # content div
            html.Img(
                id='modal-close-button3',
                src= dashapp1.get_asset_url('times-circle-solid.svg'),
                # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
                n_clicks=0,
                className='info-icon2',
                style={'margin': 0},
            ),
            html.Div(
                children=[
                    dcc.Markdown(dedent('''

                    _**Cash & Short-term Investments**_ – A low amount or lack of cash stockpile usually means that the 
                    company has poor or mediocre economics. Companies that have a surplus of cash resulting from 
                    ongoing business activities, little or no debt, no new sales of shares or assets and a history of 
                    consistent earnings probably have excellent economics and competitive advantage working in their 
                    favour. If we see a lot of cash and marketable securities with little to no debt, chances are the 
                    business will sail through troubled times. 

                    _**Property plant and equipment**_ (net accumulated depreciation) – Companies that are in constant 
                    competition constantly have to update their manufacturing facilities to try to stay competitive 
                    often before equipment is already worn out. This creates an ongoing expense that is often quite 
                    substantial and keeps adding to the amount of plant and equipment the company lists on its 
                    balance sheet. A company with durable competitive advantage doesn’t need to constantly upgrade 
                    its plant and equipment to stay competitive. Instead it replaces equipment as they wear out. PP&E 
                    depreciates in value over time. 

                    _**Short term debts**_ – Money owed and due within a year is historically cheaper than long term 
                    money. Institutions make money by borrowing short term and lending long term but the problem with 
                    this is money borrowed in the short term needs to be payed off. This works fine until short term 
                    rates jump above what we leant long term. This makes aggressive borrowers of short-term money at 
                    the mercy of sudden shifts in the credit market. Smartest and safest way to make money is borrow 
                    money long term and lend it long term.  Warren does not invest in companies with lots of 
                    short-term debt. E.g Wells Fargo has $0.57 of short-term debt to every dollar of long-term debt 
                    compared to Bank of America who has $2.09. 

                    _**Long term debt**_ – Some companies lump it with short term debt which creates the illusion 
                    that the company has more short-term debt then it actually does. As a rule, companies with 
                    durable competitive advantage have little to no long-term debt. 

                    Sometimes an excellent business with a consumer monopoly will add large amounts of debt to 
                    finance the acquisition of another business, if so check the acquisition is also a consumer 
                    monopoly – when two combine lots of excess profits quickly reduce these debt mountains but when a 
                    consumer monopoly acquires a commodity business it will only suck out profits to support its poor 
                    economics. 

                    _**Treasury shares**_ – Shares set aside that can be brought back for additional funding and reduces 
                    the number of shares owned by private investors lowering the amount that must be paid out in 
                    dividends. If a company feels the market has undervalued its business, it might buy back some 
                    shares possibly reissuing once the price has been corrected. Reducing the number of shares boosts 
                    certain ratios as a form of financial engineering such as earnings per share which causes short 
                    term investors to flock back to stock seeing improved ratios increasing share price. 

                    _**Retained Earnings**_ – Net Income can either be paid out as a dividend, used to buy back 
                    company shares or it can be retained to keep the business growing. When income is retained it is 
                    put on the balance sheet under shareholders equity and when they are profitability used, 
                    they can greatly improve the long-term economic picture of the business. 

                    It is an accumulated number which means each year new retained earnings are added to the total 
                    accumulated retained earnings years prior. This is one of the most important metrics when 
                    determining if a business has durable competitive advantage – if a company is not adding to its 
                    retained earnings pool it is not growing its long term net worth and is unlikely to make you 
                    super rich long term. 

                    Not all growth in retained earnings is due to incremental increases in sales of existing 
                    products, some off it is due to the acquisition of other businesses. When two companies merge, 
                    their retained earnings pools are joined which creates an even larger pool. 

                    _**Leverage**_ – using debt to increase earnings of a company can give of the illusion of 
                    competitive advantage. The problem is while there seems to be some consistency in the income 
                    stream the source paying the interest payments may not be able to maintain these payments – just 
                    look at the sub prime lending crisis where banks borrowed billions at 6% and loaned at 8% to 
                    homebuyers but when the economy started to slip these buyers started to default on mortgages. 

                    These subprime borrowers did not have a durable source of income which ultimately meant 
                    investment banks didn’t have either. 

                    In assessing the quality and durability of a company’s competitive advantage, Warren Buffet 
                    avoids businesses that use a lot of leverage to generate earnings – in the short run they appear 
                    to be the goose that lays the golden egg but at the end of the day they are not. _**“Only when 
                    the tide goes out do you discover who's been swimming naked.”**_ 

                    '''))]
            ),

        ],
            style={'textAlign': 'center', },
            className='modal-content',
        ),
    ], id='modal3', className='modal', style={"display": "none"}),
])


    # callback
    @dashapp1.callback(Output('tabs-content', 'children'),
                       [Input('sub-tabs', 'value')])
    def render_content(tab):
        if tab == 'tab-1':
            return html.Div([
                html.Div([
                    html.H6('Annual Income Statement'),
                    html.Img(
                        id='instructions-button',
                        src= dashapp1.get_asset_url('question-circle-solid.svg'),
                        # html.Img(src= dashapp1.get_asset_url('question-circle-solid.svg'))
                        n_clicks=0,
                        className='info-icon',
                    ),
                ], className='annual-income'),
                html.Div([
                    dash_table.DataTable(
                        style_cell={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 0px'

                        },
                        id='table',
                        columns=[{"name": i, "id": i} for i in df_income.columns]
                    )
                ]),
                html.Div([
                    dcc.Graph(id='sales', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='costs', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        # "margin-left":"-100px"
                    }),

                    dcc.Graph(id='operating', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        "display": "inline-block",
                        # "margin-left":"-100px"
                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),
                html.Div([
                    dcc.Graph(id='interest', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"

                    }),

                    dcc.Graph(id='tax', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block'

                    }),

                    dcc.Graph(id='shares', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "30vw",
                        "float": "left",
                        'display': 'inline-block'

                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "-20px"}),
                html.Div([
                    html.H6('Key Ratios %'),
                    html.Img(
                        id='instructions-button2',
                        src= dashapp1.get_asset_url('question-circle-solid.svg'),
                        # html.Img(src=dashapp1.get_asset_url('stock-icon.png'))
                        n_clicks=0,
                        className='info-icon3',
                    ),
                ], className='text1'),
                html.Div([
                    dash_table.DataTable(
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 0px'
                        },
                        id='table2',
                        columns=[{"name": i, "id": i} for i in df2_original.columns]
                    )
                ]),
                html.Div([
                    dcc.Graph(id='profit-margin', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "31vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='SGA', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "31vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='R&D', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "30vw",
                        "float": "left",
                        "display": "inline-block",
                        "margin-left": "20px"
                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),
                html.Div([
                    dcc.Graph(id='operating-margin-ratio', config={'displayModeBar': False},
                              style={

                                  "height": "40vh",
                                  "width": "32vw",
                                  "float": "left",
                                  'display': 'inline-block',
                                  "margin-left": "20px"

                              }),

                    dcc.Graph(id='interest-coverage', config={'displayModeBar': False},
                              style={

                                  "height": "40vh",
                                  "width": "32vw",
                                  "float": "left",
                                  'display': 'inline-block'

                              }),

                    dcc.Graph(id='taxes-paid', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "30vw",
                        "float": "left",
                        'display': 'inline-block'

                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "-20px"}),
                html.Div([
                    html.H6('Growth Signals')
                ], className='text2'),
                html.Div([
                    dash_table.DataTable(
                        # style_cell={
                        #     'whiteSpace': 'normal',
                        #     'height': 'auto',
                        # },
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 20px'

                        },
                        id='income_compound_table',
                        columns=[{"name": i, "id": i} for i in df_income_compound_original.columns],
                    )
                ]),
                html.Div([
                    dash_table.DataTable(
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 0px'
                        },
                        id='table_growth',
                        columns=[{"name": i, "id": i} for i in df1_growth.columns]
                    )
                ]),
            ]),

        elif tab == 'tab-2':
            return html.Div([
                html.Div([
                    html.H6('Annual Balance Sheets'),
                    html.Img(
                        id='instructions-button3',
                        src= dashapp1.get_asset_url('question-circle-solid.svg'),
                        # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
                        n_clicks=0,
                        className='info-icon4',
                    ),
                ], className='annual-income'),
                html.Div([
                    dash_table.DataTable(
                        style_cell={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 0px'
                        },
                        id='table3',
                        columns=[{"name": i, "id": i} for i in df3_original.columns],
                    ),
                ]),
                html.Div([
                    dcc.Graph(id='balance', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='liquidity', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        # "margin-left":"-100px"
                    }),

                    dcc.Graph(id='long-term-assets', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        "display": "inline-block",
                        # "margin-left":"-100px"
                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),
                html.Div([
                    dcc.Graph(id='current debts', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='non-current-debts', config={'displayModeBar': False},
                              style={

                                  "height": "40vh",
                                  "width": "32vw",
                                  "float": "left",
                                  'display': 'inline-block',
                                  # "margin-left":"-100px"
                              }),

                    dcc.Graph(id='retained-earnings', config={'displayModeBar': False},
                              style={

                                  "height": "40vh",
                                  "width": "30vw",
                                  "float": "left",
                                  "display": "inline-block",
                                  # "margin-left":"-100px"
                              }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "-20px"}),
                html.Div([
                    html.H6('Balance Signals')
                ], className='text2'),
                html.Div([
                    dash_table.DataTable(
                        style_cell={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 0px'
                        },
                        id='table4',
                        columns=[{"name": i, "id": i} for i in df4_original.columns],
                        # data=df4.to_dict('records'),
                    )
                ]),
                html.Div([
                    dcc.Graph(id='equity_returns', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='retained_equity', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        # "margin-left":"-100px"
                    }),

                    dcc.Graph(id='assets_return', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        "display": "inline-block",
                        # "margin-left":"-100px"
                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),
                html.Div([
                    html.H6('Growth Signals')
                ], className='text2'),
                html.Div([
                    dash_table.DataTable(
                        # style_cell={
                        #     'whiteSpace': 'normal',
                        #     'height': 'auto',
                        # },
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 0px'

                        },
                        id='balance_compound_growth',
                        columns=[{"name": i, "id": i} for i in df_balance_compound_original.columns]
                    )
                ]),
                html.Div([
                    dash_table.DataTable(
                        style_cell={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_table={
                            'width': '95%',
                            'margin': '20px 20px 0px'
                        },
                        id='balance_growth',
                        columns=[{"name": i, "id": i} for i in balance_growth.columns],
                        # data=df4.to_dict('records'),
                    )
                ])
            ])


    @dashapp1.callback(
        Output('table', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1 = df_income.loc[input_value]
            data = df1.to_dict("records")
            return data
        except TypeError:
            pass


    @dashapp1.callback(
        Output('table_growth', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1_growth.loc[input_value]['Revenue Growth'][0] = 0
            df1_growth.loc[input_value]['Profit Growth'][0] = 0
            df1_growth.loc[input_value]['Operating Income Growth'][0] = 0
            df1_growth.loc[input_value]['Pretax Income Growth'][0] = 0
            df1_growth.loc[input_value]['Net Income Growth'][0] = 0
            growth = df1_growth.loc[input_value]
            data = growth.to_dict("records")
            return data
        except TypeError:
            pass


    @dashapp1.callback(
        Output('income_compound_table', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1 = df_income.loc[input_value]
            df3 = df_balance.loc[input_value]
            years_data = df1['Year'][-1] - df1['Year'][0]
            income_change = df1['Net Income'][-1] / df1['Net Income'][0]
            income_growth_percent = round((((income_change ** (1 / years_data)) - 1) * 100), 2)
            revenue_change = df1['Revenue'][-1] / df1['Revenue'][0]
            revenue_growth_percent = round((((revenue_change ** (1 / years_data)) - 1) * 100), 2)
            profit_change = df1['Gross Profit'][-1] / df1['Gross Profit'][0]
            profit_growth_percent = round((((profit_change ** (1 / years_data)) - 1) * 100), 2)
            operating_change = df1['Operating Income'][-1] / df1['Operating Income'][0]
            operating_growth_percent = round((((operating_change ** (1 / years_data)) - 1) * 100), 2)
            pretax_change = df1['Pretax Income'][-1] / df1['Pretax Income'][0]
            pretax_growth_percent = round((((pretax_change ** (1 / years_data)) - 1) * 100), 2)

            inventory_change = df3['Inventory & Stock'][-1] / df3['Inventory & Stock'][0]
            inventory_growth_percent = round((((inventory_change ** (1 / years_data)) - 1) * 100), 2)

            df_income_compound = pd.DataFrame()
            df_income_compound['Revenue %'] = [revenue_growth_percent]
            df_income_compound['Inventory %'] = [inventory_growth_percent]
            df_income_compound['Gross Profit %'] = [profit_growth_percent]
            df_income_compound['Operating Income %'] = [operating_growth_percent]
            df_income_compound['Pre tax %'] = [pretax_growth_percent]
            df_income_compound['Net Income %'] = [income_growth_percent]
            data = df_income_compound.to_dict("records")
            return data
        except (TypeError, IndexError):
            pass


    @dashapp1.callback(
        Output('table2', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df2 = df_signals.loc[input_value]
            data = df2.to_dict("records")
            return data
        except TypeError:
            pass


    @dashapp1.callback(
        Output('table3', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df3 = df_balance.loc[input_value]
            data = df3.to_dict("records")
            return data
        except TypeError:
            pass


    @dashapp1.callback(
        Output('sales', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('costs', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('operating', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df11 = df_negative.loc[input_value]
            fig3 = make_subplots(specs=[[{"secondary_y": True}]])
            fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Expenses']), name="Expenses"))
            fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Gross Profit']), name="Gross Profit"))
            fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Income']), name="Operating Income"))
            fig3.update_layout(legend=dict(x=0, y=1,
                                           traceorder="normal",
                                           font=dict(family="sans-serif", size=12, color="black"),
                                           bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
            fig3.update_layout(title={'text': "Gross Profit to Operating Income", 'y': 0.96, 'x': 0.5, 'xanchor': 'center',
                                      'yanchor': 'top'})
            fig3.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig3.update_yaxes(rangemode="tozero")
            return fig3
        except TypeError:
            pass


    @dashapp1.callback(
        Output('interest', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('tax', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('shares', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('profit-margin', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('SGA', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('R&D', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('operating-margin-ratio', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('interest-coverage', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df2 = df_signals.loc[input_value]
            fig11 = make_subplots()
            fig11.add_trace(
                go.Scatter(x=list(df2['Year']), y=list(df2['Interest to Operating Income %']), name="interest-coverage",
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('taxes-paid', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except TypeError:
            pass


    @dashapp1.callback(
        Output('liquidity', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df3 = df_balance.loc[input_value]
            fig13 = make_subplots(specs=[[{"secondary_y": True}]])
            fig13.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Cash & Equivalent']), name="Cash & Equivalent"))
            fig13.add_trace(
                go.Scatter(x=list(df3['Year']), y=list(df3['Accounts Receivable']), name="Accounts Receivables"))
            fig13.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Inventory & Stock']), name="Inventory"))
            fig13.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Current Assets']), name="Current_Assets"))
            fig13.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig13.update_layout(title={'text': "Liquidity", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig13.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig13.update_yaxes(rangemode="tozero")
            return fig13
        except TypeError:
            pass


    @dashapp1.callback(
        Output('long-term-assets', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df3 = df_balance.loc[input_value]
            fig14 = make_subplots(specs=[[{"secondary_y": True}]])
            fig14.add_trace(
                go.Scatter(x=list(df3['Year']), y=list(df3['Prop Plant & Equipment']), name="Prop Plant & Equipment"))
            fig14.add_trace(
                go.Scatter(x=list(df3['Year']), y=list(df3['Long Term Investments']), name="Long Term Investments"))
            fig14.add_trace(
                go.Scatter(x=list(df3['Year']), y=list(df3['Other Long Term Assets']), name="Other Long Term Assets"))
            fig14.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Noncurrent assets']), name="Non current Assets"))
            fig14.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig14.update_layout(
                title={'text': "Non Current Assets", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig14.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig14.update_yaxes(rangemode="tozero")
            return fig14
        except TypeError:
            pass


    @dashapp1.callback(
        Output('balance', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df3 = df_balance.loc[input_value]
            fig15 = make_subplots(specs=[[{"secondary_y": True}]])
            fig15.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Total Assets']), name="Assets"))
            fig15.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Total Liabilities']), name="Liabilities"))
            fig15.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Total Equity']), name="Equity"))
            fig15.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig15.update_layout(title={'text': "Balance", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig15.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig15.update_yaxes(rangemode="tozero")
            return fig15
        except TypeError:
            pass


    @dashapp1.callback(
        Output('current debts', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df3 = df_balance.loc[input_value]
            fig16 = make_subplots(specs=[[{"secondary_y": True}]])
            fig16.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Accounts Payable']), name="Accounts Payable"))
            fig16.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['ShortTerm debts']), name="Short Term Debts"))
            fig16.add_trace(
                go.Scatter(x=list(df3['Year']), y=list(df3['Current Liabilities']), name="Current Liabilities"))
            fig16.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig16.update_layout(
                title={'text': "Current Debts", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig16.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig16.update_yaxes(rangemode="tozero")
            return fig16
        except TypeError:
            pass


    @dashapp1.callback(
        Output('non-current-debts', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df3 = df_balance.loc[input_value]
            fig17 = make_subplots(specs=[[{"secondary_y": True}]])
            fig17.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['LongTerm Debts']), name="Long Term Debts"))
            fig17.add_trace(
                go.Scatter(x=list(df3['Year']), y=list(df3['Noncurrent Liabilities']), name="Non Current Liabilities"))
            fig17.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig17.update_layout(
                title={'text': "Non Current Debts", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig17.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig17.update_yaxes(rangemode="tozero")
            return fig17
        except TypeError:
            pass


    @dashapp1.callback(
        Output('retained-earnings', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df3 = df_balance.loc[input_value]
            fig18 = make_subplots()
            fig18.add_trace(
                go.Scatter(x=list(df3['Year']), y=list(df3['Retained Earnings']), name="retained",
                           line=dict(color='#00cc96')))
            fig18.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig18.update_layout(
                title={'text': "Retained Earnings", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig18.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig18.update_yaxes(rangemode="tozero")
            return fig18
        except TypeError:
            pass


    @dashapp1.callback(
        Output('table4', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df4 = df_balance_signals.loc[input_value]
            data = df4.to_dict("records")
            return data
        except TypeError:
            pass


    @dashapp1.callback(
        Output('balance_growth', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            balance_growth.loc[input_value]['Cash Growth'][0] = 0
            balance_growth.loc[input_value]['Inventory Growth'][0] = 0
            balance_growth.loc[input_value]['Current Assets Growth'][0] = 0
            balance_growth.loc[input_value]['PP&E Growth'][0] = 0
            balance_growth.loc[input_value]['Investment Growth'][0] = 0
            balance_growth.loc[input_value]['Asset Growth'][0] = 0
            balance_growth.loc[input_value]['Liability Growth'][0] = 0
            balance_growth.loc[input_value]['Retained Earnings Growth'][0] = 0
            balance_growth.loc[input_value]['Equity Growth'][0] = 0
            growth_balance = balance_growth.loc[input_value]
            data = growth_balance.to_dict("records")
            return data
        except TypeError:
            pass


    @dashapp1.callback(
        Output('balance_compound_growth', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df3 = df_balance.loc[input_value]
            years_data = df3['Year'][-1] - df3['Year'][0]

            inventory_change = df3['Inventory & Stock'][-1] / df3['Inventory & Stock'][0]
            inventory_growth_percent = round((((inventory_change ** (1 / years_data)) - 1) * 100), 2)

            current_assets_change = df3['Current Assets'][-1] / df3['Current Assets'][0]
            current_assets_growth_percent = round((((current_assets_change ** (1 / years_data)) - 1) * 100), 2)

            ppe_change = df3['Prop Plant & Equipment'][-1] / df3['Prop Plant & Equipment'][0]
            ppe_percent = round((((ppe_change ** (1 / years_data)) - 1) * 100), 2)

            investment_change = df3['Long Term Investments'][-1] / df3['Long Term Investments'][0]
            investment_percent = round((((investment_change ** (1 / years_data)) - 1) * 100), 2)

            assets_change = df3['Total Assets'][-1] / df3['Total Assets'][0]
            assets_percent = round((((assets_change ** (1 / years_data)) - 1) * 100), 2)

            liability_change = df3['Total Liabilities'][-1] / df3['Total Liabilities'][0]
            liability_percent = round((((liability_change ** (1 / years_data)) - 1) * 100), 2)

            retained_earnings_change = df3['Retained Earnings'][-1] / df3['Retained Earnings'][0]
            retained_earnings_percent = round((((retained_earnings_change ** (1 / years_data)) - 1) * 100), 2)

            equity_change = df3['Total Equity'][-1] / df3['Total Equity'][0]
            equity_percent = round((((equity_change ** (1 / years_data)) - 1) * 100), 2)

            cash_equivalent_change = df3['Cash & Equivalent'][-1] / df3['Cash & Equivalent'][0]
            cash_equivalent_duplicate = round((((cash_equivalent_change ** (1 / years_data)) - 1) * 100), 2)

            df_balance_compound = pd.DataFrame()
            df_balance_compound['Cash %'] = [cash_equivalent_duplicate]
            df_balance_compound['Inventory %'] = [inventory_growth_percent]
            df_balance_compound['Current Assets %'] = [current_assets_growth_percent]
            df_balance_compound['PP&E %'] = [ppe_percent]
            df_balance_compound['Long Term Investment%'] = [investment_percent]
            df_balance_compound['Assets %'] = [assets_percent]
            df_balance_compound['Liability %'] = [liability_percent]
            df_balance_compound['Retained Earnings %'] = [retained_earnings_percent]
            df_balance_compound['Equity %'] = [equity_percent]

            data = df_balance_compound.to_dict("records")
            return data
        except (TypeError, IndexError):
            pass


    @dashapp1.callback(
        Output('equity_returns', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df4 = df_balance_signals.loc[input_value]
            fig20 = make_subplots(specs=[[{"secondary_y": True}]])
            fig20.add_trace(go.Scatter(x=list(df4['Year']), y=list(df4['Return on EquityT']), name="Return on Equity"))
            fig20.add_trace(
                go.Scatter(x=list(df4['Year']), y=list(df4['Liabilities to EquityT']), name="Liabilities to Equity"))
            fig20.add_trace(
                go.Scatter(x=list(df4['Year']), y=list(df4['Debt (LS) to EquityT']), name="Debt to Equity"))
            fig20.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig20.update_layout(
                title={'text': "Risk and Earnings Power", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig20.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig20.update_yaxes(rangemode="tozero")
            return fig20
        except TypeError:
            pass


    @dashapp1.callback(
        Output('retained_equity', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df4 = df_balance_signals.loc[input_value]
            figure21 = make_subplots()
            figure21.add_trace(
                go.Scatter(x=list(df4['Year']), y=list(df4['Retained Earning to Equity%']), name="retained",
                           line=dict(color='#00cc96')))
            figure21.update_layout(legend=dict(x=0, y=1,
                                               traceorder="normal",
                                               font=dict(family="sans-serif", size=12, color="black"),
                                               bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                               borderwidth=0))
            figure21.update_layout(
                title={'text': "Retained Earnings to Equity", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            figure21.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            figure21.update_yaxes(rangemode="tozero")
            return figure21
        except TypeError:
            pass


    @dashapp1.callback(
        Output('assets_return', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df4 = df_balance_signals.loc[input_value]
            fig22 = make_subplots(specs=[[{"secondary_y": True}]])
            fig22.add_trace(go.Scatter(x=list(df4['Year']), y=list(df4['Return on Assets%']), name="Return om Assets"))
            fig22.add_trace(
                go.Scatter(x=list(df4['Year']), y=list(df4['PP&E of Assets%']), name="PP&E of Assets"))
            fig22.add_trace(
                go.Scatter(x=list(df4['Year']), y=list(df4['Inventory of Assets%']), name="Inventory of Assets"))
            fig22.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig22.update_layout(
                title={'text': "Assets allocation", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig22.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig22.update_yaxes(rangemode="tozero")
            return fig22
        except TypeError:
            pass


    @dashapp1.callback(Output('modal', 'style'),
                       [Input('instructions-button', 'n_clicks')])
    def show_modal(n):
        if n > 0:
            return {"display": "block"}
        return {"display": "none"}


    @dashapp1.callback(Output('instructions-button', 'n_clicks'),
                       [Input('modal-close-button', 'n_clicks')])
    def close_modal(n):
        if n is not None:
            # return {"display": "none"}
            return 0


    @dashapp1.callback(Output('modal2', 'style'),
                       [Input('instructions-button2', 'n_clicks')])
    def show_modal(n):
        if n > 0:
            return {"display": "block"}
        return {"display": "none"}


    @dashapp1.callback(Output('instructions-button2', 'n_clicks'),
                       [Input('modal-close-button2', 'n_clicks')])
    def close_modal(n):
        if n is not None:
            # return {"display": "none"}
            return 0


    @dashapp1.callback(Output('modal3', 'style'),
                       [Input('instructions-button3', 'n_clicks')])
    def show_modal(n):
        if n > 0:
            return {"display": "block"}
        return {"display": "none"}


    @dashapp1.callback(Output('instructions-button3', 'n_clicks'),
                       [Input('modal-close-button3', 'n_clicks')])
    def close_modal(n):
        if n is not None:
            # return {"display": "none"}
            return 0



    _protect_dashviews(dashapp1)
    
    
def _protect_dashviews(dashapp):
    for view_func in dashapp.server.view_functions:
        if view_func.startswith(dashapp.config.url_base_pathname):
            dashapp.server.view_functions[view_func] = login_required(dashapp.server.view_functions[view_func])


def register_extensions(server):
    from app.extensions import db
    from app.extensions import login
    from app.extensions import migrate
    from app.extensions import bootstrap

    db.init_app(server)
    bootstrap.init_app(server)
    login.init_app(server)
    login.login_view = 'main.login'
    migrate.init_app(server, db)


def register_blueprints(server):
    from app.webapp import server_bp

    server.register_blueprint(server_bp)
