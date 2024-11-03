
odoo.define('awesome_theme_pro.theme_config', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var awesome_theme_configer = require('awesome_theme_pro.theme_configer')

    /**
     * awsome theme config
     */
    var AwsomeThemeModeConfig = AbstractAction.extend({
        init: function (parent, action) {
            this._super.apply(this, arguments)
        },

        start: function () {
            var self = this;
            this._super.apply(this, arguments).then(function () {
                self.theme_configer = new awesome_theme_configer(self)
                self.theme_configer.appendTo(this.$el);
            })
        },

        willStart: function () {
            return this._super.apply(this, arguments);
        }
    });

    core.action_registry.add('AwsomeThemeModeConfig', AwsomeThemeModeConfig);
    return AwsomeThemeModeConfig;
});