odoo.define('equip3_hse_operation.safe_hour', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var fields = require('web.basic_fields');
    var fieldUtils = require('web.field_utils');
    var field_registry = require('web.field_registry');
    var time = require('web.time');

    var _t = core._t;

    var SafeHourTimer = fields.FieldFloatTime.extend({

        init: function () {
            this._super.apply(this, arguments);
            this.duration = this.record.data.safe_hour;
        },

        willStart: function () {
            var self = this;
            var domain = []
            var def = this._rpc({
                model: 'hr.employee',
                method: 'search_read',
                domain: [
                    ['id', '=', this.record.data.id],

                ],
            }).then(function (result) {
                var currentDate = new Date();
                var duration = 0;
                if (result.length > 0) {
                    duration += self._getDateDifference(time.auto_str_to_date(result[0].date_start), currentDate);
                }
                var minutes = duration / 60 >> 0;
                var seconds = duration % 60;
                self.duration += minutes + seconds / 60;
                if (self.mode === 'edit') {
                    self.value = self.duration;
                }
            });
            return Promise.all([this._super.apply(this, arguments), def]);
        },

        destroy: function () {
            this._super.apply(this, arguments);
            clearTimeout(this.timer);
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        isSet: function () {
            return true;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Compute the difference between two dates.
         *
         * @private
         * @param {string} dateStart
         * @param {string} dateEnd
         * @returns {integer} the difference in millisecond
         */
        _getDateDifference: function (dateStart, dateEnd) {
            return moment(dateEnd).diff(moment(dateStart), 'seconds');
        },
        /**
         * @override
         */
        _renderReadonly: function () {

            if (this.record.data.attendance_state !== 'checked_out'){
                this._startTimeCounter();
            }else {
                this._super.apply(this, arguments);
            }

        },
        /**
         * @private
         */
        _startTimeCounter: function () {
            var self = this;
            // clearTimeout(this.timer);

            if (this.record.data.attendance_state !== 'checked_out'){
                this.timer = setTimeout(function () {
                    self.duration += 1/60;
                    self._startTimeCounter();
                }, 60000);
                this.$el.text(fieldUtils.format.float_time(this.duration));
            }
            else {
                this.$el.text(fieldUtils.format.float_time(0));
            }
            // this._setValue('safe_hour', this.duration)
        },
    });

    field_registry
        .add('safe_hour_timer', SafeHourTimer);

    fieldUtils.format.safe_hour_timer = fieldUtils.format.float_time;

    });