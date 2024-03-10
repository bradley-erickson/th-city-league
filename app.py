import dash
from dash import DiskcacheManager, html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import datetime
import diskcache

import helpers, deck_table, placements as _place

cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)
app = dash.Dash(
    __name__,
    background_callback_manager=background_callback_manager,
    external_stylesheets=[dbc.themes.FLATLY],
    title='City League Analysis'
)

select_dates = 'dates'
fetch_decks = 'fetch-btn'
cancel = 'cancel-btn'
progress_bar = 'progress'
decks_store = 'decks'

filters = 'filters'
include_cards = 'include'
exclude_cards = 'exclude'

analysis = 'analysis'
total_decks = 'total-decks'
inclusion_rate = 'inclusion-rate'
progress_analysis = 'analysis-progress'
skeleton = 'skeleton'
skeleton_type = 'skeleton-type'
placement_slider = 'placement-slider'
placements = 'placements'
table_clipboard = 'copy-to-clipboard'

app.layout = dbc.Container([
    html.H2('City League Result Analysis'),
    html.P(
        'Welcome to the Trainer Hill City League decklist analysis tool. '\
        'This demo tool caches results from Japanese City Leagues via '\
        'LimitlessTCG. If an event has not yet been cached on the server, '\
        'the initial fetching may take a few moments.'
    ),
    dbc.Row([
        html.H3('Date Range'),
        dbc.Col([
            dcc.DatePickerRange(
                id=select_dates,
                start_date=datetime.date.today() - datetime.timedelta(21),
                end_date=datetime.date.today(),
                min_date_allowed='2024-01-21'
            ),
            dbc.Button('Fetch decks', id=fetch_decks, class_name='mx-1'),
            dbc.Button('Cancel', id=cancel, color='danger')
        ], class_name='mb-1'),
        dbc.Col(dbc.Progress(value=0, id=progress_bar), width=12),
        dcc.Store(id=decks_store, data=[])
    ]),
    dbc.Row([
        html.H3('Deck filters'),
        dbc.Col([
            dbc.Label('Include Cards'),
            dcc.Dropdown(multi=True, id=include_cards, value=[])
        ], width=6),
        dbc.Col([
            dbc.Label('Exclude Cards'),
            dcc.Dropdown(multi=True, id=exclude_cards, value=[]),
        ], width=6),
        dbc.Col([
            dbc.Label('Minimum Placement'),
            dcc.Slider(
                id=placement_slider,
                min=1, max=16, step=None, value=16,
                marks={16: 'T16', 8: 'T8', 4: 'T4', 2: 'Finals', 1: 'Winner'}
            )
        ], width=6),
    ], id=filters),
    dbc.Row(dbc.Col([
        dbc.Progress(value=0, id=progress_analysis),
        html.H3('Analysis'),
        html.H4([
            'Total decks:',
            dbc.Badge(0, id=total_decks, class_name='mx-1'),
        ]),
        dbc.Label('Showing % of available decks'),
        dbc.Progress(id=inclusion_rate, value=0, color='danger'),
        dcc.Graph(id=placements, config={'displayModeBar': False}),
        dbc.Button(dcc.Clipboard(id=table_clipboard, content='None'), className='me-1', title='Copy Skeleton Decklist'),
        html.Span(dbc.RadioItems(
            id=skeleton_type,
            className='btn-group',
            inputClassName='btn-check',
            labelClassName='btn btn-outline-primary',
            labelCheckedClassName='active',
            options=[
                {'label': 'List', 'value': 'list'},
                {'label': 'Grid', 'value': 'grid'},
            ],
            value='grid',
        ), className='radio-group'),
        html.Div(id=skeleton)
    ], width=12), id=analysis)
], fluid=True)

@callback(
    Output(decks_store, 'data'),
    Input(fetch_decks, 'n_clicks'),
    State(select_dates, 'start_date'),
    State(select_dates, 'end_date'),
    running=[
        (Output(progress_bar, 'striped'), True, False),
        (Output(progress_bar, 'animated'), True, False),
        (Output(progress_bar, 'label'), 'Fetching decks...', 'Decks loaded.'),
        (Output(fetch_decks, 'disabled'), True, False),
        (Output(cancel, 'disabled'), False, True),
        (Output(filters, 'class_name'), 'd-none', ''),
        (Output(analysis, 'class_name'), 'd-none', ''),
    ],
    background=True,
    progress=[Output(progress_bar, 'value')],
    cancel=[Input(cancel, 'n_clicks')]
)
def update_decks(set_progress, n, start, end):
    if n is None:
        raise dash.exceptions.PreventUpdate
    tours = helpers.get_tournaments_paginate()
    total_tours = len(tours)
    decks = []
    for i, tour in enumerate(tours):
        set_progress((i+1)/total_tours * 100)
        tour_date_str = tour['date']
        tour_date_obj = datetime.datetime.strptime(tour_date_str, '%d %b %y')
        tour_date = tour_date_obj.strftime('%Y-%m-%d')
        if tour_date > end or tour_date < start:
            continue
        decklists = helpers.get_tour_decklists(tour['url'])
        decks.extend(decklists)
    return decks


@callback(
    Output(include_cards, 'options'),
    Output(exclude_cards, 'options'),
    Input(decks_store, 'data')
)
def update_card_options(decks):
    cards = {}
    for deck in decks:
        decklist = deck['decklist']
        for card in decklist:
            id = f'{card.get("set")}-{card.get("number")}'
            cards[id] = f'{card.get("name")} {id}'
    return cards, cards


def check_decklist(dl, include, exclude):
    cards = set(f'{card.get("set")}-{card.get("number")}' for card in dl)
    inset = set(include)
    exset = set(exclude)
    if len(exset.intersection(cards)) > 0:
        return False
    if inset.issubset(cards):
        return True
    return False


@callback(
    Output(total_decks, 'children'),
    Output(inclusion_rate, 'value'),
    Output(inclusion_rate, 'label'),
    Output(placements, 'figure'),
    Output(skeleton, 'children'),
    Output(table_clipboard, 'content'),
    Input(decks_store, 'data'),
    Input(include_cards, 'value'),
    Input(exclude_cards, 'value'),
    Input(skeleton_type, 'value'),
    Input(placement_slider, 'value'),
    running=[
        (Output(include_cards, 'disabled'), True, False),
        (Output(exclude_cards, 'disabled'), True, False),
        (Output(progress_analysis, 'animated'), True, False),
        (Output(progress_analysis, 'striped'), True, False),
        (Output(skeleton_type, 'disabled'), True, False),
        (Output(placement_slider, 'disabled'), True, False)
    ],
    background=True,
    progress=[Output(progress_analysis, 'value'), Output(progress_analysis, 'label')]
)
def update_filter_store(set_progress, decks, include, exclude, skel_type, min_place):
    set_progress((15, 'Filtering data...'))
    filtered = [d for d in decks if check_decklist(d['decklist'], include, exclude) and d['placing'] <= min_place]

    if len(filtered) == 0:
        set_progress((100, 'No decks found. Please change your filters.'))
        raise dash.exceptions.PreventUpdate
    
    set_progress((45, 'Calculating placements...'))
    placement_data = helpers.placement_analysis(filtered)
    place_out = _place.create_placement_graph(placement_data, len(decks))

    set_progress((75, 'Calculating Skeleton...'))
    skeletal_data = helpers.skeletal_analysis(filtered)
    records = skeletal_data.to_dict('records')
    output = deck_table.container_layout[skel_type](records, len(filtered))
    set_progress((100, 'Analysis finished.'))

    skel = [c for c in records if c['skeleton']]
    skeleton_list = '\n'.join((' '.join(str(c[k]) for k in ['count', 'name', 'set', 'number']) for c in skel))
    percent_inc = len(filtered)/len(decks)
    return len(filtered), percent_inc * 100, f'{percent_inc:.1%}', place_out, output, skeleton_list


server = app.server

if __name__ == '__main__':
    app.run(debug=True)
