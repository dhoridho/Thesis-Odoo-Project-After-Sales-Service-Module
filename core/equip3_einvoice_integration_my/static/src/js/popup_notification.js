odoo.define('equip3_einvoice_integration_my.popup_notification', function(require) {
    "use strict";

    const FormController = require('web.FormController');
    const core = require('web.core');

    FormController.include({
        saveRecord: function() {
            // Display pre-save notification
            //this.do_notify("Notice", "Saving record...", "info");

            // Original save logic with pre-save notification
            console.log("saveRecord function called"); // Log when function is called
            return this._super(...arguments).then(result => {
                const isLhdnSubmit = this.model.get(this.handle, {raw: true}).data.is_lhdn_submit;
                console.log("isLhdnSubmit value:", isLhdnSubmit); // Log the value of isLhdnSubmit
                if (isLhdnSubmit) {
                    this.do_notify("E-Invoice", "E-Invoice has been submitted to MyInvois Portal", "success");
                }
                return result;
            });
        }
    });
});