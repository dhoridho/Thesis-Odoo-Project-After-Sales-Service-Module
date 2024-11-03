odoo.define('awesome_theme_pro.Dialog', function(require) {
    "use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var BackendUserSetting = require('awesome_theme_pro.backend_setting')

    Dialog.include({
        init: function(parent, options) {
            this._super.apply(this, arguments)
            this.title = BackendUserSetting.window_default_title || "Awesome Odoo";
        },
    })
});