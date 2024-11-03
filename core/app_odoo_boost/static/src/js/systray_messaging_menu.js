odoo.define('app_odoo_boost.MessagingMenu', function (require) {
    "use strict";

    //todo: MessagingMenu 改 owl
    var session = require('web.session');
    var ActivityMenu = require('mail.systray.ActivityMenu');

    ActivityMenu.include({
        init: function (params) {
            var self = this;
            self.app_enable_discuss = session.app_enable_discuss;
            self.app_disable_poll = session.app_disable_poll;
            this._super.apply(this, arguments);
        },

        start: function () {
            return this._super.apply(this, arguments);
        },
    });
});
