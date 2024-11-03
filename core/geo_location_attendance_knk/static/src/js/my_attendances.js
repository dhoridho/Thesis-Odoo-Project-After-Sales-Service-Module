odoo.define('geo_location_attendance_knk.my_attendances', function(require) {
    "use strict";

    var MyAttendances = require('hr_attendance.my_attendances');

    MyAttendances.include({
        update_attendance: function() {
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            };

            function success(pos) {
                var crd = pos.coords;
                debugger;
                self._rpc({
                    model: 'hr.employee',
                    method: 'attendance_location',
                    args: [
                        [self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances', crd.latitude, crd.longitude
                    ],
                })
                .then(function(result) {
                    if (result.action) {
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.do_warn(result.warning);
                    }
                });
            }

            function error(err) {
                console.warn(`ERROR(${err.code}): ${err.message}`);
            }
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(success, error, options);
            }
        },
    });
});