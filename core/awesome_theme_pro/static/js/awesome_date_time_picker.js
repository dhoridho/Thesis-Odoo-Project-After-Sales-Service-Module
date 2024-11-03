odoo.define('awesome.datepicker', function (require) {
    "use strict";
    
    var DatePicker = require("web.datepicker").DateWidget

    DatePicker.include({

        _onDateTimePickerShow: function () {
            this._super.apply(this, arguments);
            this.$('.o_datepicker_button').addClass('awesome_reverse')
        },

        _onDateTimePickerHide: function () {
            this._super.apply(this, arguments);
            this.$('.o_datepicker_button').removeClass('awesome_reverse')
        },
    })
})