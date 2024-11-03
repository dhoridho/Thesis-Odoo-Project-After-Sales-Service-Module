odoo.define('equip3_hr_attendance_general.greeting_message', function (require) {
    "use strict";
    
    var GreetingMessage = require('hr_attendance.greeting_message');
    var core = require('web.core');
    var time = require('web.time');
    var _t = core._t;

    GreetingMessage.include({
        init: function(parent, action) {
            var self = this;
            this._super.apply(this, arguments);

            // We receive the start/end break times in UTC
            // This widget only deals with display, which should be in browser's TimeZone
            this.attendance.start_break = this.attendance.start_break && moment.utc(this.attendance.start_break).local();
            this.attendance.end_break = this.attendance.end_break && moment.utc(this.attendance.end_break).local();

            // start/end break times displayed in the greeting message template.
            this.format_time = time.getLangTimeFormat();
            this.attendance.start_break_time = this.attendance.start_break && this.attendance.start_break.format(this.format_time);
            this.attendance.end_break_time = this.attendance.end_break && this.attendance.end_break.format(this.format_time);

            if (action.break_hours_today) {
                var duration = moment.duration(action.break_hours_today, "hours");
                this.break_hours_today = duration.hours() + ' hours, ' + duration.minutes() + ' minutes';
            }
        },
    });
    
    });
    