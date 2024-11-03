odoo.define('equip3_asset_fms_operation.Timer', function (require) {
    "use strict";
    
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fields = require('web.basic_fields');
var fieldUtils = require('web.field_utils');
var field_registry = require('web.field_registry');
var time = require('web.time');

var _t = core._t;

var TimeProgress = fields.FieldFloatTime.extend({

    init: function () {
        this._super.apply(this, arguments);
        this.time_in_progress = this.record.data.time_in_progress;
    },

    willStart: function () {
        var self = this;
        var domain = []
        if (this.model === "maintenance.work.order") {
            domain = [
                ['maintenance_wo_id', '=', this.record.data.id],
                ['date_end', '=', false],
            ]
        }
        else if (this.model === "maintenance.repair.order") {
            domain = [
                ['repair_id', '=', this.record.data.id],
                ['date_end', '=', false],
            ]
        }
        var def = this._rpc({
            model: 'time.progress',
            method: 'search_read',
            domain: domain,
        }).then(function (result) {
            var currentDate = new Date();
            var duration = 0;
            if (result.length > 0) {
                duration += self._getDateDifference(time.auto_str_to_date(result[0].date_start), currentDate);
            }
            var minutes = duration / 60 >> 0;
            var seconds = duration % 60;
            self.time_in_progress += minutes + seconds / 60;
            if (self.mode === 'edit') {
                self.value = self.time_in_progress;
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
        if (this.record.data.state_id === "in_progress" || this.record.data.state_id === "to_approve_post"){
            this._startTimeCounter();
        }
        else if (this.record.data.in_progress_to_post === true && this.record.data.state_id === "to_approve_post") {
            this._startTimeCounter();
        }
        else if (this.record.data.in_progress_to_post === false && this.record.data.state_id === "to_approve_done") {
            this._startTimeCounter();
        }
        else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @private
     */
    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        if (this.record.data.state_id === "in_progress" || this.record.data.state_id === "to_approve_post") {
            this.timer = setTimeout(function () {
                self.time_in_progress += 1/60;
                self._startTimeCounter();
            }, 1000);
        }
        else if (this.record.data.in_progress_to_post === true && this.record.data.state_id === "to_approve_post") {
            this.timer = setTimeout(function () {
                self.time_in_progress += 1/60;
                self._startTimeCounter();
            }, 1000);
        }
        else if (this.record.data.in_progress_to_post === false && this.record.data.state_id === "to_approve_done") {
            this.timer = setTimeout(function () {
                self.time_in_progress += 1/60;
                self._startTimeCounter();
            }, 1000);

        } 
        else {
            clearTimeout(this.timer);
        }
        this.$el.text(fieldUtils.format.float_time(this.time_in_progress));
    },
});

var TimePost = fields.FieldFloatTime.extend({

    init: function () {
        this._super.apply(this, arguments);
        this.time_post = this.record.data.time_post;
    },

    willStart: function () {
        var self = this;
        var domain = []
        if (this.model === "maintenance.work.order") {
            domain = [
                ['maintenance_wo_id', '=', this.record.data.id],
                ['date_end', '=', false],
            ]
        }
        else if (this.model === "maintenance.repair.order") {
            domain = [
                ['repair_id', '=', this.record.data.id],
                ['date_end', '=', false],
            ]
        }
        var def = this._rpc({
            model: 'time.post',
            method: 'search_read',
            domain: domain,
        }).then(function (result) {
            var currentDate = new Date();
            var duration = 0;
            if (result.length > 0) {
                duration += self._getDateDifference(time.auto_str_to_date(result[0].date_start), currentDate);
            }
            var minutes = duration / 60 >> 0;
            var seconds = duration % 60;
            self.time_post += minutes + seconds / 60;
            if (self.mode === 'edit') {
                self.value = self.time_post;
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
        if (this.record.data.state_id === "pending") {
            this._startTimeCounter();
        }
        else if (this.record.data.in_progress_to_post === true && this.record.data.state_id === "to_approve_done") {
            this._startTimeCounter();
        } 
        else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @private
     */
    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        if (this.record.data.state_id === "pending") {
            this.timer = setTimeout(function () {
                self.time_post += 1/60;
                self._startTimeCounter();
            }, 1000);
        }
        else if (this.record.data.in_progress_to_post === true && this.record.data.state_id === "to_approve_done") {
            this.timer = setTimeout(function () {
                self.time_post += 1/60;
                self._startTimeCounter();
            }, 1000);
        } 
        else {
            clearTimeout(this.timer);
        }
        this.$el.text(fieldUtils.format.float_time(this.time_post));
    },
});

field_registry
    .add('time_in_progress', TimeProgress)
    .add('time_post', TimePost)

fieldUtils.format.time_in_progress = fieldUtils.format.float_time;
fieldUtils.format.time_post = fieldUtils.format.float_time;

});