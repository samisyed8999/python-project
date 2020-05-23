import dash_table
from dash.dependencies import Output, Input, State

def register_callbacks(dashapp1):
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
            columns =[{"name": i, "id": i} for i in df1.columns]
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
            columns =[{"name": i, "id": i} for i in df2.columns]
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
            columns =[{"name": i, "id": i} for i in df3.columns]
            return columns
