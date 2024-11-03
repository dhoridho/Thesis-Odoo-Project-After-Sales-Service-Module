odoo.define('equip3_agri_operations.DatetimeTimepicker', function(require){
    "use strict";

    var { FieldDateTime } = require('web.basic_fields');
    var { DateTimeWidget } = require('web.datepicker');
    var registry = require('web.field_registry');
    var session = require('web.session');
    var field_utils = require('web.field_utils');

    var time = require('web.time');
    var core = require('web.core');
    var _lt = core._lt;

    function parseSmartDateInput(value) {
        const units = {
            d: 'days',
            m: 'months',
            w: 'weeks',
            y: 'years',
        };
        const re = new RegExp(`^([+-])(\\d+)([${Object.keys(units).join('')}]?)$`);
        const match = re.exec(value);
        if (match) {
            let date = moment();
            const offset = parseInt(match[2], 10);
            const unit = units[match[3] || 'd'];
            if (match[1] === '+') {
                date.add(offset, unit);
            } else {
                date.subtract(offset, unit);
            }
            return date;
        }
        return false;
    }

    function parseDateTimepicker(value, field, options){
        if (!value) {
            return false;
        }

        const datePattern = time.getLangDateFormat();
        const timePattern = time.getLangTimeFormat();

        if (typeof(value) === 'string'){
            value = moment.utc().format(datePattern) + ' ' + value;
        }

        const datePatternWoZero = time.getLangDateFormatWoZero();
        const timePatternWoZero = time.getLangTimeFormatWoZero();
        var pattern1 = datePattern + ' ' + timePattern;
        var pattern2 = datePatternWoZero + ' ' + timePatternWoZero;
        var datetime;
        const smartDate = parseSmartDateInput(value);
        if (smartDate) {
            datetime = smartDate;
        } else {
            if (options && options.isUTC) {
                value = value.padStart(19, "0"); // server may send "932-10-10" for "0932-10-10" on some OS
                // phatomjs crash if we don't use this format
                datetime = moment.utc(value.replace(' ', 'T') + 'Z');
            } else {
                datetime = moment.utc(value, [pattern1, pattern2, moment.ISO_8601]);
                if (options && options.timezone) {
                    datetime.add(-session.getTZOffset(datetime), 'minutes');
                }
            }
        }
        if (datetime.isValid()) {
            if (datetime.year() === 0) {
                datetime.year(moment.utc().year());
            }
            if (datetime.year() >= 1000) {
                datetime.toJSON = function () {
                    return this.clone().locale('en').format('YYYY-MM-DD HH:mm:ss');
                };
                return datetime;
            }
        }
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct datetime"), value));
    }

    function formatDateTimepicker(value, field, options){
        if (value === false) {
            return "";
        }
        if (!options || !('timezone' in options) || options.timezone) {
            value = value.clone().add(session.getTZOffset(value), 'minutes');
        }
        return value.format('HH:mm');
    }

    field_utils.parse.datetime_timepicker = parseDateTimepicker;
    field_utils.format.datetime_timepicker = formatDateTimepicker;

    var DateTimepickerWidget = DateTimeWidget.extend({
        type_of_date: "datetime_timepicker",

        init: function (parent, options) {
            this._super.apply(this, arguments);
            _.extend(this.options, {
                format: 'HH:mm'
            });
        },
    });

    var FieldDateTimePicker = FieldDateTime.extend({
        description: _lt("Timepicker"),
        supportedFieldTypes: ['datetime'],

        _makeDatePicker: function () {
            return new DateTimepickerWidget(this, this.datepickerOptions);
        }
    });

    registry.add('datetime_timepicker', FieldDateTimePicker);

    return {
        DateTimepickerWidget: DateTimepickerWidget,
        FieldDateTimePicker: FieldDateTimePicker
    };
});