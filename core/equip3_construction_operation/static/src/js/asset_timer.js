odoo.define('equip3_construction_operation.Timer', function (require) {
    "use strict";
    
    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var fields = require('web.basic_fields');
    var fieldUtils = require('web.field_utils');
    var field_registry = require('web.field_registry');
    var time = require('web.time');
    
    var _t = core._t;
    
    var AssetTimeProgress = fields.FieldFloatTimeHMS.extend({
    
        init: function () {
            this._super.apply(this, arguments);
            this.duration = this.record.data.duration;
        },
    
        willStart: function () {
            var self = this;
            var domain = []
            if (this.model === "allocation.asset") {
                domain = [
                    ['allocation_id', '=', this.record.data.id],
                    ['date_end', '=', false],
                ]
            }
            else if (this.model === "allocation.asset.line") {
                domain = [
                    ['allocation_asset_id', '=', this.record.data.id],
                    ['date_end', '=', false],
                ]
            }
            var def = this._rpc({
                model: 'asset.time.progress',
                method: 'search_read',
                domain: domain,
                // domain: [
                //     ['allocation_asset_id', '=', this.record.data.id],
                //     ['date_end', '=', false],
                // ],
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
            if (this.record.data.state === "in_progress") {
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
            if (this.record.data.state === "in_progress") {
                if (this.record.data.asset_allocation_option === "live_count") {
                    this.timer = setTimeout(function () {
                        self.duration += 1/60;
                        self._startTimeCounter();
                    }, 1000);
                } else{
                    clearTimeout(this.timer);
                }

            } else {
                clearTimeout(this.timer);
            }
            this.$el.text(fieldUtils.format.float_time_hms(this.duration));
        },
    });
    
    field_registry
        .add('asset_duration', AssetTimeProgress);
    
    fieldUtils.format.asset_duration = fieldUtils.format.float_time_hms;
    
    });