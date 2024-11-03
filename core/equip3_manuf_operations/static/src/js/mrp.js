odoo.define('equip3_manuf_operations.mrp_state', function (require) {"use strict";

    var fields = require('web.basic_fields');
    var fieldUtils = require('web.field_utils');
    var field_registry = require('web.field_registry');
    var time = require('web.time');

    var TimeCounter = fields.FieldFloatTimeHMS.extend({

        init: function () {
            this._super.apply(this, arguments);
            this.duration = this.record.data.duration;
        },

        willStart: function () {
            var workorderIds;
            if (this.model === 'mrp.workorder'){
                workorderIds = [this.record.data.id];
            } else {
                workorderIds = this.record.data.workorder_ids.res_ids
            }
            var self = this;
            var def = this._rpc({
                model: 'mrp.workcenter.productivity',
                method: 'search_read',
                domain: [
                    ['workorder_id', 'in', workorderIds],
                    ['date_end', '=', false]
                ],
            }).then(function (result) {
                var currentDate = new Date();
                var duration = 0;
                for (let i=0; i < result.length; i++){
                    duration += self._getDateDifference(time.auto_str_to_date(result[i].date_start), currentDate);
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
            if (this.record.data.is_user_working) {
                this._startTimeCounter();
            } else {
                this._super.apply(this, arguments);
            }
        },
        /**
         * @private
         */
        _startTimeCounter: function () {
            var self = this;
            clearTimeout(this.timer);
            if (this.record.data.is_user_working) {
                this.timer = setTimeout(function () {
                    self.duration += 1/60;
                    self._startTimeCounter();
                }, 1000);
            } else {
                clearTimeout(this.timer);
            }
            this.$el.text(fieldUtils.format.float_time_hms(this.duration));
        }
    });

    field_registry.add('equip_time_counter', TimeCounter);
    fieldUtils.format.equip_time_counter = fieldUtils.format.float_time_hms;
});