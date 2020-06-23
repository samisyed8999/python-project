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

    # income statement
    df_income = sf.load(dataset='income', variant='annual', market='us', index=[TICKER])
    df_income = df_income.drop(['Currency', 'SimFinId', 'Fiscal Period', 'Publish Date', 'Shares (Basic)',
                                'Abnormal Gains (Losses)', 'Net Extraordinary Gains (Losses)',
                                'Income (Loss) from Continuing Operations',
                                'Net Income (Common)', 'Pretax Income (Loss), Adj.', 'Report Date', 'Restated Date'], axis=1)
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
    df1 = df_income.loc[ticker].copy()
    # restated date
    df_names = df_income.index.copy()
    df_names = df_names.drop_duplicates()

    # income growth per year
    df1_growth = pd.DataFrame(index=df1.index)
    df1_growth['Year'] = df1['Year'].copy()
    df1_growth['Revenue Growth'] = df1['Revenue'].pct_change().mul(100).round(2).copy()
    df1_growth['Profit Growth'] = df1['Gross Profit'].pct_change().mul(100).round(2).copy()
    df1_growth['Operating Income Growth'] = df1['Operating Income'].pct_change().mul(100).round(2).copy()
    df1_growth['Pretax Income Growth'] = df1['Pretax Income'].pct_change().mul(100).round(2).copy()
    df1_growth['Net Income Growth'] = df1['Net Income'].pct_change().mul(100).round(2).copy()
    df1_growth = df1_growth.fillna(0)

    # compounded income growth
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

    df_income_compound = pd.DataFrame()
    df_income_compound['Net Income %'] = [income_growth_percent]
    df_income_compound['Pre tax %'] = [pretax_growth_percent]
    df_income_compound['Operating Income %'] = [operating_growth_percent]
    df_income_compound['Gross Profit %'] = [profit_growth_percent]
    df_income_compound['Revenue %'] = [revenue_growth_percent]

    # income signals
    df_negative = df_income.copy()
    df_negative[['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']] = \
        df_negative[
            ['Cost of Revenue', 'R&D', 'Operating Expenses', 'SGA', 'Income Tax', 'D&A', 'Interest Expense']].apply(
            lambda x: x * -1)
    df_negative['Expenses'] = df_negative['Operating Expenses'] + df_negative['SGA'] + df_negative['R&D'] + \
                              df_negative['D&A']
    df11 = df_negative.loc[ticker]
    df_signals = pd.DataFrame(index=df_negative.index)
    df_signals['Year'] = df_negative['Year'].copy()
    df_signals['Gross Profit Margin %'] = round((df_negative['Gross Profit'] / df_negative['Revenue']) * 100,
                                                2).copy()
    df_signals['SGA Of Gross Profit'] = round((df_negative['SGA'] / df_negative['Gross Profit']) * 100, 2).copy()
    df_signals['R&D Of Gross Profit'] = round((df_negative['R&D'] / df_negative['Gross Profit']) * 100, 2).copy()
    df_signals['Operating margin ratio'] = round((df_negative['Operating Income'] / df_negative['Revenue']) * 100,
                                                 2).copy()
    df_signals['Interest Coverage'] = round((df_negative['Operating Income'] / df_negative['Interest Expense']),
                                            2).copy()
    df_signals['Taxes paid'] = round((df_negative['Income Tax'] / df_negative['Pretax Income']) * 100, 2).copy()
    df_signals['Net income margin'] = round((df_negative['Net Income'] / df_negative['Revenue']) * 100, 2).copy()
    df_signals['Interest Coverage'] = df_signals['Interest Coverage'].replace(-np.inf, 0)
    df2 = df_signals.loc[ticker]

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
    ticker = 'AAPL'
    df3 = df_balance.loc[ticker]

    # balance signals
    df_balance_signals = pd.DataFrame(index=df_balance.index)
    df_balance_signals['Year'] = df_balance['Year'].copy()
    df_balance_signals['Return on Assets%'] = round((df_income['Net Income'] / df_balance['Total Assets']) * 100, 2).copy()
    df_balance_signals['Return on EquityT%'] = round(
        (df_income['Net Income'] / (df_balance['Total Equity'] + (-1 * df_balance['Treasury Stock']))) * 100, 2).copy()
    df_balance_signals['Current Ratio'] = round((df_balance['Current Assets'] / df_balance['Current Liabilities']),
                                                2).copy()
    df_balance_signals['Retained Earning to Equity%'] = round(
        (df_balance['Retained Earnings'] / df_balance['Total Equity']) * 100, 2).copy()
    df_balance_signals['Debt to EquityT%'] = round(
        (df_balance['Total Liabilities'] / (df_balance['Total Equity'] + (-1 * df_balance['Treasury Stock']))) * 100,
        2).copy()
    df_balance_signals['Receivables of Revenue%'] = round((df_balance['Accounts Receivable'] / df_income['Revenue']) * 100,
                                                          2).copy()
    df_balance_signals['PP&E of Assets%'] = round((df_balance['Prop Plant & Equipment'] / df_balance['Total Assets']) * 100,
                                                  2).copy()
    df_balance_signals['Inventory of Assets%'] = round((df_balance['Inventory & Stock'] / df_balance['Total Assets']) * 100,
                                                       2).copy()
    df_balance_signals['Long Term Debt Coverage'] = round((df_income['Net Income'] / df_balance['LongTerm Debts']),
                                                          2).copy()
    df_balance_signals['Long Term Debt Coverage'] = df_balance_signals['Long Term Debt Coverage'].replace([np.inf, -np.inf],
                                                                                                          0)
    df4 = df_balance_signals.loc[ticker]

    # graphs
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

    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Expenses']), name="Expenses"))
    fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Operating Income']), name="Operating Income"))
    fig3.add_trace(go.Scatter(x=list(df11['Year']), y=list(df11['Gross Profit']), name="Gross Profit"))
    fig3.update_layout(legend=dict(x=0, y=1,
                                   traceorder="normal",
                                   font=dict(family="sans-serif", size=12, color="black"),
                                   bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig3.update_layout(
        title={'text': "Gross Profit to Operating Income", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
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
    fig4.update_layout(
        title={'text': "Measuring Interest Expense", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
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
    fig7.update_layout(
        title={'text': "Gross Profit Margin %", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig7.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig7.update_yaxes(rangemode="tozero")

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
        go.Scatter(x=list(df2['Year']), y=list(df2['Interest Coverage']), name="interest-coverage",
                   line=dict(color='#00cc96')))
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

    fig13 = make_subplots(specs=[[{"secondary_y": True}]])
    fig13.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Cash & Equivalent']), name="Cash & Equivalent"))
    fig13.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Accounts Receivable']), name="Accounts Receivables"))
    fig13.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Inventory & Stock']), name="Inventory"))
    fig13.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Current Assets']), name="Current_Assets"))
    fig13.update_layout(legend=dict(x=0, y=1,
                                    traceorder="normal",
                                    font=dict(family="sans-serif", size=12, color="black"),
                                    bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig13.update_layout(title={'text': "Liquidity", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig13.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig13.update_yaxes(rangemode="tozero")

    #
    fig14 = make_subplots(specs=[[{"secondary_y": True}]])
    fig14.add_trace(
        go.Scatter(x=list(df3['Year']), y=list(df3['Prop Plant & Equipment']), name="Prop Plant & Equipment"))
    fig14.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Long Term Investments']), name="Long Term Investments"))
    fig14.add_trace(
        go.Scatter(x=list(df3['Year']), y=list(df3['Other Long Term Assets']), name="Other Long Term Assets"))
    fig14.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Noncurrent assets']), name="Non current Assets"))
    fig14.update_layout(legend=dict(x=0, y=1,
                                    traceorder="normal",
                                    font=dict(family="sans-serif", size=12, color="black"),
                                    bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig14.update_layout(
        title={'text': "Non Current Assets", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig14.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig14.update_yaxes(rangemode="tozero")

    fig15 = make_subplots(specs=[[{"secondary_y": True}]])
    fig15.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Total Assets']), name="Assets"))
    fig15.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Total Liabilities']), name="Liabilities"))
    fig15.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Total Equity']), name="Equity"))
    fig15.update_layout(legend=dict(x=0, y=1,
                                    traceorder="normal",
                                    font=dict(family="sans-serif", size=12, color="black"),
                                    bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig15.update_layout(title={'text': "Balance", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig15.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig15.update_yaxes(rangemode="tozero")

    fig16 = make_subplots(specs=[[{"secondary_y": True}]])
    fig16.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Accounts Payable']), name="Accounts Payable"))
    fig16.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['ShortTerm debts']), name="Short Term Debts"))
    fig16.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['Current Liabilities']), name="Current Liabilities"))
    fig16.update_layout(legend=dict(x=0, y=1,
                                    traceorder="normal",
                                    font=dict(family="sans-serif", size=12, color="black"),
                                    bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig16.update_layout(title={'text': "Current Debts", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig16.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig16.update_yaxes(rangemode="tozero")

    fig17 = make_subplots(specs=[[{"secondary_y": True}]])
    fig17.add_trace(go.Scatter(x=list(df3['Year']), y=list(df3['LongTerm Debts']), name="Long Term Debts"))
    fig17.add_trace(
        go.Scatter(x=list(df3['Year']), y=list(df3['Noncurrent Liabilities']), name="Non Current Liabilities"))
    fig17.update_layout(legend=dict(x=0, y=1,
                                    traceorder="normal",
                                    font=dict(family="sans-serif", size=12, color="black"),
                                    bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig17.update_layout(title={'text': "Non Current Debts", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig17.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig17.update_yaxes(rangemode="tozero")

    fig18 = make_subplots()
    fig18.add_trace(
        go.Scatter(x=list(df2['Year']), y=list(df3['Retained Earnings']), name="retained", line=dict(color='#00cc96')))
    fig18.update_layout(legend=dict(x=0, y=1,
                                    traceorder="normal",
                                    font=dict(family="sans-serif", size=12, color="black"),
                                    bgcolor="rgba(50, 50, 50, 0)", bordercolor="rgba(50, 50, 50, 0)", borderwidth=0))
    fig18.update_layout(
        title={'text': "Retained Earnings", 'y': 0.96, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
    fig18.update_layout(margin={'t': 25, 'b': 0, 'l': 0, 'r': 0})
    fig18.update_yaxes(rangemode="tozero")


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
                   href='https://financial8999.herokuapp.com/logout/'),
            html.Img(src= dashapp1.get_asset_url('stock-icon.png')),
        ], className="banner"),

        html.Div([
            dcc.Dropdown(id='drop-down', options=[
                {'label': i, 'value': i} for i in df_names
            ], value=ticker, multi=False, placeholder='Enter a ticker'),
        ], className='drops'),

        dcc.Tabs(id="tabs", value='Tab2', className='custom-tabs-container', children=[
            dcc.Tab(label='Portfolio tracker', id='tab1', value='Tab1', selected_className='custom-tab--selected',
                    children=[

                    ]),
            dcc.Tab(label='Financial Statements', id='tab2', value='Tab2', selected_className='custom-tab--selected',
                    children=[
                        dcc.Tabs(className='sub-tab-container', children=[
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

                                dash_table.DataTable(
                                    # style_cell={
                                    #     'whiteSpace': 'normal',
                                    #     'height': 'auto',
                                    # },
                                    style_table={
                                        'width': '95%',
                                        'margin': '20px 20px 0px'

                                    },
                                    id='income_compound_table',
                                    columns=[{"name": i, "id": i} for i in df_income_compound.columns],
                                    data=df_income_compound.to_dict('records'),
                                ),

                                html.Div([
                                    dcc.Graph(id='sales', config={'displayModeBar': False}, figure=fig1, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        "margin-left": "20px"
                                    }),

                                    dcc.Graph(id='costs', config={'displayModeBar': False}, figure=fig2, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        # "margin-left":"-100px"
                                    }),

                                    dcc.Graph(id='operating', config={'displayModeBar': False}, figure=fig3, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        "display": "inline-block",
                                        # "margin-left":"-100px"
                                    }),

                                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),
                                html.Div([
                                    dcc.Graph(id='interest', config={'displayModeBar': False}, figure=fig4, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        "margin-left": "20px"

                                    }),

                                    dcc.Graph(id='tax', config={'displayModeBar': False}, figure=fig5, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        'display': 'inline-block'

                                    }),

                                    dcc.Graph(id='shares', config={'displayModeBar': False}, figure=fig6, style={

                                        "height": "40vh",
                                        "width": "30vw",
                                        "float": "left",
                                        'display': 'inline-block'

                                    }),

                                ], style={"height": "50vh", "width": "98vw", "margin-top": "-20px"}),

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
                                    dcc.Graph(id='profit-margin', config={'displayModeBar': False}, figure=fig7, style={

                                        "height": "40vh",
                                        "width": "31vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        "margin-left": "20px"
                                    }),

                                    dcc.Graph(id='SGA', config={'displayModeBar': False}, figure=fig8, style={

                                        "height": "40vh",
                                        "width": "31vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        "margin-left": "20px"
                                    }),

                                    dcc.Graph(id='R&D', config={'displayModeBar': False}, figure=fig9, style={

                                        "height": "40vh",
                                        "width": "30vw",
                                        "float": "left",
                                        "display": "inline-block",
                                        "margin-left": "20px"
                                    }),

                                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),
                                html.Div([
                                    dcc.Graph(id='operating-margin-ratio', config={'displayModeBar': False}, figure=fig10,
                                              style={

                                                  "height": "40vh",
                                                  "width": "32vw",
                                                  "float": "left",
                                                  'display': 'inline-block',
                                                  "margin-left": "20px"

                                              }),

                                    dcc.Graph(id='interest-coverage', config={'displayModeBar': False}, figure=fig11,
                                              style={

                                                  "height": "40vh",
                                                  "width": "32vw",
                                                  "float": "left",
                                                  'display': 'inline-block'

                                              }),

                                    dcc.Graph(id='taxes-paid', config={'displayModeBar': False}, figure=fig12, style={

                                        "height": "40vh",
                                        "width": "30vw",
                                        "float": "left",
                                        'display': 'inline-block'

                                    }),

                                ], style={"height": "50vh", "width": "98vw", "margin-top": "-20px"}),

                                dash_table.DataTable(
                                    style_table={
                                        'width': '95%',
                                        'margin': '0px 20px 0px'
                                    },
                                    id='table_growth',
                                    columns=[{"name": i, "id": i} for i in df1_growth.columns],
                                    data=df1_growth.to_dict('records'),
                                ),

                            ]),
                            dcc.Tab(label='Balance Sheet', selected_className='sub-tab', children=[
                                dash_table.DataTable(
                                    style_cell={
                                        'whiteSpace': 'normal',
                                        'height': 'auto',
                                    },
                                    style_table={
                                        'width': '95%',
                                        'margin': '20px 20px 0px'
                                    },
                                    id='table3',
                                    columns=[{"name": i, "id": i} for i in df3.columns],
                                    data=df3.to_dict('records'),
                                ),

                                html.Div([
                                    dcc.Graph(id='balance', config={'displayModeBar': False}, figure=fig15, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        "margin-left": "20px"
                                    }),

                                    dcc.Graph(id='liquidity', config={'displayModeBar': False}, figure=fig13, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        # "margin-left":"-100px"
                                    }),

                                    dcc.Graph(id='long-term-assets', config={'displayModeBar': False}, figure=fig14, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        "display": "inline-block",
                                        # "margin-left":"-100px"
                                    }),

                                ], style={"height": "50vh", "width": "98vw", "margin-top": "20px"}),
                                html.Div([
                                    dcc.Graph(id='current debts', config={'displayModeBar': False}, figure=fig16, style={

                                        "height": "40vh",
                                        "width": "32vw",
                                        "float": "left",
                                        'display': 'inline-block',
                                        "margin-left": "20px"
                                    }),

                                    dcc.Graph(id='non-current-debts', config={'displayModeBar': False}, figure=fig17,
                                              style={

                                                  "height": "40vh",
                                                  "width": "32vw",
                                                  "float": "left",
                                                  'display': 'inline-block',
                                                  # "margin-left":"-100px"
                                              }),

                                    dcc.Graph(id='retained-earnings', config={'displayModeBar': False}, figure=fig18,
                                              style={

                                                  "height": "40vh",
                                                  "width": "30vw",
                                                  "float": "left",
                                                  "display": "inline-block",
                                                  # "margin-left":"-100px"
                                              }),

                                ], style={"height": "50vh", "width": "98vw", "margin-top": "-20px"}),

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
                                    columns=[{"name": i, "id": i} for i in df4.columns],
                                    data=df4.to_dict('records'),
                                ),

                            ]),
                            dcc.Tab(label='Cash Flow statement ', selected_className='sub-tab', children=[]),
                        ])
                    ]),
            dcc.Tab(label='Intrinsic value estimations', id='tab3', value='Tab3', selected_className='custom-tab--selected',
                    children=["yo"]),
            dcc.Tab(label='Machine learning', id='tab4', value='Tab4', selected_className='custom-tab--selected',
                    children=["yo"]),
        ])
    ])

    # callback
    @dashapp1.callback(
        Output('table', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1 = df_income.loc[input_value]
            data = df1.to_dict("records")
            return data
        except:
            pass


    @dashapp1.callback(
        Output('table', 'columns'),
        [Input("drop-down", "value")])
    def update_columns(input_value):
        try:
            df1 = df_income.loc[input_value]
            columns = [{"name": i, "id": i} for i in df1.columns]
            return columns
        except:
            pass


    @dashapp1.callback(
        Output('income_compound_table', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df1 = df_income.loc[input_value]
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
            df_income_compound = pd.DataFrame()
            df_income_compound['Net Income %'] = [income_growth_percent]
            df_income_compound['Pre tax %'] = [pretax_growth_percent]
            df_income_compound['Operating Income %'] = [operating_growth_percent]
            df_income_compound['Gross Profit %'] = [profit_growth_percent]
            df_income_compound['Revenue %'] = [revenue_growth_percent]
            data = df_income_compound.to_dict("records")
            return data
        except:
            pass


    @dashapp1.callback(
        Output('income_compound_table', 'columns'),
        [Input("drop-down", "value")])
    def update_columns(input_value):
        try:
            df1 = df_income.loc[input_value]
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
            df_income_compound = pd.DataFrame()
            df_income_compound['Net Income %'] = [income_growth_percent]
            df_income_compound['Pre tax %'] = [pretax_growth_percent]
            df_income_compound['Operating Income %'] = [operating_growth_percent]
            df_income_compound['Gross Profit %'] = [profit_growth_percent]
            df_income_compound['Revenue %'] = [revenue_growth_percent]
            columns = [{"name": i, "id": i} for i in df_income_compound.columns]
            return columns
        except:
            pass


    @dashapp1.callback(
        Output('table2', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df2 = df_signals.loc[input_value]
            data = df2.to_dict("records")
            return data
        except:
            pass


    @dashapp1.callback(
        Output('table2', 'columns'),
        [Input("drop-down", "value")])
    def update_columns(input_value):
        try:
            df2 = df_signals.loc[input_value]
            columns = [{"name": i, "id": i} for i in df2.columns]
            return columns
        except:
            pass


    @dashapp1.callback(
        Output('table3', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df3 = df_balance.loc[input_value]
            data = df3.to_dict("records")
            return data
        except:
            pass

    @dashapp1.callback(
        Output('table3', 'columns'),
        [Input("drop-down", "value")])
    def update_columns(input_value):
        try:
            df3 = df_balance.loc[input_value]
            columns = [{"name": i, "id": i} for i in df3.columns]
            return columns
        except:
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
        except:
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
        except:
            pass


    @dashapp1.callback(
        Output('operating', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except:
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
        except:
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
        except:
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
        except:
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
        except:
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
        except:
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
        except:
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
        except:
            pass


    @dashapp1.callback(
        Output('interest-coverage', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
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
        except:
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
        except:
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
        except:
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
        except:
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
        except:
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
        except:
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
        except:
            pass


    @dashapp1.callback(
        Output('retained-earnings', 'figure'),
        [Input("drop-down", "value")])
    def update_fig(input_value):
        try:
            df3 = df_balance.loc[input_value]
            fig18 = make_subplots()
            fig18.add_trace(
                go.Scatter(x=list(df2['Year']), y=list(df3['Retained Earnings']), name="retained",
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
        except:
            pass


    @dashapp1.callback(
        Output('table4', 'data'),
        [Input("drop-down", "value")])
    def update_data(input_value):
        try:
            df4 = df_balance_signals.loc[input_value]
            data = df4.to_dict("records")
            return data
        except:
            pass


    @dashapp1.callback(
        Output('table4', 'columns'),
        [Input("drop-down", "value")])
    def update_columns(input_value):
        try:
            df4 = df_balance_signals.loc[input_value]
            columns = [{"name": i, "id": i} for i in df4.columns]
            return columns
        except:
            pass
   
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
