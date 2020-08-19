import cherrypy

from uber.config import c
from uber.decorators import ajax, all_renderable, log_pageview
from uber.errors import HTTPRedirect
from uber.models import Attendee, WatchList
from uber.utils import check


@all_renderable()
class Root:
    @log_pageview
    def index(self, session, message='', **params):
        watchlist_entries = session.query(WatchList).order_by(WatchList.last_name).all()
        for entry in watchlist_entries:
            if entry.active:
                entry.attendee_guesses = session.guess_watchentry_attendees(entry)

        return {
            'watchlist_entries': watchlist_entries,
            'message': message
        }

    def watchlist_form(self, session, message='', **params):
        if 'attendee_id' in params:
            attendee = session.attendee(params.get('attendee_id'), allow_invalid=True)
            entry = WatchList(first_names=attendee.first_name,
                              last_name=attendee.last_name,
                              email=attendee.email,
                              birthdate=attendee.birthdate)
        else:
            entry = session.watch_list(params, bools=['active'])
        entry.attendee_guesses = session.guess_watchentry_attendees(entry)

        if cherrypy.request.method == 'POST':
            message = check(entry)
            newly_banned_attendees = []

            if not message:
                session.add(entry)

                if entry.active:
                    for attendee in session.guess_watchentry_attendees(entry):
                        if attendee.badge_status == c.NEW_STATUS:
                            attendee.badge_status = c.WATCHED_STATUS
                            newly_banned_attendees.append(attendee.full_name)
                            session.add(attendee)

                if 'id' not in params:
                    message = 'New watchlist entry added.'
                else:
                    message = 'Watchlist entry updated.'
                raise HTTPRedirect('index?message={}', message)
                
        return {
            'entry': entry,
            'message': message
        }

    @ajax
    def update_watchlist_entry(self, session, attendee_id, watchlist_id=None, message='', **params):
        attendee = session.attendee(attendee_id, allow_invalid=True)
        if 'ignore' in params:
            attendee.badge_status = c.COMPLETED_STATUS
            message = 'Attendee can now check in'
        elif watchlist_id:
            watchlist_entry = session.watch_list(watchlist_id)

            if 'active' in params:
                watchlist_entry.active = not watchlist_entry.active
                message = 'Watchlist entry updated'
            if 'confirm' in params:
                attendee.watchlist_id = watchlist_id
                message = 'Watchlist entry permanently matched to attendee'

        session.commit()

        return {'success': True, 'message': message}
