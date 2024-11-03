odoo.define('equip3_date_year.month_year', function (require) {"use strict";

    var fields = require('web.basic_fields');
    var fieldUtils = require('web.field_utils');
    var field_registry = require('web.field_registry');
    var datepicker = require('web.datepicker');
    var session = require('web.session');

    var dateMonthYearWidget = datepicker.DateWidget.extend({
        type_of_date: "date_month_year",
        init: function (parent, options) {
            this._super(parent, _.extend({
                format: 'MMMM YYYY'
            }, options || {}));
        }
    })

    var dateTimeMonthYearWidget = datepicker.DateTimeWidget.extend({
        type_of_date: "datetime_month_year",
        init: function (parent, options) {
            this._super(parent, _.extend({
                format: 'MMMM YYYY',
                buttons: {
                    showToday: false,
                    showClear: false,
                    showClose: false,
                }
            }, options || {}));
        }
    })

    function parseDateMonthYear(value, field, options) {
        if (!value) {
            return false;
        }
        var date = moment.utc(value, 'MMMM YYYY');
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

    function formatDateMonthYear(value, field, options) {
        if (value === false || isNaN(value)) {
            return "";
        }
        return value.format('MMMM YYYY');
    }

    function parseDateTimeMonthYear(value, field, options) {
        if (!value) {
            return false;
        }
        var datetime = moment.utc(value, 'MMMM YYYY');
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

    function formatDateTimeMonthYear(value, field, options) {
        if (value === false) {
            return "";
        }
        if (!options || !('timezone' in options) || options.timezone) {
            value = value.clone().add(session.getTZOffset(value), 'minutes');
        }
        return value.format('MMMM YYYY');
    }
    
    var FieldDateMonthYear = fields.FieldDate.extend({
        supportedFieldTypes: ['date'],
        init: function () {
            this._super.apply(this, arguments);
            this.formatType = 'date_month_year';
        },
        _makeDatePicker: function () {
            return new dateMonthYearWidget(this, this.datepickerOptions);
        }
    });

    var FieldDateTimeMonthYear = fields.FieldDateTime.extend({
        supportedFieldTypes: ['datetime'],
        init: function () {
            this._super.apply(this, arguments);
            this.formatType = 'datetime_month_year';
        },
        _makeDatePicker: function () {
            return new dateTimeMonthYearWidget(this, this.datepickerOptions);
        }
    });

    field_registry.add('date_month_year', FieldDateMonthYear);
    field_registry.add('datetime_month_year', FieldDateTimeMonthYear);

    fields.FieldDateMonthYear = FieldDateMonthYear;
    fields.FieldDateTimeMonthYear = FieldDateTimeMonthYear;

    fieldUtils.format.date_month_year = formatDateMonthYear;
    fieldUtils.parse.date_month_year = parseDateMonthYear;
    
    fieldUtils.format.datetime_month_year = formatDateTimeMonthYear;
    fieldUtils.parse.datetime_month_year = parseDateTimeMonthYear;

    return {
        dateMonthYearWidget: dateMonthYearWidget,
        dateTimeMonthYearWidget: dateTimeMonthYearWidget,
        FieldDateMonthYear: FieldDateMonthYear,
        FieldDateTimeMonthYear: FieldDateTimeMonthYear,
        format: {
            date_month_year: formatDateMonthYear,
            datetime_month_year: formatDateTimeMonthYear
        },
        parse: {
            date_month_year: parseDateMonthYear,
            datetime_month_year: parseDateTimeMonthYear
        }
    }
});
