import pytz
import requests
import calendar
from datetime import timedelta
import datetime
import dateutil.parser
import dateutil.tz
import defusedxml.ElementTree as ET
import json

def request_json(url):
    r = requests.get(url)
    r.raise_for_status()
    return json.loads(r.content)

def get_volunteering(url = "https://emfcamp.org/volunteer/info-beamer.json"):

    def to_unixtimestamp(dt):
        dt = start.astimezone(pytz.utc)
        ts = int(calendar.timegm(dt.timetuple()))
        return ts
    data = request_json(url)
    parsed_events = []


    for event in data["urgent_shifts"]:

        start = dateutil.parser.parse(event["start"])

        end = dateutil.parser.parse(event["end"])
        duration = end - start

        parsed_events.append(dict(
            #start = start,
            start_str = start.strftime('%H:%M'),
            end_str = end.strftime('%H:%M'),
            start_unix  = to_unixtimestamp(start),
            end_unix = to_unixtimestamp(end),
            duration = int(duration.total_seconds() / 60),
            title = event['role'],
            track = "Urgent",
            place = event['venue'],
            abstract = "",
            lang = '', # Not in EMF struct
            id = str(event['id']),
            is_from_cfp = False,
            age_range = "People needed: " + str(event["max_needed"] - event["current"]),
            content_note = "",
            requires_ticket = False,
            group = "Primary"
        ))

    return parsed_events


def get_schedule(url, group, timezone = "UTC"):
    def load_events_emf_json(json_str):
        def to_unixtimestamp(dt):
            dt = start.astimezone(pytz.utc)
            ts = int(calendar.timegm(dt.timetuple()))
            return ts


        def all_events():
            return json.loads(json_str)

        parsed_events = []
        for event in all_events():
            # EMF schedule is in BST. The unix "now" calculations expect UTC
            BST = dateutil.tz.gettz('Europe/London')
            start = dateutil.parser.parse(event["start_date"] + " BST", tzinfos={'BST': BST})

            end = dateutil.parser.parse(event["end_date"] + " BST", tzinfos={'BST': BST})
            duration = end - start

            speaker = event['speaker'].strip() if event['speaker'] else None
            # Remove stuff like "Arcade with Arcade"
            if speaker and event['venue'].strip() == speaker:
                speaker = None
            if speaker and event["pronouns"]:
                speaker += " - " + event['pronouns']
            parsed_events.append(dict(
                start = start,
                start_str = start.strftime('%H:%M'),
                end_str = end.strftime('%H:%M'),
                start_unix  = to_unixtimestamp(start),
                end_unix = to_unixtimestamp(end),
                duration = int(duration.total_seconds() / 60),
                title = event['title'],
                track = event['type'],
                place = event['venue'],
                abstract = event['description'],
                speakers = [
                    speaker
                ] if speaker else [],
                lang = '', # Not in EMF struct
                id = str(event['id']),
                is_from_cfp = event['is_from_cfp'],
                age_range = event['age_range'] if ('age_range' in event and event['age_range']) else ("Family Friendly" if ('is_family_friendly' in event and event['is_family_friendly']) else ""),
                content_note = event['content_note'] if ('content_note' in event) else "",
                requires_ticket = event['requires_ticket'] if ('requires_ticket' in event) else False,
                group = group
            ))
        return parsed_events



    def load_events(xml):
        def to_unixtimestamp(dt):
            dt = dt.astimezone(pytz.utc)
            ts = int(calendar.timegm(dt.timetuple()))
            return ts
        def text_or_empty(node, child_name):
            child = node.find(child_name)
            if child is None:
                return u""
            if child.text is None:
                return u""
            return unicode(child.text)
        def parse_duration(value):
            h, m = map(int, value.split(':'))
            return timedelta(hours=h, minutes=m)

        def all_events():
            schedule = ET.fromstring(xml)
            for day in schedule.findall('day'):
                for room in day.findall('room'):
                    for event in room.findall('event'):
                        yield event

        parsed_events = []
        for event in all_events():
            start = dateutil.parser.parse(event.find('date').text)
            duration = parse_duration(event.find('duration').text)
            end = start + duration

            persons = event.find('persons')
            if persons is not None:
                persons = persons.findall('person')

            parsed_events.append(dict(
                start = start.astimezone(pytz.utc),
                start_str = start.strftime('%H:%M'),
                end_str = end.strftime('%H:%M'),
                start_unix  = to_unixtimestamp(start),
                end_unix = to_unixtimestamp(end),
                duration = int(duration.total_seconds() / 60),
                title = text_or_empty(event, 'title'),
                track = text_or_empty(event, 'track'),
                place = text_or_empty(event, 'room'),
                abstract = text_or_empty(event, 'abstract'),
                speakers = [
                    unicode(person.text.strip())
                    for person in persons
                ] if persons else [],
                lang = text_or_empty(event, 'language'),
                id = event.attrib["id"],
                is_from_cfp = False,
                group = group
            ))
        return parsed_events

    r = requests.get(url)
    r.raise_for_status()
    schedule = r.content
    if url.endswith('.json'):
        return load_events_emf_json(schedule)
    return load_events(schedule)
