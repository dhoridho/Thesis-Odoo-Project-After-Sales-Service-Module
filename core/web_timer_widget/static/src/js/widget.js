odoo.define('web_timer_widget.web_timer', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var field_registry = require('web.field_registry');
var time = require('web.time');
var utils = require('web.utils');

var core = require('web.core');
var _t = core._t;
 
var TimeCounter = AbstractField.extend({
    supportedFieldTypes: [],

    willStart: function () {
        var self = this;
        var def = this._rpc({
            model: this.model,
            method: 'search_read',
            domain: [
                ['id', '=', this.record.data.id],
            ],
        }).then(function (result) {
            if (self.mode === 'readonly') {
                var currentDate = new Date();
                var start_date = self.attrs['options'].widget_start_field;
                var stop_date = self.attrs['options'].widget_stop_field;
                self.duration = 0;
                _.each(result, function (data) {
                    self.duration += data[stop_date] ?
                        self._getDateDifference(data[start_date], data[stop_date]) :
                        self._getDateDifference(time.auto_str_to_date(data[start_date]), currentDate);
                        self._startTimeCounter();
                });
            }
        });
        return $.when(this._super.apply(this, arguments), def);
    },

    destroy: function () {
        this._super.apply(this, arguments);
        clearTimeout(this.timer);
    },

    _render: function () {
        this._startTimeCounter();
    },

    _getDateDifference: function (dateStart, dateEnd) {
        return moment(dateEnd).diff(moment(dateStart));
    },

    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        this.timer = setTimeout(function () {
            self.duration += 1000;
            self._startTimeCounter();
        }, 1000);
        if (this.$el){
            if (this.recordData[self.attrs['options'].widget_start_field] && !this.recordData[self.attrs['options'].widget_stop_field]) {
                this.$el.html($('<span>' + moment.utc(this.duration).format("HH:mm:ss") + '</span>'));
            } else {
                this.$el.html($('<span> </span>'));
            }
        }
    },
});


field_registry
    .add('web_time_counter', TimeCounter);
});