odoo.define('equip3_ph_accounting_masterdata.custom_char_field_vat', function (require) {
    "use strict";

    var core = require('web.core');
    var FieldChar = require('web.basic_fields').FieldChar;
    var _t = core._t;

    FieldChar.include({
        init: function () {
            this._super.apply(this, arguments);
            if (this.name === 'vat' && this.model === 'res.partner') {
                this.attrs.placeholder = "e.g 123-456-789-111";
            }
        },
    });
});
