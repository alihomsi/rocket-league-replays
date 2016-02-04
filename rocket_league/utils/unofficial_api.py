from django import template
from django.conf import settings

from ..apps.users.models import LeagueRating

import os
import re
import requests
import time

register = template.Library()

API_BASE = 'https://psyonix-rl.appspot.com'
API_VERSION = '105'


def api_login():

    HEADERS = {
        'DBVersion': '00.03.0011-00.01.0011',
        'LoginSecretKey': 'dUe3SE4YsR8B0c30E6r7F2KqpZSbGiVx',
        'CallProcKey': 'pX9pn8F4JnBpoO8Aa219QC6N7g18FJ0F',
        'DB': 'BattleCars_Prod',
    }

    login_data = {
        'PlayerName': "RocketLeagueReplays.com",
        'PlayerID': os.getenv('STEAM_ID'),
        'Platform': 'Steam',
        'BuildID': 64123161,
        'AuthCode': '1400000007975B47F1DEFD678CA3E50201001001F581785618000000010000000200000048FA925600000000B698010001000000BE0000003E000000040000008CA3E5020100100116DC03003352A75664C0FEA900000000457E7856C52D94560100E4780000020000FA05000000B22E0600000000006CFF6B550F2F82520844764F624C679B4FC142A0736366E063CD4031788A853D9DB99551F3EF9C71F3B91AC7F8257C63BB4AF2250F8C4EEFD9583F121EBA6ADE224E52594128BB9FC714F167C82FE785921348B1907FB719DF2A6BB2D48482B489F190633FCC135D4C60987AC8F25E613859D8C3308D6BF48E4175F28C46D3CF',
    }

    r = requests.post(API_BASE + '/auth/'.format(API_VERSION), headers=HEADERS, data=login_data)

    if r.text.strip() == 'SCRIPT ERROR PlatformAuthError:':
        # Wait a few seconds and try again.
        print 'Hit PlatformAuthError, trying again in 5 seconds.'
        time.sleep(5)
        return api_login()

    elif r.text != '1':
        raise Exception("Unable to login.")

    HEADERS['SessionID'] = r.headers['sessionid']

    return HEADERS






def get_league_data(steam_ids):
    """
    Playlist=0&Mu=20.6591&Sigma=4.11915&RankPoints=100
    Playlist=10&Mu=27.0242&Sigma=2.96727&RankPoints=292
    Playlist=11&Mu=37.0857&Sigma=2.5&RankPoints=618
    Playlist=12&Mu=35.8244&Sigma=2.5&RankPoints=500
    Playlist=13&Mu=33.5018&Sigma=2.5&RankPoints=468
    """

    all_steam_ids = list(steam_ids)

    for steam_ids in chunks(all_steam_ids, 10):
        data = {
            'Proc[]': [
                'GetPlayerSkillAndRankPointsSteam'
            ] * len(steam_ids),
        }

        for index, steam_id in enumerate(steam_ids):
            data['P{}P[]'.format(index)] = [str(steam_id)]

        headers = api_login()
        r = requests.post(
            API_BASE + '/callproc{}/'.format(API_VERSION),
            headers=headers,
            data=data
        )

        if r.text.strip() == 'SCRIPT ERROR SessionNotActive:':
            print 'Hit SessionNotActive'
            continue

        # Split the response into individual chunks.
        response_chunks = r.text.strip().split('\r\n\r\n')

        for index, response in enumerate(response_chunks):
            print 'Getting rating data for', steam_ids[index]
            matches = re.findall(r'Playlist=(\d+)&.+RankPoints=(\d+)', response)

            if not matches:
                print 'no matches'

            matches = dict(matches)

            # Store this, cache it, do something with it.
            LeagueRating.objects.create(
                steamid=steam_ids[index],
                duels=matches.get(str(settings.PLAYLISTS['RankedDuels']), 0),
                doubles=matches.get(str(settings.PLAYLISTS['RankedDoubles']), 0),
                solo_standard=matches.get(str(settings.PLAYLISTS['RankedSoloStandard']), 0),
                standard=matches.get(str(settings.PLAYLISTS['RankedStandard']), 0),
            )


def chunks(input_list, chunk_length):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(input_list), chunk_length):
        yield input_list[i:i+chunk_length]
