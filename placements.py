import pandas as pd
import plotly.express as px

def create_placement_graph(data):
    df = pd.DataFrame(list(data.items()), columns=['placement', 'count'])
    fig = px.bar(df, x='placement', y='count', title='Placements')
    fig.update_xaxes(dtick=1)
    return fig
