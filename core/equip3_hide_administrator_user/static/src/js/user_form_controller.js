odoo.define('equip3_hide_administrator_user.UserFormController', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    FormController.include({
        is_action_enabled: function (action) {
            var self = this;
            console.log('is_action_enabled called', action, self.modelName, self.renderer.state.data);
            if (action === 'edit' && self.modelName === 'res.users' && self.renderer.state.data.is_administrator) {
                return false;
            }
            return this._super(action);
        },

        saveRecord: function () {
            this.renderer.state.context.is_from_menu = true;
            return this._super.apply(this, arguments);
        },
    });

});