from collections import OrderedDict
import datetime
import json
import os.path
import requests
import re
import time

import nflgame.update_sched

__pdoc__ = {}

_sched_json_file = os.path.join(os.path.dirname(__file__), 'schedule.json')

_CURRENT_WEEK_ENDPOINT = 'http://www.nfl.com/schedules/'
"""
Used to update the season state based on the url this gets redirected to
nfl.com/schedules/{current_year}/{phase}{week_number}/
"""
_cur_week = None
"""The current week. It is updated infrequently automatically."""

_cur_year = None
"""The current year. It is updated infrequently automatically."""

_cur_season_phase = 'PRE'
"""The current phase of the season."""

def _update_week_number():
    global _cur_week, _cur_year, _cur_season_phase

    # requests.get is throwing a 403 w/o setting the user agent
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
    curWeekResponse = requests.get(_CURRENT_WEEK_ENDPOINT, headers=headers)

    if (curWeekResponse.ok):
        schedule_details = curWeekResponse.url.split('/')
        week = re.findall(r'\d+', schedule_details[5])
        phase = re.findall(r'\w+', schedule_details[5])
        _cur_week = week[0]
        _cur_season_phase = phase[0]
        _cur_year = schedule_details[4]

    # return the time for calculating when to check 
    return time.time()

def current_season_phase():
    """
    Returns the current season phase
    """
    _update_week_number()
    return _cur_season_phase

def current_year_and_week():
    """
    Returns a tuple (year, week) where year is the current year of the season
    and week is the current week number of games being played.
    i.e., (2012, 3).

    """
    _update_week_number()
    return _cur_year, _cur_week

def calc_desired_weeks(year, phase):
    desired_weeks = []

    for week in range(5):
        desired_weeks.append(tuple([year, 'PRE', week]))
    for week in range(1,18):
        desired_weeks.append(tuple([year,'REG',week]))

    if phase is 'POST':
        for week in range(1,5):
            desired_weeks.append(tuple([year, 'POST', week]))

    return desired_weeks


def check_missing_weeks(sched, year, phase):

    missing_weeks = calc_desired_weeks(year, phase)
    stored_weeks = set()

    for info in sched.values():
        if info['year'] != year:
            continue
        stored_week = (year, info['season_type'], info['week'])
        stored_weeks.add(stored_week)

    for stored_week in stored_weeks:
        if stored_week in stored_weeks: stored_weeks.remove(stored_week)

    return missing_weeks


def order_weeks_to_update(missing_weeks, current_week):
    if current_week in missing_weeks:
        missing_weeks.remove(current_week)

    missing_weeks.insert(0, current_week)
    return missing_weeks


def _create_schedule(jsonf=None):
    """
    Returns an ordered dict of schedule data from the schedule.json
    file, where games are ordered by the date and time that they
    started. Keys in the dictionary are GSIS ids and values are
    dictionaries with the following keys: week, month, year, home,
    away, wday, gamekey, season_type, time.
    """
    day = 60 * 60 * 24
    if jsonf is None:
        jsonf = _sched_json_file
    try:
        data = json.loads(open(jsonf).read())
    except IOError:
        return OrderedDict(), datetime.datetime.utcnow()

    sched = OrderedDict()
    for gsis_id, info in data.get('games', []):
        sched[gsis_id] = info

    return sched

games = _create_schedule()

__pdoc__['nflgame.sched.games'] = """
An ordered dict of schedule data, where games are ordered by the date
and time that they started. Keys in the dictionary are GSIS ids and
values are dictionaries with the following keys: week, month, year,
home, away, wday, gamekey, season_type, time.
"""

__pdoc__['nflgame.sched.last_updated'] = """
A `datetime.datetime` object representing the last time the schedule
was updated.
"""
