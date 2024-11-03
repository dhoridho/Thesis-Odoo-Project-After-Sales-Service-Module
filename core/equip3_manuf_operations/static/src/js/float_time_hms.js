odoo.define('equip3_manuf_operations.float_time_hms', function (require) {"use strict";

    var fields = require('web.basic_fields');
    var fieldUtils = require('web.field_utils');
    var field_registry = require('web.field_registry');

    function parseFloatTimeHMS(value) {
        var factor = 1;
        if (value[0] === '-') {
            value = value.slice(1);
            factor = -1;
        }
        var float_time_pair = value.split(":");
        if (float_time_pair.length !== 3)
            return factor * parseFloat(value);
        var hours = parseInt(float_time_pair[0]);
        var minutes = parseInt(float_time_pair[1]);
        var seconds = parseInt(float_time_pair[2]);
        return factor * ((hours * 60) + minutes + (seconds / 60));
    }

    function formatFloatTimeHMS(value) {
        var totalSeconds = value * 60;
        var hour = Math.floor(totalSeconds / 3600);
        var minutes = Math.floor((totalSeconds - (hour * 3600)) / 60);
        var seconds = Math.round(totalSeconds - (hour * 3600) - (minutes * 60));
        if (seconds === 60){
            seconds = 0;
            minutes += 1;
        }
        if (minutes === 60){
            minutes = 0;
            hour += 1;
        }
        return _.str.sprintf('%02d:%02d:%02d', hour, minutes, seconds);
    }
    
    var FieldFloatTimeHMS = fields.FieldFloat.extend({
        init: function () {
            this._super.apply(this, arguments);
            this.formatType = 'float_time_hms';
        }
    });

    field_registry.add('float_time_hms', FieldFloatTimeHMS);
    fields.FieldFloatTimeHMS = FieldFloatTimeHMS;
    fieldUtils.format.float_time_hms = formatFloatTimeHMS;
    fieldUtils.parse.float_time_hms = parseFloatTimeHMS;
});