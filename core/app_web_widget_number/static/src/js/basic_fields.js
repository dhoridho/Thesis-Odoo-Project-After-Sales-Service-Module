odoo.define('app_web_widget_number.basic_fields', function (require) {
    "use strict";

    var session = require('web.session');
    var basic_fields = require('web.basic_fields');
    basic_fields.NumericField.include({
        isValid: function () {
            var isValid = this._super.apply(this, arguments);
            if (this.mode === 'edit' && !session.app_negative_allow && !this.nodeOptions.negative_allow && this.value < 0) {
                isValid = false;
            }
            return isValid;
        }
    });

});