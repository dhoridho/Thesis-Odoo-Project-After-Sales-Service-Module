odoo.define('apps_installation_activity_log.apps_activity', function (require) {
"use strict";

    var Dialog = require('web.Dialog');
    var Model = require('web.Model');

    Dialog.include({
        destroy: function(reason) {
            var self = this;
            if (this.$modal.find('.apps_activity_uninstall').length > 0 &&
                this.debug_manager && this.debug_manager._action && 
                this.debug_manager._action.context && this.debug_manager._action.context.active_id) {
                new Model("base.module.upgrade")
                    .call("upgrade_module_cancel", [this.debug_manager._action.context.active_id])
                    .then(function (result) {
                        return false;
                    });
                return this._super.apply(this, arguments);
            }
            else {
                return this._super.apply(this, arguments);
            }
        },
    })
});