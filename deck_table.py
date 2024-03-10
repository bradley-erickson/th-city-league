from dash import html, dcc
import dash_bootstrap_components as dbc
import math
import pandas as pd
import plotly.express as px

import colors

ptcg_card_url = 'https://limitlesstcg.nyc3.digitaloceanspaces.com'

def get_card_image(card_code, size):
    if not card_code:
        return ''
    card_code = card_code.replace('PR-SW', 'SSP')
    card_code = card_code.replace('PR-SV', 'SVP')
    set_code, number = card_code.split('-', 1)

    card_origin = 'tpc' if (set_code.startswith('SV') and set_code[2].isdigit()) or set_code == 'SVHM' else 'tpci'
    lang = 'EN'
    if card_origin == 'tpc':
        lang = 'JP'
        number = number.lstrip('0')
    source = f'{ptcg_card_url}/{card_origin}/{set_code}/{set_code}_{number}_R_{lang}_{size}.png'
    return source


color_breakdown = colors.blue
color_inclusion = colors.red

def create_grid_item(card, total):
    id = card['card_code']
    play_rate = sum(x['decks'] for x in card.get('counts')) / total

    df = pd.DataFrame(
        data={
            'count': [c['count'] for c in card.get('counts')],
            'play_rate': [c['decks']/total for c in card.get('counts')]
        }
    )
    max_num = df.loc[df.play_rate.idxmax()]['count']
    df = df[df['count'] > 0]
    df.dropna(inplace=True)

    figure = px.bar(
        df, x='count', y='play_rate',
        color_discrete_sequence=[color_breakdown],
        labels=dict(count='', play_rate=''),
    )
    figure.update_layout(
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=0, r=0, b=0, t=0),
    )
    figure.update_xaxes(
        showgrid=False,
        title=None,
        type='category',
    )
    figure.update_yaxes(
        showticklabels=False,
        title=None,
        range=[0, 1.2],
        showgrid=False
    )

    item = dbc.Col([
        html.Img(src=get_card_image(id, 'SM'), className='w-100'),
        html.Div(
            dcc.Graph(
                figure=figure,
                config={'staticPlot': True},
                className='bg-white rounded h-100 w-100 bg-blur'
            ),
            className='position-absolute bottom-0 h-50 start-0 end-0 m-1'
        ),
        html.Div(
            dbc.Progress(
                value=play_rate*100, label=f'{play_rate:.1%}',
                class_name='w-100',
                color=color_inclusion
            ),
            className='position-absolute bottom-40 p-2 w-100'
        ),
        dbc.Badge(
            int(max_num),
            class_name='position-absolute top-0 end-0 m-2 mt-3 rounded-circle font-monospace border border-light',
        )
    ], className='position-relative', id=id, xs=4, sm=3, md=2, lg=2, xxl=1)
    return item

def create_grid_layout(cards, total):
    skeleton_count = sum(c['count'] for c in cards if c['skeleton'])
    row = dbc.Row([
        html.H5(['Skeleton', dbc.Badge(skeleton_count, className='ms-1')]),
        dbc.Row([create_grid_item(card, total) for card in cards if card['skeleton']], className='g-1 mb-1'),
        html.H5('Other cards'),
        dbc.Row([create_grid_item(card, total) for card in cards if not card['skeleton']], className='g-1')
    ])
    return row

def create_list_item(card, max_count, total, i):
    id = card['card_code']
    color = colors.red_gradient[math.floor(card['play_rate']*100)]

    hover_bars = [
        dbc.Label('Overall'),
        dbc.Progress(value=card['play_rate'], max=1, color=color_inclusion),
    ]

    counts = [html.Td()]*max_count
    for count in sorted(card['counts'], key=lambda d: d['count']):
        c = count['count']
        c_value = count["decks"] / total
        c_color = colors.blue_gradient[math.floor(c_value * 100)]
        counts[c-1] = html.Td(
            html.Span(f'{c_value:.1%}', className='d-none d-md-inline'),
            style={'backgroundColor': c_color},
            className='text-end'
        )
        hover_bars.append(dbc.Label(f'{c} cop{"ies" if c > 1 else "y"}'))
        hover_bars.append(dbc.Progress(value=c_value, max=1, color=color_breakdown))

    cells = [
        dbc.Popover(
            dbc.PopoverBody(dbc.Row([
                dbc.Col(
                    html.Img(src=get_card_image(id, 'SM'), className='w-100'),
                    width=6
                ),
                dbc.Col(hover_bars)
            ])),
            target=id,
            trigger='hover',
            placement='bottom'
        ),
        html.Td(i+1),
        html.Td(f"{card['name']} {card['card_code']}", className='w-100'),
        html.Td(
            html.Span(f'{card["play_rate"]:.1%}', className='d-none d-md-inline'),
            style={'backgroundColor': color},
            className='text-end')
    ]
    cells.extend(counts[:4])
    row = html.Tr(cells, id=id)
    return row

def create_list_layout(cards, total):
    max_count = max(count['count'] for card in cards for count in card['counts'])
    skeleton_count = sum(c['count'] for c in cards if c['skeleton'])
    skeleton = []
    other = []
    for i, card in enumerate(cards):
        if card['skeleton']:
            skeleton.append(create_list_item(card, max_count, total, i))
        else:
            other.append(create_list_item(card, max_count, total, i))

    headers = [html.Th(), html.Th('Card'), html.Th('Overall')] + [html.Th(i, className='text-end') for i in range(1, 5)]

    body = [html.Tr([
        html.Td(''),
        html.Td(['Skeleton', dbc.Badge(skeleton_count, className='ms-1')])
    ])] + skeleton + [html.Tr([
        html.Td(''),
        html.Td('Other')
    ])] + other

    table = dbc.Table([
        html.Thead(html.Tr(headers)),
        html.Tbody(body)
    ])
    return table

container_layout = {
    'grid': create_grid_layout,
    'list': create_list_layout
}
