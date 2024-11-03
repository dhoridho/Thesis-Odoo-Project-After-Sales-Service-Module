odoo.define('app_odoo_boost.Longpolling', function (require) {
    "use strict";

    var session = require('web.session');
    var LongpollingBus = require('bus.Longpolling');

    // LongpollingBus.include({
    //     startPolling: function () {

    //         if (session.app_disable_poll) {
    //             this.stopPolling();
    //         } else {
    //             this._super.apply(this, arguments);
    //         }
    //     },
    // });
});



