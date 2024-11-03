odoo.define('awesome_theme_pro.AbstractAction', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction')
    var core = require('web.core')
    var BackendUserSetting = require('awesome_theme_pro.backend_setting')
    var ActionMixin = require('web.ActionMixin');

    var AwesomeAbstractAction = AbstractAction.include({

        init: function (parent, action, options) {
            this._super.apply(this, arguments);
            this.action = action
            this.isClientAction = false;
            if (action.tag && core.action_registry.contains(action.tag)) {
                // mark it is in client action
                this.isClientAction = true;
            }
        },

        start: async function () {
            // change adn store the control pannel template
            if (this.hasControlPanel) {
                var old_template = this.config.ControlPanel.template;
                this.config.ControlPanel.template = this.get_control_pannel_template()
            }
            await this._super(...arguments);
            // restore the control pannel template
            if (this.hasControlPanel) {
                this.config.ControlPanel.template = old_template;
            }
        },

        get_control_pannel_template: function() {
            return 'awesome_theme_pro.ControlPanel.' + BackendUserSetting.settings.control_panel_mode;
        },

        on_detach_callback: function () {
            ActionMixin.on_detach_callback.call(this);
            if (this.searchModel) {
                this.searchModel.off('search', this);
            }
            if (this.hasControlPanel) {
                this.searchModel.off('get-controller-query-params', this);
            }
        },
    })

    return AwesomeAbstractAction;
});
