import os
import math
import pickle
from time import sleep

import googlemaps
from dotenv import load_dotenv

from bracket import Bracket


def get_stadium_locations(client, team_names):
    coords = {}
    for team in team_names:
        query = f'{team} Basketball Stadium'
        rsp = client.places(query)
        try:
            geo = rsp['results'][0]['geometry']['location']
        except IndexError as ex:
            print(f'Failed with team {team}')
            print(rsp['results'])
            raise ex

        coords[team] = (geo['lat'], geo['lng'])
        sleep(0.25)
    return coords


def haversine(lat1, lng1, lat2, lng2):
    """
    Calculate the great circle distance between two points using the Haversine formula

    Params:
        lat1 (float): latitude of point 1 
        lng1 (float): longitude of point 1 
        lat2 (float): latitude of point 2 
        lng2 (float): longitude of point 2

    Returns:
        dist (float): distance between two points 
    """
    EARTH_RADIUS_KM = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * \
        math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return EARTH_RADIUS_KM * c


def get_nearest_waffle_house(client, stadium_coords):
    """
    Gets distance between stadium and its nearest Waffle House. Distances are 
    calculated by the Haversine formula (i.e. as the crow flies) as opposed 
    to true travel distance

    Params:
        client: Google Maps client
        stadium_coords (dict[str, tuple]), latitude and longitude of each team's stadium

    Returns:
        distances (dict[str, float]): distances in km to nearest Waffle House 
    """

    def is_waffle_house_establishment(place):
        """
        The Nearby API will return other waffle-themed restaurants if there is no Waffle House nearby
        Determines if place is indeed a Waffle House

        Params:
            place (dict): place, as part of the Nearby API's result field

        Returns:
            is_waffle_house (bool): Is place a Waffle House?
        """

        name = place.get('name', '').strip().lower()
        if not name:
            return False

        # Only allow the Waffle House chain name variants.
        valid_name = (
            name == 'waffle house'
            or name.startswith('waffle house')
        )
        if not valid_name:
            return False

        # Check that, if place type is provided, place is a restaurant
        types = set(place.get('types', []))
        if types and 'restaurant' not in types and 'food' not in types:
            return False

        return True

    distances = {}
    known_waffle_houses = []

    for team, (lat, lng) in stadium_coords.items():
        rsp = client.places_nearby(
            location=(lat, lng),
            name='Waffle House',
            type='restaurant',
            rank_by='distance',
        )

        best_dist = math.inf
        while True:
            results = rsp.get('results', [])
            for place in results:
                if not is_waffle_house_establishment(place):
                    continue

                geo = place.get('geometry', {}).get('location', {})
                wh_lat = geo.get('lat')
                wh_lng = geo.get('lng')
                if wh_lat is None or wh_lng is None:
                    continue

                known_waffle_houses.append((wh_lat, wh_lng))

                dist = haversine(lat, lng, wh_lat, wh_lng)
                if dist < best_dist:
                    best_dist = dist

            next_page = rsp.get('next_page_token')
            if not next_page:
                break

            # Google Places requires a short delay before fetching next page.
            sleep(2)
            rsp = client.places_nearby(page_token=next_page)

        if best_dist == math.inf:
            print(f'No Waffle House found for team: {team}')
        else:
            print(f'Nearest Waffle House for {team} is {best_dist} km')
        distances[team] = best_dist

    # The Nearby API is limited to a 50km search radius, so some teams don't have Waffle Houses
    # As a fallback, compute the shortest distance to the set of Waffle Houses we've seen nationwide
    if known_waffle_houses:
        # Deduplicate with light rounding to prevent repeated coordinates.
        # Three decimal places has about a ~100m fidelity
        unique_waffle_houses = {
            (round(wh_lat, 3), round(wh_lng, 3)) for wh_lat, wh_lng in known_waffle_houses
        }

        for team, (lat, lng) in stadium_coords.items():
            if not math.isinf(distances[team]):
                continue

            best_dist = min(
                haversine(lat, lng, wh_lat, wh_lng)
                for wh_lat, wh_lng in unique_waffle_houses
            )
            distances[team] = best_dist
            print(
                f'Fallback nearest Waffle House for {team} is {best_dist} km '
                '(estimated from discovered locations)'
            )

    return distances


def construct_bracket(team_info, distances):
    bracket_info = {
        'east': 16 * [None],
        'west': 16 * [None],
        'midwest': 16 * [None],
        'south': 16 * [None],
    }

    for team, (seed, region) in team_info.items():
        bracket_info[region][seed-1] = {
            'name': team,
            'distance': distances[team]
        }

    return Bracket(bracket_info)


def main(teams_file):
    with open(teams_file, 'rb') as fp:
        team_info = pickle.load(fp)

    load_dotenv()
    GMAPS_API_KEY = os.environ.get('GMAPS_API_KEY')
    assert GMAPS_API_KEY is not None, "Missing API key"

    client = googlemaps.Client(GMAPS_API_KEY)
    stadium_coords = get_stadium_locations(client, list(team_info.keys()))
    wh_distances = get_nearest_waffle_house(client, stadium_coords)

    bracket = construct_bracket(team_info, wh_distances)
    bracket.play()
    res = bracket.get_results()
    for match in res:
        print(match)


if __name__ == '__main__':
    TEAMS_FILE = './teams.pkl'
    main(TEAMS_FILE)
