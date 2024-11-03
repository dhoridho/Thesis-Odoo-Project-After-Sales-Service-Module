odoo.define('equip3_accounting_budget.confirmation_dialog', function (require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var FormController = require('web.FormController');

    FormController.include({
        _onSave: function (ev) {
            console.log("Form save initiated"); // Add this line
            var self = this;
            var def = this._super.apply(this, arguments);
            def.fail(function (error) {
                console.log("Save failed with error:", error); // Add this line
                if (error.message && error.message.includes("Are you sure you want to mark this budget as done?")) {
                    console.log("Confirmation message detected"); // Add this line
                    Dialog.confirm(self, error.message, {
                        confirm_callback: function () {
                            console.log("User confirmed the action"); // Add this line
                            // Call the action_budget_done method if confirmed
                            self._rpc({
                                model: 'monthly.purchase.budget',
                                method: 'action_budget_done',
                                args: [[self.initialState.data.id]],
                            }).then(function () {
                                console.log("Action budget done executed"); // Add this line
                                self.reload();
                            });
                        },
                    });
                }
            });
            return def;
        },
    });
});