odoo.define('equip3_purchase_accessright_setting.form_unsaved_changes', function (require) {
    "use strict";

    var FormView = require('web.FormView');

    FormView.include({
        _renderView: function () {
            this._super.apply(this, arguments);
            // Menyembunyikan tombol Save dan Discard dari toolbar
            this.$el.find('.o_form_button_save, .o_form_button_discard').hide();
        }
    });
});
