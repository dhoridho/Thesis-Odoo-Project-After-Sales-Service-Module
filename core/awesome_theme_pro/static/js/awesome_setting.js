odoo.define('awesome.settings', function (require) {
    "use strict";

    var settings = require('base.settings')
    var BaseSettingRenderer = settings.Renderer

    var BaseSettingRenderer = BaseSettingRenderer.include({

        events: _.extend({}, BaseSettingRenderer.prototype.events, {
            "click .awesome_setting_toggler": "_on_toggler_click"
        }),

        _on_toggler_click: function (event) {
            if (this.$('.settings_tab').hasClass('show')) {
                this.$('.settings_tab').removeClass('show')
                this.$('.awesome_setting_toggler .left_arrow').addClass('d-none')
                this.$('.awesome_setting_toggler .right_arrow').removeClass('d-none')
            } else {
                this.$('.settings_tab').addClass('show')
                this.$('.awesome_setting_toggler .left_arrow').removeClass('d-none')
                this.$('.awesome_setting_toggler .right_arrow').addClass('d-none')
            }
        }
    });
});
