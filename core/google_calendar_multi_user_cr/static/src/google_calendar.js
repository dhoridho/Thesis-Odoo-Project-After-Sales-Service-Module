odoo.define('google_calendar_multi_user_cr.google_calendar', function(require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var google_renderer = require('google_calendar.CalendarView')
    const CalendarRenderer = require('calendar.CalendarRenderer');
    const CalendarModel = require('calendar.CalendarModel');

    CalendarModel.include({
        _syncGoogleCalendar(shadow = false) {
            var self = this;
            var context = this.getSession().user_context;
            return this._rpc({
                route: '/google_calendar/sync_data',
                params: {
                    model: this.modelName,
                    fromurl: window.location.href,
                    local_context: context, // LUL TODO remove this local_context
                }
            }, { shadow }).then(function(result) {
                if (result.status === "need_config_from_admin" || result.status === "need_auth") {
                    self.google_is_sync = false;
                } else if (result.status === "no_new_event_from_google" || result.status === "need_refresh") {
                    self._loadCalendar()
                    self.google_is_sync = true;
                }
                return result
            });
        },
    })
})