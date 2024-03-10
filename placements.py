import pandas as pd
import plotly.express as px

def create_placement_graph(data, total):
    df = pd.DataFrame(list(data.items()), columns=['placement', 'count'])
    fig = px.bar(df, x='placement', y='count', title='Placements for filtered decks')
    fig.update_xaxes(dtick=1, fixedrange=True, title='Placement')
    fig.update_yaxes(fixedrange=True, range=[-5, total/16 + 5], title='Count')
    return fig
