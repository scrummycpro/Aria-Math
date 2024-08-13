import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import io
import base64
import plotly.express as px

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select a CSV File')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='output-data-upload'),
    html.Div(id='chart-options', style={'display': 'none'}),
    dcc.Dropdown(id='x-axis-dropdown', style={'width': '50%', 'display': 'none'}),
    dcc.Dropdown(id='y-axis-dropdown', style={'width': '50%', 'display': 'none'}),
    dcc.Dropdown(
        id='chart-type-dropdown',
        options=[
            {'label': 'Bar Chart', 'value': 'bar'},
            {'label': 'Line Chart', 'value': 'line'},
            {'label': 'Scatter Plot', 'value': 'scatter'}
        ],
        value='bar',
        style={'width': '50%', 'display': 'none'}
    ),
    dcc.Graph(id='chart-output')
])

def parse_contents(contents, filename):
    try:
        content_type, content_string = contents.split(',')

        # Decode the content string to get the file content
        decoded = base64.b64decode(content_string)
        # Use BytesIO to create a buffer and read it with pandas
        buffer = io.BytesIO(decoded)

        if 'csv' in filename:
            # Read the CSV file into a pandas DataFrame
            df = pd.read_csv(buffer)

            # Ensure correct data types for numeric columns
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except ValueError:
                    # If conversion fails, leave the column as is
                    pass

        else:
            return html.Div([
                'The file you uploaded is not a CSV file.'
            ]), None
        
        # Display the DataFrame as a table and pass the DataFrame to chart options
        return html.Div([
            html.H5(filename),
            html.Hr(),
            dash.dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[{'name': i, 'id': i} for i in df.columns],
                style_table={'overflowX': 'auto'}
            ),
            html.Hr(),  # horizontal line
        ]), df
    except Exception as e:
        return html.Div([
            f'There was an error processing this file: {str(e)}'
        ]), None

@app.callback(
    Output('output-data-upload', 'children'),
    Output('x-axis-dropdown', 'options'),
    Output('y-axis-dropdown', 'options'),
    Output('x-axis-dropdown', 'style'),
    Output('y-axis-dropdown', 'style'),
    Output('chart-type-dropdown', 'style'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_output(contents, filename):
    if contents is not None:
        parsed_contents, df = parse_contents(contents, filename)
        if df is not None:
            options = [{'label': col, 'value': col} for col in df.columns]
            return (parsed_contents, options, options,
                    {'width': '50%', 'display': 'block'},
                    {'width': '50%', 'display': 'block'},
                    {'width': '50%', 'display': 'block'})
    return 'No file uploaded yet.', [], [], {'display': 'none'}, {'display': 'none'}, {'display': 'none'}

@app.callback(
    Output('chart-output', 'figure'),
    Input('x-axis-dropdown', 'value'),
    Input('y-axis-dropdown', 'value'),
    Input('chart-type-dropdown', 'value'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_chart(x_axis, y_axis, chart_type, contents, filename):
    if contents is not None and x_axis and y_axis:
        _, df = parse_contents(contents, filename)
        if df is not None:
            # Handle different chart types
            if chart_type == 'bar':
                fig = px.bar(df, x=x_axis, y=y_axis)
            elif chart_type == 'line':
                fig = px.line(df, x=x_axis, y=y_axis)
            elif chart_type == 'scatter':
                fig = px.scatter(df, x=x_axis, y=y_axis)
            return fig
    return {}

if __name__ == '__main__':
    app.run_server(debug=True)
