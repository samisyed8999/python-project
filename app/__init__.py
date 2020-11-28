import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import simfin as sf
from dash.dependencies import Output, Input
from plotly.subplots import make_subplots
from simfin.names import *
from textwrap import dedent
import dash_daq as daq
import yfinance as yf
import datetime
import pandas_datareader as pdr
from dateutil.relativedelta import relativedelta
import plotly.express as px
from scipy.stats import pearsonr
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.preprocessing import RobustScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn import metrics
from flask import Flask
from flask.helpers import get_root_path
from flask_login import login_required
from config import BaseConfig
from flask_migrate import Migrate

def create_app():
    server = Flask(__name__)
    server.config.from_object(BaseConfig)

    register_dashapps(server)
    register_extensions(server)
    register_blueprints(server)

    return server

def register_dashapps(app):
    # income statement
    sf.set_data_dir('~/simfin_data/')
    api_key = "ZxGEGRnaTpxMF0pbGQ3JLThgqY2HBL17"
    df_income = sf.load(dataset='income', variant='annual', market='us', refresh_days=3, index=[TICKER])
    df_publish = df_income.copy()
    df_pe = pd.DataFrame()
    df_pe['Date'] = df_publish['Fiscal Year']
    df_pe['EPS'] = df_publish[NET_INCOME].div(df_publish[SHARES_DILUTED], axis=0)
    df_shares = df_income[SHARES_DILUTED]
    df_income = df_income.drop(['Currency', 'SimFinId', 'Fiscal Period', 'Publish Date', 'Shares (Basic)',
                                'Abnormal Gains (Losses)', 'Net Extraordinary Gains (Losses)',
                                'Income (Loss) from Continuing Operations',
                                'Net Income (Common)', 'Pretax Income (Loss), Adj.', 'Report Date', 'Restated Date'],
                               axis=1)
    # df_income=df_income.fillna(0)
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
    df_balance = sf.load_balance(variant='annual', market='us', refresh_days=3, index=[TICKER])
    df_balance = df_balance.drop(
        ['Currency', 'SimFinId', 'Fiscal Period', 'Publish Date', 'Shares (Basic)', 'Shares (Diluted)', 'Report Date',
         'Total Liabilities & Equity', 'Restated Date'], axis=1)
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
    df_balance['Book Value'] = round((df_balance['Total Equity'] / df_income['Shares']), 2)
    df_balance['EPS'] = round((df_income['Net Income'] / df_income['Shares']), 2)
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

    # cashflow statement
    df_cashflow = sf.load_cashflow(variant='annual', market='us', refresh_days=3, index=[TICKER, FISCAL_YEAR])
    df_cashflow = df_cashflow.drop(
        ['Currency', 'SimFinId', 'Fiscal Period', 'Publish Date', 'Shares (Basic)', 'Report Date',
         'Shares (Diluted)', 'Restated Date'], axis=1)
    df_cashflow = df_cashflow.apply(lambda x: x / 1000000)
    df_cashflow.rename(
        columns={'Net Income/Starting Line': 'Net Income', 'Depreciation & Amortization': 'D&A',
                 'Change in Working Capital': 'ΔWorking Capital', 'Change in Accounts Receivable': 'ΔReceivables',
                 'Change in Inventories': 'ΔInventory', 'Change in Accounts Payable': 'ΔPayables',
                 'Change in Other': 'ΔOther',
                 'Net Cash from Operating Activities': 'Cash from Operating',
                 'Change in Fixed Assets & Intangibles': 'Capital Expenditure',
                 'Net Change in Long Term Investment': 'ΔLT Investment',
                 'Net Cash from Acquisitions & Divestitures': 'Acquisitions& Divestitures',
                 'Net Cash from Investing Activities': 'Cash from Investing',
                 'Cash from (Repayment of) Debt': 'Debt Repayment', 'Cash from (Repurchase of) Equity': 'Equity Repurchase',
                 'Net Cash from Financing Activities': 'Cash from Financing'}, inplace=True)

    # complicated transposing issue where fiscal year is originally needed as an index, for graph use fiscal year
    df_cashflow = df_cashflow.fillna(0)
    df_freecashflow = pd.DataFrame()
    df_freecashflow['Cash from Operating'] = df_cashflow['Cash from Operating']
    df_freecashflow['Capital Expenditure'] = df_cashflow['Capital Expenditure']
    df_freecashflow['Free Cash Flow'] = (df_cashflow['Cash from Operating'] + df_cashflow['Capital Expenditure']).round(2)

    df_cashflow = df_cashflow.reset_index()
    df_cashflow = df_cashflow.set_index('Ticker')

    df_dividend = pd.DataFrame()
    df_dividend['Dividend per share'] = (df_cashflow['Dividends Paid'] * -1000000) / df_shares
    df_dividend['Year'] = df_cashflow['Fiscal Year']

    df_positive_cashflow = df_cashflow.copy()
    df_positive_cashflow[['Cash from Investing', 'Cash from Financing', 'Equity Repurchase', 'ΔLT Investment']] = \
        df_positive_cashflow[['Cash from Investing', 'Cash from Financing', 'Equity Repurchase', 'ΔLT Investment']].apply(
            lambda x: x * -1)
    df_positive_cashflow['Free Cash Flow'] = (
            df_positive_cashflow['Cash from Operating'] + df_positive_cashflow['Capital Expenditure']).round(2)
    df_positive_cashflow['Capex FCF'] = (
            ((df_cashflow['Capital Expenditure'] * -1) / df_cashflow['Cash from Operating']) * 100).round(2)
    df_positive_cashflow['Capex Income'] = (
            ((df_cashflow['Capital Expenditure'] * -1) / df_cashflow['Net Income']) * 100).round(2)

    df2_growth = pd.DataFrame(index=df_cashflow.index)
    df2_growth['Year'] = df_cashflow['Fiscal Year'].copy()
    df2_growth['Net Income'] = df_cashflow['Net Income'].pct_change().mul(100).round(2).copy()
    df2_growth['Free Cash Flow'] = df_positive_cashflow['Free Cash Flow'].pct_change().mul(100).round(2).copy()
    df2_growth['Cash from Operating'] = df_cashflow['Cash from Operating'].pct_change().mul(100).round(2).copy()
    df2_growth['Cash from Investing'] = df_positive_cashflow['Cash from Investing'].pct_change().mul(100).round(2).copy()
    df2_growth['Cash from Financing'] = df_positive_cashflow['Cash from Financing'].pct_change().mul(100).round(2).copy()
    df2_growth['Equity Repurchase'] = df_positive_cashflow['Equity Repurchase'].pct_change().mul(100).round(2).copy()
    df2_growth['Capex of Operating'] = df_positive_cashflow['Capex FCF']
    df2_growth['Capex of Income'] = df_positive_cashflow['Capex Income']
    df2_growth = df2_growth.fillna(0)

    df_cashflow_compound_original = pd.DataFrame()
    df_cashflow_compound_original['Net Income %'] = []
    df_cashflow_compound_original['Free Cash Flow %'] = []
    df_cashflow_compound_original['Owners Earnings'] = []
    df_cashflow_compound_original['Cash from Operating %'] = []
    df_cashflow_compound_original['Cash from Investing %'] = []
    df_cashflow_compound_original['Cash from Financing %'] = []
    df_cashflow_compound_original['Total Capex Of Total Income'] = []
    df_cashflow_compound_original['Capex Avergae of Operating'] = []

    # Buffett Indicator
    end = datetime.datetime.now()
    start = end - relativedelta(years=20)
    gdp = pdr.get_data_fred('GDP', start, end)
    wilshire = pdr.get_data_fred('WILL5000PR', start, end)

    combined = pd.concat([gdp, wilshire], axis=1)
    gdp_dates = gdp.index.values
    prev_date = 'NaN'

    for date in gdp_dates:
        if prev_date == 'NaN':
            combined.loc[:date, 'GDP'] = gdp.loc[date, 'GDP']
        else:
            combined.loc[date, 'GDP'] = gdp.loc['GDP']
        # combined.loc['GDP'] = gdp.loc[date, 'GDP']

    combined['Buffet_Indicator'] = combined.WILL5000PR / combined.GDP * 100

    fig30 = make_subplots()
    fig30.add_trace(go.Scatter(x=list(combined.index), y=list(combined['Buffet_Indicator']), name='Buffet'))
    fig30.update_layout(legend=dict(x=0, y=1,
                                    traceorder="normal",
                                    font=dict(family="sans-serif", size=12, color="black"),
                                    bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig30.update_layout(title={'text': "Buffett Indicator", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig30.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})

    # PCA Kmeans preprocessing
    clustersignals = pd.DataFrame()

    clustersignals['Gross profit margin'] = (df_income['Gross Profit'] / df_income['Revenue'])
    clustersignals['Net Income Margin'] = (df_income['Net Income'] / df_income['Revenue'])
    clustersignals['Return on Equity'] = (df_income['Net Income'] / df_balance['Total Equity'])
    clustersignals['Return on Assets'] = (df_income['Net Income'] / df_balance['Total Assets'])
    clustersignals['Liabilities to Equity'] = (df_balance['Total Liabilities'] / df_balance['Total Equity'])
    clustersignals['Retained earnings to Equity'] = (df_balance['Retained Earnings'] / df_balance['Total Equity'])
    clustersignals['Year'] = df_income['Year']

    # be careful this must be here or half of data gets destroyed
    clustersignals.dropna(inplace=True)

    # selecting only the 2018 value for each ticker
    clustersignals['Ticker'] = clustersignals.index
    clustersignals = clustersignals.set_index(clustersignals['Year'])
    clustersignals = clustersignals.drop(['Year'], axis=1)
    clustersignals = clustersignals.loc[2018]
    clustersignals = clustersignals.set_index(clustersignals['Ticker'])
    clustersignals = clustersignals.drop(['Ticker'], axis=1)


   

    

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
            html.H2('Fundamental Analysis'),
            html.A(html.Button(id="logout-button", n_clicks=0, children="Log Out", className="logout2"),
                   href='https://python-project-sami.herokuapp.com/logout/'),
            html.Img(src= dashapp1.get_asset_url('stock-icon.png')),
            # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
        ], className="banner"),
        html.Div([
            dcc.Dropdown(id='drop-down', options=[
                {'label': i, 'value': i} for i in df_names
            ], value=ticker, multi=False, placeholder='Enter a ticker'),
        ], className='drops'),
        dcc.Tabs(id="tabs", value='Tab4', className='custom-tabs-container', children=[
            dcc.Tab(label='Financial Statements', id='tab2', value='Tab2', selected_className='custom-tab--selected',
                    children=[]),
            dcc.Tab(label='Intrinsic value estimations', id='tab3', value='Tab3', selected_className='custom-tab--selected',
                    children=[]),
            dcc.Tab(label='Machine learning', id='tab4', value='Tab4', selected_className='custom-tab--selected', children=[
            ]),
        ]),
        html.Div(id='dynamic-content'),
        html.Div([
            html.Div([  # modal div
                html.Div([  # content div
                    html.Img(
                        id='modal-close-button',
                        src= dashapp1.get_asset_url('times-circle-solid.svg'),
                        # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
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
            html.Div([  # modal div
                html.Div([  # content div
                    html.Img(
                        id='modal-close-button4',
                         src= dashapp1.get_asset_url('times-circle-solid.svg'),
                        # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
                        n_clicks=0,
                        className='info-icon2',
                        style={'margin': 0},
                    ),
                    html.Div(
                        children=[
                            dcc.Markdown(dedent('''

                        The reason cash flow statements were implemented is it provides more clarity to where earnings 
                        are being used such as towards buying assets and paying off debts. Furthermore, 
                        selling shares/bonds can also contribute to cash flow but isn’t listed on the income statement. 
                        Shares bought in other companies and the dividend produced are on the cash flow statement. There 
                        are also unaccounted expenditures which are not on the income statement but are on the cash flow 
                        statement such as paying off bond holder coupons or buying back shares in the company. 

                        If cash from operations exceeds net income, the company is said to have high quality 
                        earnings-implying it is operating efficiently. 

                        The bottom line is that if a company is consistently generating more money that it is using it 
                        will potentially be able to do a number of useful things with the surplus such as: increase 
                        dividend payments, paying off existing debts, reducing its expenditure on interest payments and 
                        repurchasing shares. 

                        _**Capital Expenditure**_ – Buying a new track for your company is a capital expenditure, 
                        the value of the truck will be expensed through depreciation over its life time but the gasoline 
                        is a current expense with the full price deducted from the income during the current year. 

                        If CAPEX remains high over a number of years, they start to have a deep impact on earnings. 
                        Warren has said that this is the reason that he never invested in telephone companies, 
                        the tremendous capital outlays in building out communication networks greatly hamper their 
                        long-term economics. 

                        When looking at capital expenditures we simply add a company’s total CAPEX over a ten-year period 
                        and compare the figure with the companies net earnings for the same ten-year period. If a company 
                        is historically using less than 50% of its annual net earnings for CAPEX, it is a good place to 
                        start to look for durable competitive advantage. If it consistently using less than 25% then it 
                        more then likely has durable competitive advantage. As a rule, a company with durable competitive 
                        advantage uses a smaller portion of its earnings for capital expenditures for continuing 
                        operations. 

                        Coca Cola over the last 10 years earned a total of $20.21 per share while only using $4.01 per 
                        share or 19% of its total net earnings. If CAPEX is greater then earnings this means the company 
                        is being financed by debt. 

                        _**D&A**_ – Depreciation and Amortisation + non cash items have already been accounted for 
                        through deductions on the income statement. To get a true representation of the cash flow in the 
                        business we must we add back the cash reserved for this. 

                        _**Δ Working Capital**_ – Working capital is defined as current assets minus current liabilities.
                         It is positive if the company has more current assets or decreased current liabilities. 
                         It is negative if the company has less current assets and more current liabilities which affect
                          the cash flow in the business. 

                        _**Δ Receivables**_ – If net receivables on the balance sheet decreases this means some receivables
                         have been turned into cash therefore being a positive number on the cash flow statement.
                          If net receivables increased then more of the net income is on credit therefore to reflect cash 
                          outstanding it must be deducted. If there are large net receivable deductions this could be a sign
                           of a commodity business as most of the company’s income is on credit which is unfavourable. 

                        _**Δ Inventory**_ – If Inventory levels have increased like seen on balance sheet this figure will 
                        be negative as cash has flowed out of the business to pay for the inventory. If inventory decreased
                         annually then then it will be positive as cash flowed into the business via selling the inventory.

                        _**Δ Accounts payable**_ helps boost the cash on hand the company has by having preferable payment
                         terms suggesting competitive advantage and trust between partners. 

                        _**Cash from investing**_ – The money used to buy more supplies, upgrade facilities, build buildings
                        , purchase stock, bonds and other companies. This figure should be negative as these are
                         expenditures showing investments have been bought. If positive it means the company sold some of
                          its investments contributing to positive cash flow. 

                        _**Cash from financing**_ – Raise money or repurchase equity (shares) or bonds or give out 
                        dividends. If you see a positive number it means the company has sold bonds but incurred debt which
                         is not a good thing. This should be a negative number as it shows bonds and shares have been 
                         bought back which increases the value of your stake and reduces debt in the company. 

                        _**Net change in cash**_ – If largely positive it could suggest the company is going to conduct an 
                        acquisition. 
                        '''))]
                    ),

                ],
                    style={'textAlign': 'center', },
                    className='modal-content',
                ),
            ], id='modal4', className='modal', style={"display": "none"}),
        ])  # hidden divs
    ])


    @dashapp1.callback(Output('dynamic-content', 'children'),
                       [Input('tabs', 'value')])
    def render_content(tabs):
        if tabs == 'Tab2':
            return html.Div([

                dcc.Tabs(className='sub-tab-container', id='sub-tabs', value='tab-1', children=[
                    dcc.Tab(label='Income Statement', selected_className='sub-tab', value='tab-1'),
                    dcc.Tab(label='Balance Sheet', selected_className='sub-tab', value='tab-2'),
                    dcc.Tab(label='Cash Flow statement ', selected_className='sub-tab', value='tab-3'),
                ]),
                html.Div(id='tabs-content')
            ])

        if tabs == 'Tab3':
            return html.Div([
                html.Div([
                    html.Div([
                        html.H6('Discounted Cash Flow Model'),
                        html.Div(['Free Cash $'], className='block5-h0'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-free-cash',
                                min=0.0, max=100000,  # value=50000,
                                size=100
                            )
                        ], className='slider0'),
                        html.H5('Growth Rate'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-growth-rate',
                                label='%',
                                labelPosition='right',
                                min=0.0, max=30.0,
                                size=90
                            )
                        ], className='slider1'),
                        html.H4('Perpetual Growth'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-perpetual',
                                label='%',
                                labelPosition='right',
                                min=0.0, max=10.0, value=2.5,
                                size=60

                            ),
                        ], className='slider2'),
                        html.H3('Discount Rate'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-discount',
                                label='%',
                                labelPosition='right',
                                min=0.0, max=25.0, value=15.0,
                                size=90
                            ),
                        ], className='slider3'),

                        html.Div(['Shares in M'], className='shares-text'),

                        html.Div([
                            daq.NumericInput(
                                id='daq-shares',
                                size=110,
                                min=0.0, max=10000000,
                            ),
                        ], className='slider-shares'),

                        # html.Div([], className='block7'),
                        html.H2('Future Period'),
                        html.Div([
                            daq.Slider(
                                id='slider-period',
                                min=5, max=20, value=10,
                                size=240,
                                marks={'5': '5y', '10': '10', '15': '15', '20': '20y'}
                            ),
                        ], className='slider4'),
                        html.H1('Margin Of Safety'),
                        html.Div([
                            daq.Slider(
                                id='slider-safety',
                                min=0, max=100, value=100,
                                marks={'0': '0%', '10': '10', '20': '20', '30': '30', '40': '40', '50': '50',
                                       '60': '60', '70': '70', '80': '80', '90': '90', '100': '100%'}
                            ),
                        ], className='slider5'),
                    ], className='block5'),

                ], className='block1'),
                html.Div([
                    html.Div([
                        dcc.Graph(id='close-graph', config={'displayModeBar': False}, style={
                            "height": "40vh",
                            "width": "47vw",
                        }),
                    ], className='boxtest'),
                    html.Div([
                        html.Div([
                            html.Div([
                                dcc.Graph(figure=fig30, config={'displayModeBar': False}, style={

                                    "height": "30vh",
                                    "width": "30vw",

                                }),

                            ], className='Buffett-indicator'),
                            html.Div([
                                html.Div([
                                    html.H6('Value Estimations')

                                ], className='estimate-box'),
                                html.Div([
                                    html.Div(id='my-output'),
                                ], className='dcf-box'),

                                html.Div([
                                    html.Div(id='equity-bond'),
                                ], className='eq-box'),

                                html.Div([
                                    html.Div(id='income-bond'),
                                ], className='inc-box'),

                                html.Div([
                                    html.Div(id='book-bond'),
                                ], className='book-box'),

                            ], className='block11')
                        ], className='block10'),
                    ], className='block4'),

                ], className='block2'),
                html.Div([
                    html.Div([
                        html.H6('Equity Bond Model'),
                        html.H5('Net Equity $'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-neteq',
                                min=0.0, max=10000000,  # value=50000,
                                size=90
                            )
                        ], className='slider6'),
                        html.H4('Net Earnings $'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-netinc',
                                min=0.0, max=10000000,  # value=50000,
                                size=90
                            )
                        ], className='slider7'),
                        html.H3('Equity Growth'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-equity',
                                label='%',
                                labelPosition='right',
                                min=0.0, max=100.0,  # value=50000,
                                size=90
                            )
                        ], className='slider8'),

                        html.H2('Av Equity Return'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-equiret',
                                label='%',
                                labelPosition='right',
                                min=0.0, max=100.0,  # value=50000,
                                size=75
                            )
                        ], className='slider9'),

                        html.H1('Av P/E Ratio'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-ratio',
                                min=0.0, max=150.0,  # value=50000,
                                size=95
                            )
                        ], className='slider9_2'),

                        html.Div(['EPS Growth'], className='eps-growth'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-incgrow',
                                label='%',
                                labelPosition='right',
                                min=0.0, max=100.0,
                                size=90
                            )
                        ], className='slider10'),
                        html.Div(['BV Growth'], className='bv-growth'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-bvgro',
                                label='%',
                                labelPosition='right',
                                min=0.0, max=100.0,  # value=50000,
                                size=90
                            )
                        ], className='slider11'),
                        html.Div(['Av Dividend $'], className='div-yield'),
                        html.Div([
                            daq.NumericInput(
                                id='daq-dividend',
                                min=0.0, max=100.0,  # value=50000,
                                size=75
                            )
                        ], className='slider12'),
                    ], className='block6'),

                ], className='block3'),
            ])

        if tabs == 'Tab4':
            return html.Div([
                html.Div([

                    html.Div([html.H6('Pearsons Correlation')], className='pearson'),
                    html.Div([
                        dcc.Graph(id='heatmap', config={'displayModeBar': False}, style={

                            "height": "30vh",
                            "width": "60vw",
                            "display": "inline-block",
                            "margin-left": "-36%",
                        }),
                    ], className='heatmap'),
                    html.Div([
                        html.P(id='income-corr')

                    ], className='coefficient1'),

                ], className='mac1'),
                html.Div([

                    html.Div([html.H6('Regression Analysis')], className='reg-analysis'),
                    html.Div([
                        dcc.Graph(id='regression-graph', config={'displayModeBar': False}, style={

                            "height": "30vh",
                            "width": "30vw",
                            "display": "inline-block",
                            "margin-top": "70px"
                        }),
                    ], className='regression'),
                    html.Div([html.Div([html.Div(id='r-coefficient')

                                        ], className='coeff-value'),
                              html.Div([

                                  html.P(id='dcf-machine')
                              ], className='dcf-mach'),
                              # html.Div(['COEF Estimate : $ 90.36'], className='coef-mach'),
                              html.Div(['Perpetual Growth Rate'], className='pep-mach'),
                              html.Div([
                                  daq.Slider(
                                      id='machine-pep',
                                      min=0.5, max=4.5, value=2.5,
                                      marks={'0.5': '0.5%', '1': '1', '1.5': '1.5', '2': '2', '2.5': '2.5',
                                             '3': '3', '3.5': '3.5', '4': '4', '4.5': '4.5%'},
                                      size=150, step=0.5,
                                  ),
                              ], className='machine-slider'),
                              html.Div(['Discount Rate'], className='return-mach'),
                              html.Div([
                                  daq.Slider(
                                      id='discount-pep',
                                      min=0, max=30, value=15,
                                      marks={'0': '0%', '5': '5', '10': '10', '15': '15', '20': '20',
                                             '25': '25', '30': '30%'},
                                      size=150,
                                  ),
                              ], className='discount-slider'),

                              ], className='lineardata'),
                    html.Div([

                        html.Div(id='line-equation'),
                        # 'y = {}'.format(slope)+' x + {}'.format(yinter)
                    ], className='line-equation'),
                    html.Div([
                        daq.Slider(
                            id='year-pep',
                            min=0, max=20, value=10,
                            marks={'5': '5Y', '10': '10', '15': '15', '20': '20Y'},
                            size=150,
                            vertical=True
                        ),
                    ], className='year-machine'),

                ], className='mac2'),
                html.Div([

                    html.Div([
                        dcc.Graph(id='PCA-2D', config={'displayModeBar': False}, style={

                            "height": "35vh",
                            "width": "30vw",
                            "display": "inline-block",
                            "margin-top": "20px"

                        })
                    ], className='PCA'),
                    html.Div([
                        dcc.Graph(id='variance', config={'displayModeBar': False}, style={

                            "height": "25vh",
                            "width": "18vw",
                            "display": "inline-block",
                            "float": "right",
                            "margin-top": "70px"
                        })
                    ], className='variance-graph'),

                ], className='mac3'),
                html.Div([
                    html.Div([
                        dcc.Graph(id='PCA-3D', config={"displaylogo": False,
                                                       'modeBarButtonsToRemove': ['pan3d', 'toImage',
                                                                                  'resetCameraDefault3d',
                                                                                  'hoverClosest3d']},
                                  # 'resetCameraLastSave3d'
                                  style={

                                      "height": "40vh",
                                      "width": "45vw",

                                  })
                    ], className='PCA-3D'),
                    html.Div([html.H6('K Means Clustering')], className='kmeans'),
                    html.Div(['Nodes:'], className='node-text'),
                    html.Div([
                        daq.NumericInput(
                            id='nodes',
                            min=2, max=10, value=4,  # value=50000,
                            size=80
                        )
                    ], className='node-slider'),
                    html.Div([html.Div(id='silhouette')], className='sil-text'),
                    html.Div([

                        dcc.RangeSlider(
                            id='filterslider',
                            min=0.0,
                            max=100,
                            value=[10, 95],
                            allowCross=False,
                            tooltip={'always_visible': True, 'placement': 'left'},  # hover
                            vertical=True,
                            verticalHeight=250,
                            marks={
                                0: {'label': '0%'},
                                100: {'label': '100%'}},
                        )

                    ], className='filterslider'),
                    html.Div([html.Div(id='3d-silhouette')], className='cluster-text'),
                    html.Div([html.Div(id='2d-cluster')], className='cluster-estimate'),
                    html.Div([html.Div(id='3d-cluster')], className='cluster-estimate-3d'),
                ], className='mac4'),

            ])


    # dynamic layout callback
    @dashapp1.callback(Output('tabs-content', 'children'),
                       [Input('sub-tabs', 'value')])
    def render_content(tab):
        if tab == 'tab-1':
            return html.Div([
                html.Div([
                    html.H6('Annual Income statement'),
                    html.Img(
                        id='instructions-button',
                        src=dashapp1.get_asset_url('question-circle-solid.svg'),
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
                        src=dashapp1.get_asset_url('question-circle-solid.svg'),
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

        if tab == 'tab-2':
            return html.Div([
                html.Div([
                    html.H6('Annual Balance Sheets'),
                    html.Img(
                        id='instructions-button3',
                        src=dashapp1.get_asset_url('question-circle-solid.svg'),
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

        if tab == 'tab-3':
            return html.Div([
                html.Div([
                    html.H6('Annual Cash Flow, statement'),
                    html.Img(
                        id='instructions-button4',
                        src=dashapp1.get_asset_url('question-circle-solid.svg'),
                        # html.Img(src= dashapp1.get_asset_url('stock-icon.png'))
                        n_clicks=0,
                        className='info-icon5',
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
                        id='table_cashflow',
                        columns=[{"name": i, "id": i} for i in df_cashflow.columns]
                    )
                ]),

                html.Div([
                    html.H6('Free Cash Flow'),
                ], className='text3'),

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
                        id='FCF',
                        # columns=[{"name": i, "id": i} for i in transposed_table.columns],
                        # data=transposed_table.to_dict('records'),
                    )
                ]),

                html.Div([
                    dcc.Graph(id='operating-cash', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='investing-cash', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        # "margin-left":"-100px"
                    }),

                    dcc.Graph(id='financing-cash', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        "display": "inline-block",
                        # "margin-left":"-100px"
                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),

                html.Div([
                    dcc.Graph(id='freecash', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        "margin-left": "20px"
                    }),

                    dcc.Graph(id='equitypurchase', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        # "margin-left": "20px"
                    }),

                    dcc.Graph(id='longterminv', config={'displayModeBar': False}, style={

                        "height": "40vh",
                        "width": "32vw",
                        "float": "left",
                        'display': 'inline-block',
                        # "margin-left": "20px"
                    }),

                ], style={"height": "50vh", "width": "98vw", "margin-top": "-20px"}),
                html.Div([
                    html.H6('Growth Signals')
                ], className='text2'),

                dash_table.DataTable(
                    # style_cell={
                    #     'whiteSpace': 'normal',
                    #     'height': 'auto',
                    # },
                    style_table={
                        'width': '95%',
                        'margin': '0px 20px 20px'

                    },
                    id='cashflow_compound_table',
                    columns=[{"name": i, "id": i} for i in df_cashflow_compound_original.columns],
                ),

                html.Div([
                    dash_table.DataTable(
                        style_table={
                            'width': '95%',
                            'margin': '0px 20px 0px'
                        },
                        id='table_growth2',
                        columns=[{"name": i, "id": i} for i in df2_growth.columns]
                    )
                ]),
            ])


    # callbacks
    @dashapp1.callback(
        [Output('silhouette', 'children'), Output('3d-silhouette', 'children'), Output('PCA-2D', 'figure'),
         Output('variance', 'figure'), Output('PCA-3D', 'figure'), Output('3d-cluster', 'children'),
         Output('2d-cluster', 'children')],
        [
            Input("filterslider", "value"),
            Input("nodes", "value"),
            Input("drop-down", "value"),

        ])
    def update_children(slider_value, nodes_value, down_value):
        try:
            # apply filters
            low = slider_value[0] / 100
            high = slider_value[1] / 100
            quant_df = clustersignals.quantile([low, high])
            filtered_cluster = clustersignals.apply(lambda x: x[(x > quant_df.loc[low, x.name]) &
                                                                (x < quant_df.loc[high, x.name])], axis=0)
            filtered_cluster.dropna(inplace=True)
            robust_scaler = RobustScaler()
            robust_scaler.fit(filtered_cluster)
            X_train_robust_filtered = robust_scaler.transform(filtered_cluster)
            k = nodes_value

            # pca 2d
            pca = PCA(n_components=2)
            pca.fit(X_train_robust_filtered)
            pca_dataset_filtered = pca.transform(X_train_robust_filtered)
            pca_dataset_filtered = pd.DataFrame(data=pca_dataset_filtered, columns=['PC1', 'PC2'])
            kmeans = KMeans(n_clusters=k, random_state=0).fit(pca_dataset_filtered)

            sil_score = metrics.silhouette_score(pca_dataset_filtered, kmeans.labels_, metric='euclidean')
            sil_score = sil_score.round(2)
            text1 = html.Div('Silhouette Score 2D: {}'.format(sil_score))

            predict = kmeans.predict(pca_dataset_filtered)
            pca_dataset_filtered['Cluster'] = pd.Series(predict, index=pca_dataset_filtered.index)
            pca_dataset_filtered['Ticker'] = filtered_cluster.index

            fig33 = px.scatter(pca_dataset_filtered, x='PC1', y='PC2', color='Cluster', hover_name="Ticker",
                               template="plotly_white")

            centers_ = kmeans.cluster_centers_
            fig33.add_trace(
                go.Scatter(x=centers_[:, 0], y=centers_[:, 1], showlegend=False, mode='markers',
                           marker=dict(symbol=4, color="red", line_width=1, size=10), hoverinfo='skip'))

            try:

                X_train_robust = robust_scaler.transform(clustersignals)
                pca_dataset1 = pca.transform(X_train_robust)
                pca_dataset1 = pd.DataFrame(data=pca_dataset1, columns=['PC1', 'PC2'])
                pca_dataset1 = pca_dataset1.set_index(clustersignals.index)
                test_data1 = [pca_dataset1.loc[down_value]]
                twod_cluster = float(kmeans.predict(test_data1))
                text4 = html.Div('2D Cluster Estimate: {}'.format(twod_cluster))
                fig33.update_layout(
                    annotations=[
                        dict(text="You are here", x=pca_dataset1.loc[down_value]['PC1'],
                             y=pca_dataset1.loc[down_value]['PC2']
                             )])
            except IndexError:
                text4 = html.Div('2D Cluster Estimate: Cluster is undefined')

            fig33.update_layout(
                title={
                    'text': "Principle Component Analysis ",
                    'y': 0.98,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'})
            fig33.update_layout(margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
            fig33.update(layout_coloraxis_showscale=False)

            # variance
            pca2 = PCA()
            pca2.fit(X_train_robust_filtered)
            exp_var_cumul = np.cumsum(pca2.explained_variance_ratio_)

            fig35 = px.area(x=range(1, exp_var_cumul.shape[0] + 1), y=exp_var_cumul,
                            labels={"x": "# Components", "y": "Explained Variance"}
                            )
            fig35.update_layout(margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})

            # pca 3d
            pca1 = PCA(n_components=3)
            pca1.fit(X_train_robust_filtered)
            pca_dataset_filtered1 = pca1.transform(X_train_robust_filtered)
            pca_dataset_filtered1 = pd.DataFrame(data=pca_dataset_filtered1, columns=['PC1', 'PC2', 'PC3'])
            kmeans1 = KMeans(n_clusters=k, random_state=0).fit(pca_dataset_filtered1)
            sil_score1 = metrics.silhouette_score(pca_dataset_filtered1, kmeans1.labels_, metric='euclidean')
            sil_score1 = sil_score1.round(2)
            text2 = html.Div('Silhouette Score 3D: {}'.format(sil_score1))

            predict1 = kmeans1.predict(pca_dataset_filtered1)
            pca_dataset_filtered1['Cluster'] = pd.Series(predict1, index=pca_dataset_filtered1.index)
            pca_dataset_filtered1['Ticker'] = filtered_cluster.index
            fig34 = px.scatter_3d(
                pca_dataset_filtered1, x='PC1', y='PC2', z='PC3', color='Cluster', hover_name="Ticker"
            )

            pca_dataset_filtered['Cluster'] = pd.Series(predict, index=pca_dataset_filtered.index)
            pca_dataset_filtered['Ticker'] = filtered_cluster.index

            fig34.update_layout(margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
            fig34.update(layout_coloraxis_showscale=False)

            camera = dict(
                eye=dict(x=0., y=2, z=0.)
            )

            fig34.update_layout(scene_camera=camera)

            try:

                X_train_robust = robust_scaler.transform(clustersignals)
                pca_dataset = pca1.transform(X_train_robust)
                pca_dataset = pd.DataFrame(data=pca_dataset, columns=['PC1', 'PC2', 'PC3'])
                pca_dataset = pca_dataset.set_index(clustersignals.index)
                test_data = [pca_dataset.loc[down_value]]
                threed_cluster = float(kmeans1.predict(test_data))
                text3 = html.Div('3D Cluster Estimate: {}'.format(threed_cluster))
                fig34.update_layout(
                    scene=dict(
                        annotations=[
                            dict(x=pca_dataset.loc[down_value]['PC1'], y=pca_dataset.loc[down_value]['PC2'],
                                 z=pca_dataset.loc[down_value]['PC3'], text="You are here", textangle=0, ax=0, ay=-75,
                                 font=dict(color="black", size=12), arrowcolor="black", arrowsize=3, arrowwidth=1,
                                 arrowhead=1)]

                    ))
            except IndexError:
                text3 = html.Div('3D Cluster Estimate: Cluster is undefined')

            return text1, text2, fig33, fig35, fig34, text3, text4
        except ValueError:
            pass


    @dashapp1.callback(
        Output('close-graph', 'figure'),
        [Input("drop-down", "value"),
         ])
    def update_fig(down_value):
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            dfyf = yf.download(down_value,
                               start='2007-01-01',
                               end=today,
                               progress=False)
            fig29 = make_subplots(specs=[[{"secondary_y": True}]])
            fig29.add_trace(
                go.Scatter(x=list(dfyf.index), y=list(dfyf['Open']), name="Share Price",
                           line=dict(color='#00cc96')))
            dfyf['smallvol'] = dfyf['Volume'] / (10 ** 7)
            if (dfyf['smallvol'].sum()) / 365 < 8:
                dfyf['smallvol'] = dfyf['smallvol'] * 10
            fig29.add_trace(
                go.Scatter(x=list(dfyf.index), y=list(dfyf['smallvol']), name="Volume", visible="legendonly",
                           line=dict(color="#EF553B")))
            fig29.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig29.update_layout(
                title={'text': "Share Price", 'y': 0.96, 'x': 0.46, 'xanchor': 'center', 'yanchor': 'top'})
            fig29.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            # fig28.update_yaxes(rangemode="tozero")
            fig29.update_layout(
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1,
                                 label="1m",
                                 step="month",
                                 stepmode="backward"),
                            dict(count=3,
                                 label="3m",
                                 step="month",
                                 stepmode="backward"),
                            dict(count=6,
                                 label="6m",
                                 step="month",
                                 stepmode="backward"),
                            dict(count=1,
                                 label="YTD",
                                 step="year",
                                 stepmode="todate"),
                            dict(count=1,
                                 label="1y",
                                 step="year",
                                 stepmode="backward"),
                            dict(count=5,
                                 label="5y",
                                 step="year",
                                 stepmode="backward"),
                            dict(count=10,
                                 label="10y",
                                 step="year",
                                 stepmode="backward"),
                        ])
                    ),
                    rangeslider=dict(
                        visible=True
                    ),
                    type="date"
                )
            )
            return fig29
        except (TypeError, AttributeError, KeyError):
            pass


    @dashapp1.callback(
        Output('daq-ratio', 'value'),
        [Input("drop-down", "value")])
    def update_ratio(down_value):
        try:
            table = df_publish.loc[down_value]
            start_date = table['Report Date'][0]
            end_date = table['Report Date'][-1]

            dfpe = df_pe.loc[down_value]
            dfpe = dfpe.set_index(dfpe['Date'])
            dfpe = dfpe.drop(['Date'], axis=1)

            today = datetime.datetime.now().strftime('%Y-%m-%d')
            app1 = yf.download(down_value,
                               start='2007-01-01',
                               end=today,
                               progress=False)
            app1['date'] = app1.index
            mask = (app1['date'] > start_date) & (app1['date'] <= end_date)
            app1 = app1.loc[mask]

            close_graph = pd.DataFrame()
            close_graph['Close'] = app1['Close']
            close_graph['Date'] = close_graph.index
            close_graph['Date'] = close_graph['Date'].dt.year
            close_graph = close_graph.set_index(close_graph['Date'])
            close_graph = close_graph.drop(['Date'], axis=1)

            close_graph['EPS'] = dfpe['EPS']
            close_graph['P/E'] = close_graph['Close'] / close_graph['EPS']
            count_row = close_graph.shape[0]
            sum1 = close_graph['P/E'].sum()
            average = (sum1 / count_row).round(2)
            return average
        except (TypeError, AttributeError, KeyError):
            return 0


    @dashapp1.callback(
        Output('daq-free-cash', 'value'),
        [Input("drop-down", "value")])
    def update_cash(down_value):
        try:
            df1 = df_cashflow.loc[down_value]
            cash_free = (df1['Cash from Operating'][-1] + df1['Capital Expenditure'][-1]).round(2)
            return cash_free
        except KeyError:
            return 0


    @dashapp1.callback(
        Output('daq-neteq', 'value'),
        [Input("drop-down", "value")])
    def update_netequity(down_value):
        try:
            df1 = df_balance.loc[down_value]
            equity = df1['Total Equity'][-1]
            return equity
        except KeyError:
            return 0


    @dashapp1.callback(
        Output('daq-netinc', 'value'),
        [Input("drop-down", "value")])
    def update_netequity(down_value):
        df1 = df_income.loc[down_value]
        income = df1['Net Income'][-1]
        return income


    @dashapp1.callback(
        Output('daq-dividend', 'value'),
        [Input("drop-down", "value")])
    def update_dend(down_value):
        try:
            df1 = df_dividend.loc[down_value]
            years_data = df1['Year'][-1] - df1['Year'][0]
            total_dividend = df1['Dividend per share'].sum()
            average_dividend = (total_dividend / years_data).round(2)
            return average_dividend
        except KeyError:
            return 0


    @dashapp1.callback(
        Output('daq-bvgro', 'value'),
        [Input("drop-down", "value")])
    def update_cash(down_value):
        try:
            df1 = df_balance.loc[down_value]
            years_data = df1['Year'][-1] - df1['Year'][0]
            book_change = df1['Book Value'][-1] / df1['Book Value'][0]
            if book_change < 0:
                return 0
            else:
                book_growth_percent = round((((book_change ** (1 / years_data)) - 1) * 100), 2)
                return book_growth_percent
        except (TypeError, KeyError):
            return 0


    @dashapp1.callback(
        Output('daq-equity', 'value'),
        [Input("drop-down", "value")])
    def update_cash(down_value):
        try:
            df3 = df_balance.loc[down_value]
            years_data = df3['Year'][-1] - df3['Year'][0]
            equity_change = df3['Total Equity'][-1] / df3['Total Equity'][0]
            if equity_change < 0:
                return 0
            else:
                equity_percent = round((((equity_change ** (1 / years_data)) - 1) * 100), 2)
                return equity_percent
        except KeyError:
            return 0


    @dashapp1.callback(
        Output('daq-equiret', 'value'),
        [Input("drop-down", "value")])
    def update_cash(down_value):
        try:
            df3 = df_balance_signals.loc[down_value]
            years_data = df3['Year'][-1] - df3['Year'][0]
            sum1 = (df3['Return on EquityT'] * 100).sum()
            average_equity = (sum1 / years_data).round(2)
            return average_equity
        except KeyError:
            return 0


    @dashapp1.callback(
        Output('daq-incgrow', 'value'),
        [Input("drop-down", "value")])
    def update_cash(down_value):
        df1 = df_income.loc[down_value]
        years_data = df1['Year'][-1] - df1['Year'][0]
        df1['EPS'] = df1['Net Income'] / df1['Shares']
        eps_change = df1['EPS'][-1] / df1['EPS'][0]
        if eps_change < 0:
            return 0
        else:
            eps_growth_percent = round((((eps_change ** (1 / years_data)) - 1) * 100), 2)
            return eps_growth_percent


    @dashapp1.callback(
        Output('daq-shares', 'value'),
        [Input("drop-down", "value")])
    def update_shares(down_value):
        try:
            df1 = df_income.loc[down_value]
            shares_now = (df1['Shares'][-1]).round(0)
            return shares_now
        except IndexError:
            return 0


    @dashapp1.callback(
        Output('daq-growth-rate', 'value'),
        [Input("drop-down", "value")])
    def update_cash(down_value):
        try:
            df1 = df_cashflow.loc[down_value]
            years_data = df1['Fiscal Year'][-1] - df1['Fiscal Year'][0]
            free_cashflow_change = (df1['Cash from Operating'][-1] + df1['Capital Expenditure'][-1]) / (
                    df1['Cash from Operating'][0] + df1['Capital Expenditure'][0])
            if free_cashflow_change < 0:
                return 0
            else:
                free_cashflow_growth_percent = round((((free_cashflow_change ** (1 / years_data)) - 1) * 100), 2)
                return free_cashflow_growth_percent
        except (IndexError, KeyError):
            return 0


    @dashapp1.callback(
        Output('income-corr', 'children'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            app1 = yf.download(input_value,
                               start='2007-01-01',
                               end=today,
                               progress=False)

            df_sig = pd.DataFrame()
            df_sig['Income'] = df_income.loc[input_value]['Net Income']
            df_sig['Equity'] = df_balance.loc[input_value]['Total Equity']
            df_sig['Cash'] = df_cashflow.loc[input_value]['Cash from Operating'] + df_cashflow.loc[input_value][
                'Capital Expenditure']
            df_sig['Book Value'] = df_balance.loc[input_value]['Total Equity'] / df_income.loc[input_value]['Shares']
            df_sig['Date'] = df_income.loc[input_value]['Year']
            df_sig = df_sig.set_index(df_sig['Date'])

            # combining the variables with the close price so that the indexes match
            df_value = pd.DataFrame()
            df_value['Close'] = app1['Close']

            df_value['Date'] = df_value.index
            df_value['Date'] = df_value['Date'].dt.year
            df_value = df_value.set_index(df_value['Date'])
            df_value = df_value.drop(['Date'], axis=1)

            df_value['Income'] = df_sig['Income']
            df_value['Cash'] = df_sig['Cash']
            df_value['Equity'] = df_sig['Equity']
            df_value['Book Value'] = df_sig['Book Value']

            df_value.dropna(inplace=True)
            income_corr = (pearsonr(df_value['Close'], df_value['Income'])[0]).round(2)
            equity_corr = (pearsonr(df_value['Close'], df_value['Equity'])[0]).round(2)
            book_corr = (pearsonr(df_value['Close'], df_value['Book Value'])[0]).round(2)
            cash_corr = (pearsonr(df_value['Close'], df_value['Cash'])[0]).round(2)
            return html.P([

                'Income Correlation: {}'.format(income_corr), html.Br(),
                'Free Cash Correlation: {}'.format(cash_corr), html.Br(),
                'Equity Correlation: {}'.format(equity_corr), html.Br(),
                'Book Value Correlation: {}'.format(book_corr)
            ])
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('my-output', 'children'),
        [
            Input('daq-free-cash', 'value'),
            Input('daq-shares', 'value'),
            Input('daq-growth-rate', 'value'),
            Input('daq-perpetual', 'value'),
            Input('daq-discount', 'value'),
            Input('slider-period', 'value'),
            Input('slider-safety', 'value'),
        ])
    def update_output_div(cash_value, shares_value, rate_value, perpetual_value, discount_value, period_value,
                          safety_value):
        try:
            shares = shares_value
            discount = 1 + (discount_value / 100)
            perpetual = 1 + (perpetual_value / 100)
            growth = 1 + (rate_value / 100)
            common_difference = growth / discount
            new_common_difference = perpetual / discount
            safety = safety_value / 100

            power_variable = common_difference ** period_value
            cash_difference = cash_value * common_difference
            geometric_numer = cash_difference * (1 - power_variable)
            geometric_denom = 1 - common_difference
            equation1 = geometric_numer / geometric_denom

            new_geometric_numer = cash_value * power_variable * new_common_difference
            new_geometric_denom = 1 - new_common_difference
            equation2 = new_geometric_numer / new_geometric_denom

            discounted_cash = equation1 + equation2
            intrinsic_value = (discounted_cash / shares) * safety
            intrinsic_value = round(intrinsic_value, 2)

            return 'DCF Estimate: $ {}'.format(intrinsic_value)
        except (ZeroDivisionError, TypeError):
            return 'DCF Estimate: $ 0'


    @dashapp1.callback(
        Output('equity-bond', 'children'),
        [
            Input("daq-neteq", "value"),
            Input('daq-equity', 'value'),
            Input('daq-shares', 'value'),
            Input('daq-equiret', 'value'),
            Input('daq-ratio', 'value'),
            Input('daq-discount', 'value'),
            Input('slider-period', 'value'),
            Input('slider-safety', 'value'),
        ])
    def update_output_div(neteq_value, equity_value, shares_value, equiret_value, ratio_value, discount_value, period_value,
                          safety_value):
        try:
            equity1 = neteq_value
            total_shares = shares_value
            growth = (equity_value / 100) + 1
            future_equity = equity1 * (growth ** period_value)
            future_return = future_equity * (equiret_value / 100)
            future_eps = future_return / total_shares
            future_price = ratio_value * future_eps
            discount_val = (discount_value / 100) + 1
            discount_denom = discount_val ** period_value
            discounted_value = future_price / discount_denom
            safety_margin = safety_value / 100
            intrinsic_value = round(discounted_value * safety_margin, 2)

            return 'Equity P/E: $ {}'.format(intrinsic_value * 2)
            # multiply by 2 to take into account share buybacks
        except (ZeroDivisionError, TypeError):
            return 'Equity P/E: $ 0'


    @dashapp1.callback(
        Output('income-bond', 'children'),
        [
            Input("daq-netinc", "value"),
            Input("daq-shares", "value"),
            Input('daq-incgrow', 'value'),
            Input('daq-ratio', 'value'),
            Input('daq-discount', 'value'),
            Input('slider-period', 'value'),
            Input('slider-safety', 'value'),
        ])
    def update_output_div(netinc_value, shares_value, incgro_value, ratio_value, discount_value, period_value,
                          safety_value):
        try:

            eps_now = netinc_value / shares_value
            eps_growth = (incgro_value / 100) + 1
            future_eps = eps_now * (eps_growth ** period_value)
            future_price = future_eps * ratio_value

            investment_return = (discount_value / 100) + 1
            discount_denom = investment_return ** period_value
            discount_price = future_price / discount_denom
            safety_margin = safety_value / 100
            intrinsic_value = round(discount_price * safety_margin, 2)
            return 'Income P/E: $ {}'.format(intrinsic_value)
        except (ZeroDivisionError, TypeError):
            return 'Income P/E: 0'


    @dashapp1.callback(
        Output('book-bond', 'children'),
        [
            Input("daq-neteq", "value"),
            Input("daq-shares", "value"),
            Input('daq-bvgro', 'value'),
            Input('daq-dividend', 'value'),
            Input('daq-discount', 'value'),
            Input('slider-period', 'value'),
            Input('slider-safety', 'value'),
        ])
    def update_output_div(neteq_value, shares_value, bvgro_value, dividend_value, discount_value, period_value,
                          safety_value):
        try:
            present_book = neteq_value / shares_value
            growth_rate = ((bvgro_value / 100) + 1) * period_value
            discount_rate = ((discount_value / 100) + 1) ** period_value

            first_equation = (1 - (1 / discount_rate)) * dividend_value
            first_equation = first_equation / (discount_value / 100)

            second_equation = (present_book * growth_rate) / discount_rate
            intrinsic_value = round((first_equation + second_equation) * (safety_value / 100), 2)
            return 'Liquidation: $ {}'.format(intrinsic_value)
        except (ZeroDivisionError, TypeError):
            return 'Liquidation: $ 0'


    @dashapp1.callback(
        Output('table_cashflow', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1 = df_cashflow.loc[input_value]
            data = df1.to_dict("records")
            return data
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('r-coefficient', 'children'),
        [Input("drop-down", "value")])
    def update_children(input_value):
        try:
            ticker1 = input_value
            regressiondf = pd.DataFrame()
            regressiondf['Year'] = df_income.loc[ticker1]['Year']
            regressiondf['Cash'] = df_cashflow.loc[ticker1]['Cash from Operating'] + df_cashflow.loc[ticker1][
                'Capital Expenditure']
            X = regressiondf['Year'].values.reshape(-1, 1)

            model1 = LinearRegression()
            model1.fit(X, regressiondf['Cash'])
            variance = (model1.score(X, regressiondf['Cash'])).round(2)
            return 'R Coefficient Value: {}'.format(variance)
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('line-equation', 'children'),
        [Input("drop-down", "value")])
    def update_children(input_value):
        try:
            ticker1 = input_value
            regressiondf = pd.DataFrame()
            regressiondf['Year'] = df_income.loc[ticker1]['Year']
            regressiondf['Cash'] = df_cashflow.loc[ticker1]['Cash from Operating'] + df_cashflow.loc[ticker1][
                'Capital Expenditure']
            X = regressiondf['Year'].values.reshape(-1, 1)

            model1 = LinearRegression()
            model1.fit(X, regressiondf['Cash'])
            yinter = model1.intercept_.round(2)
            slope = round((float(model1.coef_)), 2)

            if yinter < 0:
                return 'y = {}'.format(slope) + ' x {}'.format(yinter)
            if yinter > 0:
                return 'y = {}'.format(slope) + ' x + {}'.format(yinter)
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('dcf-machine', 'children'),
        [
            Input("drop-down", "value"),
            Input('machine-pep', 'value'),
            Input('discount-pep', 'value'),
            Input('year-pep', 'value'),
        ])
    def update_children(drop_value, machine_value, discount_value, year_value):
        try:
            ticker1 = drop_value
            perpetual_growth = (machine_value / 100) + 1
            discount_rate = (discount_value / 100) + 1

            regressiondf = pd.DataFrame()
            regressiondf['Year'] = df_income.loc[ticker1]['Year']
            regressiondf['Cash'] = df_cashflow.loc[ticker1]['Cash from Operating'] + df_cashflow.loc[ticker1][
                'Capital Expenditure']
            X = regressiondf['Year'].values.reshape(-1, 1)

            model1 = LinearRegression()
            model1.fit(X, regressiondf['Cash'])
            variance = (model1.score(X, regressiondf['Cash'])).round(2)
            yinter = round(float(model1.intercept_), 2)
            slope = round((float(model1.coef_)), 2)

            discount_value = 0
            for i in range(0, year_value):  # num of years is 10
                discount_value = discount_value + ((slope * (i + 2021)) + yinter) / (
                        discount_rate ** (i + 1))  # investment return is 15%
            perpetual_cash = ((slope * (year_value - 1 + 2021)) + yinter)  # num of years
            perpetual_cash = (perpetual_cash * (perpetual_growth / discount_rate)) / (
                    1 - (perpetual_growth / discount_rate))  # last year predicted value

            total_cash = discount_value + perpetual_cash
            df1 = df_income.loc[ticker1]
            shares_now = (df1['Shares'][-1]).round(0)
            intrinsic_mach = (total_cash / shares_now).round(2)

            # calculating correlation

            today = datetime.datetime.now().strftime('%Y-%m-%d')
            app1 = yf.download(drop_value,
                               start='2007-01-01',
                               end=today,
                               progress=False)

            df_sig = pd.DataFrame()
            df_sig['Cash'] = df_cashflow.loc[drop_value]['Cash from Operating'] + df_cashflow.loc[drop_value][
                'Capital Expenditure']
            df_sig['Date'] = df_income.loc[drop_value]['Year']
            df_sig = df_sig.set_index(df_sig['Date'])

            # combining the variables with the close price so that the indexes match
            df_value = pd.DataFrame()
            df_value['Close'] = app1['Close']

            df_value['Date'] = df_value.index
            df_value['Date'] = df_value['Date'].dt.year
            df_value = df_value.set_index(df_value['Date'])
            df_value = df_value.drop(['Date'], axis=1)

            df_value['Cash'] = df_sig['Cash']

            df_value.dropna(inplace=True)
            cash_corr = (pearsonr(df_value['Close'], df_value['Cash'])[0]).round(2)

            coefficient_value1 = (intrinsic_mach * cash_corr).round(2)
            coefficient_value2 = (intrinsic_mach * variance * cash_corr).round(2)

            return html.P([
                'DCF Estimate : $ {}'.format(intrinsic_mach), html.Br(),
                'P Estimate : $ {}'.format(coefficient_value1), html.Br(),
                'R+P Estimate: $ {}'.format(coefficient_value2)
            ])
        except (ZeroDivisionError, TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('FCF', 'columns'),
        [Input("drop-down", "value")])
    def update_columns(input_value):
        try:
            df1 = df_freecashflow.loc[input_value]
            df2 = df_cashflow.loc[input_value]
            years_data = df2['Fiscal Year'][-1] - df2['Fiscal Year'][0]
            average = ((df1['Capital Expenditure'] * -1) / df1['Cash from Operating']).round(2)
            average = average.sum()
            average = average / years_data
            df1['Owners Earnings'] = df1['Cash from Operating'] - (df1['Cash from Operating'] * average)
            df1['Owners Earnings'] = df1['Owners Earnings'].round(1)
            df1 = df1.drop(['Capital Expenditure', 'Cash from Operating'], axis=1)
            df1 = df1.transpose()
            columns = [{"name": i, "id": i} for i in df1.columns]
            return columns
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('FCF', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1 = df_freecashflow.loc[input_value]
            df2 = df_cashflow.loc[input_value]
            years_data = df2['Fiscal Year'][-1] - df2['Fiscal Year'][0]
            average = ((df1['Capital Expenditure'] * -1) / df1['Cash from Operating']).round(2)
            average = average.sum()
            average = average / years_data
            df1['Owners Earnings'] = (df1['Cash from Operating']) - (df1['Cash from Operating'] * average).round(1)
            df1 = df1.drop(['Capital Expenditure', 'Cash from Operating'], axis=1)
            df1 = df1.transpose()
            data = df1.to_dict("records")
            return data
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('table', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1 = df_income.loc[input_value]
            df1 = df1.fillna(0)
            data = df1.to_dict("records")
            return data
        except TypeError:
            pass


    @dashapp1.callback(
        Output('table_growth', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            pd.set_option('mode.chained_assignment', None)  # would show a warning for editing a copy
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
        Output('table_growth2', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df2_growth.loc[input_value]['Net Income'][0] = 0
            df2_growth.loc[input_value]['Free Cash Flow'][0] = 0
            df2_growth.loc[input_value]['Cash from Operating'][0] = 0
            df2_growth.loc[input_value]['Cash from Investing'][0] = 0
            df2_growth.loc[input_value]['Cash from Financing'][0] = 0
            df2_growth.loc[input_value]['Equity Repurchase'][0] = 0
            growth = df2_growth.loc[input_value]
            data = growth.to_dict("records")
            return data
        except (TypeError, KeyError):
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
        Output('cashflow_compound_table', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            np.warnings.filterwarnings('ignore')  # for values that aren't real
            df1 = df_cashflow.loc[input_value]
            df2 = df_positive_cashflow.loc[input_value]
            years_data = df1['Fiscal Year'][-1] - df1['Fiscal Year'][0]
            free_cashflow_change = (df1['Cash from Operating'][-1] + df1['Capital Expenditure'][-1]) / (
                    df1['Cash from Operating'][0] + df1['Capital Expenditure'][0])
            free_cashflow_growth_percent = round((((free_cashflow_change ** (1 / years_data)) - 1) * 100), 2)

            income_change = df1['Net Income'][-1] / df1['Net Income'][0]
            income_growth_percent = round((((income_change ** (1 / years_data)) - 1) * 100), 2)
            cash_operating_change = df1['Cash from Operating'][-1] / df1['Cash from Operating'][0]
            cash_operating_growth_percent = round((((cash_operating_change ** (1 / years_data)) - 1) * 100), 2)
            cash_investing_change = df2['Cash from Investing'][-1] / df2['Cash from Investing'][0]
            cash_investing_growth_percent = round((((cash_investing_change ** (1 / years_data)) - 1) * 100), 2)
            cash_financing_change = df2['Cash from Financing'][-1] / df2['Cash from Financing'][0]
            cash_financing_growth_percent = round((((cash_financing_change ** (1 / years_data)) - 1) * 100), 2)

            capex_total = (df1['Capital Expenditure'] * -1).sum()
            income_total = df1['Net Income'].sum()
            capex_percent = ((capex_total / income_total) * 100).round(2)
            total_capex = ((df1['Capital Expenditure'] * -1) / df1['Cash from Operating']).sum()
            capex_average = (total_capex / years_data).round(2)

            df2['Owners Earnings'] = (df1['Cash from Operating']) - (df1['Cash from Operating'] * capex_average)
            owners_earnings_change = df2['Owners Earnings'][-1] / (df2['Owners Earnings'][0])
            owners_earnings_growth_percent = round((((owners_earnings_change ** (1 / years_data)) - 1) * 100), 2)

            df_cashflow_compound = pd.DataFrame()
            df_cashflow_compound['Net Income %'] = [income_growth_percent]
            df_cashflow_compound['Free Cash Flow %'] = [free_cashflow_growth_percent]
            df_cashflow_compound['Owners Earnings'] = [owners_earnings_growth_percent]
            df_cashflow_compound['Cash from Operating %'] = [cash_operating_growth_percent]
            df_cashflow_compound['Cash from Investing %'] = [cash_investing_growth_percent]
            df_cashflow_compound['Cash from Financing %'] = [cash_financing_growth_percent]
            df_cashflow_compound['Total Capex Of Total Income'] = [capex_percent]
            df_cashflow_compound['Capex Avergae of Operating'] = [capex_average]
            df_cashflow_compound = df_cashflow_compound.fillna(0)
            data = df_cashflow_compound.to_dict("records")
            return data
        except (TypeError, KeyError, IndexError):
            pass


    @dashapp1.callback(
        Output('table2', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df2 = df_signals.loc[input_value]
            df2 = df2.fillna(0)
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

            if df3['Long Term Investments'][0] == 0:
                investment_percent = 0
            else:
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


    @dashapp1.callback(
        Output('operating-cash', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df11 = df_cashflow.loc[input_value]
            fig23 = make_subplots()
            fig23.add_trace(
                go.Scatter(x=list(df11['Fiscal Year']), y=list(df11['Cash from Operating']), name="Operating Cash"))
            fig23.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig23.update_layout(title={'text': "Cash from Operating Activities", 'y': 0.96, 'x': 0.5, 'xanchor': 'center',
                                       'yanchor': 'top'})
            fig23.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig23.update_yaxes(rangemode="tozero")
            return fig23
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('investing-cash', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df11 = df_positive_cashflow.loc[input_value]
            fig24 = make_subplots()
            fig24.add_trace(
                go.Scatter(x=list(df11['Fiscal Year']), y=list(df11['Cash from Investing']), name="Investing Cash",
                           line=dict(color="#EF553B")))
            fig24.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig24.update_layout(
                title={'text': "Cash spent investing", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig24.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig24.update_yaxes(rangemode="tozero")
            return fig24
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('financing-cash', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df11 = df_positive_cashflow.loc[input_value]
            fig25 = make_subplots()
            fig25.add_trace(
                go.Scatter(x=list(df11['Fiscal Year']), y=list(df11['Cash from Financing']), name="Financing Cash",
                           line=dict(color='#00cc96')))
            fig25.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig25.update_layout(
                title={'text': "Cash spent financing", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig25.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig25.update_yaxes(rangemode="tozero")
            return fig25
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('freecash', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df1 = df_cashflow.loc[input_value]
            df2 = pd.DataFrame()
            df2['Free Cash Flow'] = (df1['Cash from Operating'] + df1['Capital Expenditure']).round(2)
            fig26 = make_subplots()
            fig26.add_trace(go.Scatter(x=list(df1['Fiscal Year']), y=list(df2['Free Cash Flow']), name="Free Cash Flow"))
            fig26.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig26.update_layout(
                title={'text': "Free Cash Flow", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig26.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            fig26.update_yaxes(rangemode="tozero")
            return fig26
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('equitypurchase', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df1 = df_positive_cashflow.loc[input_value]
            fig27 = make_subplots()
            fig27.add_trace(
                go.Scatter(x=list(df1['Fiscal Year']), y=list(df1['Equity Repurchase']), name="Equity Repurchase",
                           line=dict(color="#EF553B")))
            fig27.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig27.update_layout(
                title={'text': "Equity Repurchased", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig27.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            # fig27.update_yaxes(rangemode="tozero")
            return fig27
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('longterminv', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df11 = df_positive_cashflow.loc[input_value]
            fig28 = make_subplots()
            fig28.add_trace(
                go.Scatter(x=list(df11['Fiscal Year']), y=list(df11['ΔLT Investment']), name="Long Term Investment",
                           line=dict(color='#00cc96')))
            fig28.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            fig28.update_layout(
                title={'text': "Long Term Investment", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
            fig28.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
            # fig28.update_yaxes(rangemode="tozero")
            return fig28
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('heatmap', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            app1 = yf.download(input_value,
                               start='2007-01-01',
                               end=today,
                               progress=False)

            df_sig = pd.DataFrame()
            df_sig['Income'] = df_income.loc[input_value]['Net Income']
            df_sig['Equity'] = df_balance.loc[input_value]['Total Equity']
            df_sig['Cash'] = df_cashflow.loc[input_value]['Cash from Operating'] + df_cashflow.loc[input_value][
                'Capital Expenditure']
            df_sig['Book Value'] = df_balance.loc[input_value]['Total Equity'] / df_income.loc[input_value]['Shares']
            df_sig['Date'] = df_income.loc[input_value]['Year']
            df_sig = df_sig.set_index(df_sig['Date'])

            # combining the variables with the close price so that the indexes match
            df_value = pd.DataFrame()
            df_value['Close'] = app1['Close']

            df_value['Date'] = df_value.index
            df_value['Date'] = df_value['Date'].dt.year
            df_value = df_value.set_index(df_value['Date'])
            df_value = df_value.drop(['Date'], axis=1)

            df_value['Income'] = df_sig['Income']
            df_value['Cash'] = df_sig['Cash']
            df_value['Equity'] = df_sig['Equity']
            df_value['Book Value'] = df_sig['Book Value']

            df_value.dropna(inplace=True)

            fig31 = px.imshow(df_value.corr(), template="seaborn", x=['Close', 'Income', 'Cash', 'Equity', 'Book'],
                              y=['Close', 'Income', 'Cash', 'Equity', 'Book'])
            fig31.update_layout(margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})

            return fig31
        except (TypeError, KeyError):
            pass


    @dashapp1.callback(
        Output('regression-graph', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            ticker1 = input_value
            regressiondf = pd.DataFrame()
            regressiondf['Year'] = df_income.loc[ticker1]['Year']
            regressiondf['Cash'] = df_cashflow.loc[ticker1]['Cash from Operating'] + df_cashflow.loc[ticker1][
                'Capital Expenditure']
            X = regressiondf['Year'].values.reshape(-1, 1)

            model1 = LinearRegression()
            model1.fit(X, regressiondf['Cash'])

            x_range = np.linspace(X.min(), X.max(), 100)
            x_range1 = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
            y_range = model1.predict(x_range.reshape(-1, 1))

            for degree in [1, 2, 3, 4]:
                poly = PolynomialFeatures(degree)
                poly.fit(X)
                X_poly = poly.transform(X)
                x_range_poly = poly.transform(x_range1)

                model = LinearRegression(fit_intercept=False)
                model.fit(X_poly, regressiondf['Cash'])
                y_poly = model.predict(x_range_poly)

            fig32 = px.scatter(regressiondf, x='Year', y='Cash',
                               opacity=0.65)  # trendline='ols', trendline_color_override='darkblue'
            fig32.add_traces(go.Scatter(x=x_range, y=y_range, name='Regression Fit'))
            fig32.add_traces(go.Scatter(x=x_range.squeeze(), y=y_poly, name='Polynomial Fit'))
            fig32.update_layout(margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
            fig32.update_layout(legend=dict(x=0, y=1,
                                            traceorder="normal",
                                            font=dict(family="sans-serif", size=12, color="black"),
                                            bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)",
                                            borderwidth=0))
            return fig32
        except (TypeError, KeyError):
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


    @dashapp1.callback(Output('modal4', 'style'),
                       [Input('instructions-button4', 'n_clicks')])
    def show_modal(n):
        if n > 0:
            return {"display": "block"}
        return {"display": "none"}


    @dashapp1.callback(Output('instructions-button4', 'n_clicks'),
                       [Input('modal-close-button4', 'n_clicks')])
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
