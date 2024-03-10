# package imports
from bs4 import BeautifulSoup
from cachetools import cached
from contextlib import closing
from diskcache import Cache
import pandas as pd
from requests import get, post

cache_dir = ".cache"
disk_cache = Cache(cache_dir)

base_url = 'https://limitlesstcg.com'
tour_url = f'{base_url}/tournaments/jp?show=100'


def card_raw_to_id(set_code, number):
    """Convert raw code to card id

    Parameters
    ----------
    raw: dict
        Card as seen in database {'name': 'x', 'set': 'y', 'number': 1}

    Returns
    ----------
    card_id: str
        Cards official ID number (set-number)
    """

    try:
        num_int = int(number)
        # TODO figure out a better way to handle this set, there are only 2 digits
        if set_code.startswith('ST') and set_code != 'STS':
            num_int = f'{num_int:02}'
        else:
            num_int = f'{num_int:03}'

    except ValueError:
        num_int = number

    return f'{set_code}-{num_int}'


def get_html(url):
    """ scrapes a webpage and returns the beautified soup """
    with closing(get(url, stream=True)) as resp:
        return BeautifulSoup(resp.content, 'html.parser')


def extract_table_rows(html, class_name):
    """ extract the table from beautiful soup data given class name """
    table = html.find('table', {'class': class_name})
    rows = table.findAll('tr')
    del rows[0]
    return rows


def fetch_tour_info(row):
    cells = row.findAll('td')
    date = cells[0].get_text()
    url = cells[2].find('a')['href']
    name = cells[2].get_text().strip()
    ret = {'date': date, 'url': url, 'id': url.split('/')[-1], 'name': name}
    return ret


def fetch_row_info(row):
    """ given a row, fetch information """
    cells = row.findAll('td')
    placement = int(cells[0].get_text())
    name = cells[1].get_text().strip()
    decklist_cell = cells[-1].find('a')
    decklist_url = decklist_cell['href'] if decklist_cell else None
    return placement, decklist_url, name


def fetch_decklist(url):
    """ fetch a decklist from a given url """
    html = get_html(url)
    price_html = html.find('span', {'class': 'decklist-price card-price usd'})
    price = float(price_html.get_text().replace('$', ''))
    soup_cards = html.findAll('div', {'class': 'decklist-card'})
    cards = []
    for soup_card in soup_cards:
        cards.append(
            {
                'number': soup_card['data-number'],
                'set': soup_card['data-set'],
                'count': int(soup_card.find('span', {'class': 'card-count'}).get_text()),
                'name': soup_card.find('span', {'class': 'card-name'}).get_text()
            }
        )
    return cards, price


def get_tournaments(page=1):
    paged_url = f'{tour_url}&page={page}'
    tours_html = get_html(paged_url)
    tour_rows = extract_table_rows(tours_html, 'data-table')
    tours = []
    for row in tour_rows:
        tour = fetch_tour_info(row)
        tours.append(tour)
    return tours


def get_tournaments_paginate():
    page = 1
    tours = []
    while True:
        paged_tours = get_tournaments(page)
        if len(paged_tours) == 0:
            break
        tours.extend(paged_tours)
        page += 1
    return tours


@cached(cache=disk_cache)
def get_tour_decklists(url):
    html = get_html(url)
    rows = extract_table_rows(html, 'data-table')

    decks = []
    for row in rows:
        placement, decklist_url, name = fetch_row_info(row)
        if decklist_url:
            decklist, price = fetch_decklist(decklist_url)
            decks.append(
                {
                    'placing': placement,
                    'name': name,
                    'player': name,
                    'decklist': decklist,
                    'tour_id': url.split('/')[-1],
                    'deck_id': decklist_url.split('/')[-1]
                }
            )
        else:
            print('Missing decklist for ', placement)
    return decks


def get_decklists(urls):
    overall = []
    for url in urls:
        decklists = get_tour_decklists(url)
        overall.extend(decklists)
    return overall


def get_deck_from_limitless(decklist):
    """ Get the player decklist image """
    list_str = ''
    for card in decklist:
        card_str = str(card['count']) + ':' + card['set'] + '-' + card['number'] + '!1~int*en '
        list_str += card_str

    res = post(
        'https://limitlesstcg.com/tools/pnggen',
        data={
            'data': list_str,
            'game': 'PTCG',
            '_token': ''
        }
    )
    return res.content


def skeletal_analysis(decks):
    for d in decks:
        d['uid'] = f'{d["tour_id"]}-{d["deck_id"]}'
    raw = pd.json_normalize(decks, 'decklist', ['placing', 'uid'])
    if len(raw.index) == 0:
        return pd.DataFrame()

    def fetch_card(card):
        # card_keys = ['name', 'number', 'set']
        # matched_card = _cards.get_card(**{k: card[k] for k in card_keys})
        # card.update(matched_card)
        return card
    raw_counts = raw.groupby(
        ['number', 'set', 'count']
    ).agg(
        {
            'count': 'first',
            'name': 'first',
            'number': 'first',
            'set': 'first',
            'uid': 'count'
        }
    ).reset_index(
        drop=True
    ).rename(
        columns={'uid': 'decks'}
    )
    raw_counts = raw_counts.apply(fetch_card, axis=1)

    raw_counts = raw_counts.groupby(
        ['number', 'set', 'count']
    ).agg(
        {
            'count': 'first',
            'name': 'first',
            'number': 'first',
            'set': 'first',
            'decks': 'sum'
        }
    ).reset_index(
        drop=True
    )
    raw_counts['card_id'] = raw_counts['number'] + raw_counts['set']
    df = pd.DataFrame(
        columns=['card_code', 'name', 'number', 'set', 'count', 'decks']
    )

    # iterate over cards and format cards for new dataframe
    card_ids = raw_counts['card_id'].unique()
    for card_id in card_ids:
        card_obj = {}
        cards = raw_counts[raw_counts['card_id'] == card_id]
        max_decks = cards['decks'].sum()
        max_id = cards['decks'].idxmax()
        max_row = cards.loc[max_id]

        card_obj['card_code'] = card_raw_to_id(max_row['set'], max_row['number'])
        card_obj['name'] = max_row['name']
        card_obj['set'] = max_row['set']
        card_obj['number'] = max_row['number']
        card_obj['count'] = max_row['count']
        card_obj['counts'] = cards[['count', 'decks']].to_dict('records')
        card_obj['decks'] = max_decks
        # card_obj['card_type'] = fetch_card_type(max_row['name'])
        df = pd.concat([df, pd.DataFrame([card_obj])], ignore_index=True)

    max_decks = df['decks'].max()
    df['play_rate'] = df['decks'] / max_decks

    df.sort_values(by=['play_rate'], ascending=False, inplace=True, ignore_index=True)
    df['running_count'] = df['count'].cumsum()

    cutoff = (df['running_count'] < 61) & (df['play_rate'] >= 0.5)
    df.loc[
        cutoff,
        'skeleton'
    ] = True
    cutoff_index = cutoff[~cutoff].index[0]

    df = df.iloc[:cutoff_index + 40, ]
    df['skeleton'] = df['skeleton'].fillna(False)

    return df


def placement_analysis(decks):
    placements = {}
    for d in decks:
        p = d['placing']
        if p not in placements:
            placements[p] = 0
        placements[p] += 1
    return placements


if __name__ == '__main__':
    tours = get_tournaments()
    for tour in tours:
        print(tour)
        decks = get_tour_decklists(tour['url'])
        for deck in decks:
            print(deck)
            break
        break
