odoo.define('equip3_hr_attendance_extend.my_attendances', function(require) {
    "use strict";

    var MyAttendances = require("hr_attendance.my_attendances");
    var KioskConfirm = require("hr_attendance.kiosk_confirm");

    MyAttendances.include({
        update_attendance: function() {
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    self._manual_attendance.bind(self),
                    self._getPositionError.bind(self),
                    options
                );
            }
        },
        _manual_attendance: function (position) {
            var self = this;
            var context = {
                'webcam': self.webcam_snapshot,
            }
            var next_action = "hr_attendance.hr_attendance_action_my_attendances"
            if (self.hasOwnProperty('kiosk') && self.kiosk == true) {
                next_action = "hr_attendance.hr_attendance_action_kiosk_mode"
            }
            this._rpc({
                model: "hr.employee",
                method: "attendance_manual",
                args: [
                    [self.employee.id],
                    next_action,
                    null,
                    [position.coords.latitude, position.coords.longitude],
                ],
                kwargs: {
                    context:context,
                },
            }).then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                    if (self.hasOwnProperty('kiosk') && self.kiosk == true) {
                        setTimeout(function tick() {
                            var action = {
                                type: 'ir.actions.client',
                                tag: 'hr_attendance_kiosk_mode',
                                target: 'fullscreen',
                                context: {},
                            };
                            self.do_action(action);
                        }, 3000);
                    }
                } else if (result.warning) {
                    var tag = "hr_attendance_my_attendances"
                    if (self.hasOwnProperty('kiosk') && self.kiosk == true) {
                        var tag = "hr_attendance_kiosk_mode"
                    }
                    var action = {
                        type: 'ir.actions.client',
                        tag: tag,
                    };
                    self.do_action(action);
                    self.do_warn(result.warning);
                }
            });
        },
        _getPositionError: function (error) {
            console.warn("ERROR(" + error.code + "): " + error.message);
            const position = {
                coords: {
                    latitude: 0.0,
                    longitude: 0.0,
                },
            };
            this._manual_attendance(position);
        },
    });

    KioskConfirm.include({
        events: _.extend(KioskConfirm.prototype.events, {
            "click .o_hr_attendance_sign_in_out_icon": _.debounce(
                function () {
                    this.update_attendance();
                },
                200,
                true
            ),
            "click .o_hr_attendance_pin_pad_button_ok": _.debounce(
                function () {
                    this.pin_pad = true;
                    this.update_attendance();
                },
                200,
                true
            ),
        }),
        // eslint-disable-next-line no-unused-vars
        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.pin_pad = false;
        },
        update_attendance: function () {
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0,
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    self._manual_attendance.bind(self),
                    self._getPositionError.bind(self),
                    options
                );
            }
        },
        _manual_attendance: function (position) {
            var self = this;
            var pinBoxVal = null;
            if (this.pin_pad) {
                this.$(".o_hr_attendance_pin_pad_button_ok").attr(
                    "disabled",
                    "disabled"
                );
                pinBoxVal = this.$(".o_hr_attendance_PINbox").val();
            }
            this._rpc({
                model: "hr.employee",
                method: "attendance_manual",
                args: [
                    [this.employee_id],
                    this.next_action,
                    pinBoxVal,
                    [position.coords.latitude, position.coords.longitude],
                ],
            }).then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.do_warn(result.warning);
                    if (self.pin_pad) {
                        self.$(".o_hr_attendance_PINbox").val("");
                        setTimeout(function () {
                            self.$(".o_hr_attendance_pin_pad_button_ok").removeAttr(
                                "disabled"
                            );
                        }, 500);
                    }
                    self.pin_pad = false;
                }
            });
        },
        _getPositionError: function (error) {
            console.warn("ERROR(" + error.code + "): " + error.message);
            const position = {
                coords: {
                    latitude: 0.0,
                    longitude: 0.0,
                },
            };
            this._manual_attendance(position);
        },
    });
});