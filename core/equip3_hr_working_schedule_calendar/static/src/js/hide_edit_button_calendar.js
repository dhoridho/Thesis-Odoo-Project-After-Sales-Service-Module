odoo.define('equip3_hr_working_schedule_calendar.hide_calendar_edit_button', function(require) {
    "use strict";

    var CalendarPopover = require('web.CalendarPopover');

    CalendarPopover.include({
        init: function (parent, eventInfo) {
            this._super.apply(this, arguments);
        },

        isEventEditable() {
            if (this.modelName == 'employee.working.schedule.calendar') {
                return false;
            }
            else {
                return true;
            }
        }
    })
});