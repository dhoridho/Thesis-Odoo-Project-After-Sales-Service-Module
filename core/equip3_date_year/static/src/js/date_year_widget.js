odoo.define('equip3_date_year.date_year', function (require) {"use strict";

    var fields = require('web.basic_fields');
    var fieldUtils = require('web.field_utils');
    var field_registry = require('web.field_registry');
    var datepicker = require('web.datepicker');
    var session = require('web.session');

    var dateYearWidget = datepicker.DateWidget.extend({
        type_of_date: "date_year",
        init: function (parent, options) {
            this._super(parent, _.extend({
                format: 'YYYY'
            }, options || {}));
        }
    })

    var dateTimeYearWidget = datepicker.DateTimeWidget.extend({
        type_of_date: "datetime_year",
        init: function (parent, options) {
            this._super(parent, _.extend({
                format: 'YYYY',
                buttons: {
                    showToday: false,
                    showClear: false,
                    showClose: false,
                }
            }, options || {}));
        }
    })

    function parseDateYear(value, field, options) {
        if (!value) {
            return false;
        }
        var date = moment.utc(value, 'YYYY');
        if (date.isValid()) {
            if (date.year() === 0) {
                date.year(moment.utc().year());
            }
            if (date.year() >= 1000){
                date.toJSON = function () {
                    return this.clone().locale('en').format('YYYY-MM-DD');
                };
                return date;
            }
        }
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct date"), value));
    }

    function formatDateYear(value, field, options) {
        if (value === false || isNaN(value)) {
            return "";
        }
        return value.format('YYYY');
    }

    function parseDateTimeYear(value, field, options) {
        if (!value) {
            return false;
        }
        var datetime = moment.utc(value, 'YYYY');
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

    function formatDateTimeYear(value, field, options) {
        if (value === false) {
            return "";
        }
        if (!options || !('timezone' in options) || options.timezone) {
            value = value.clone().add(session.getTZOffset(value), 'minutes');
        }
        return value.format('YYYY');
    }
    
    var FieldDateYear = fields.FieldDate.extend({
        supportedFieldTypes: ['date'],
        init: function () {
            this._super.apply(this, arguments);
            this.formatType = 'date_year';
        },
        _makeDatePicker: function () {
            return new dateYearWidget(this, this.datepickerOptions);
        }
    });

    var FieldDateTimeYear = fields.FieldDateTime.extend({
        supportedFieldTypes: ['datetime'],
        init: function () {
            this._super.apply(this, arguments);
            this.formatType = 'datetime_year';
        },
        _makeDatePicker: function () {
            return new dateTimeYearWidget(this, this.datepickerOptions);
        }
    });

    field_registry.add('date_year', FieldDateYear);
    field_registry.add('datetime_year', FieldDateTimeYear);

    fields.FieldDateYear = FieldDateYear;
    fields.FieldDateTimeYear = FieldDateTimeYear;

    fieldUtils.format.date_year = formatDateYear;
    fieldUtils.parse.date_year = parseDateYear;
    
    fieldUtils.format.datetime_year = formatDateTimeYear;
    fieldUtils.parse.datetime_year = parseDateTimeYear;

    return {
        dateYearWidget: dateYearWidget,
        dateTimeYearWidget: dateTimeYearWidget,
        FieldDateYear: FieldDateYear,
        FieldDateTimeYear: FieldDateTimeYear,
        format: {
            date_year: formatDateYear,
            datetime_year: formatDateTimeYear
        },
        parse: {
            date_year: parseDateYear,
            datetime_year: parseDateTimeYear
        }
    }
});
