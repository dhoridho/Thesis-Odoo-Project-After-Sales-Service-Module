odoo.define('equip3_ip_address_restriction.logout_check', function(require) {
    "use strict";

    var session = require('web.session');
    var WebClient = require('web.WebClient');

    WebClient.include({
        start: function () {
            this._super.apply(this, arguments);
            this.check_logout();
        },
        check_logout: function () {
            var self = this;
            console.log('Checking if should logout...');  // Log when the function is called
            session.rpc('/should_logout', {}).then(function (should_logout) {
                console.log('Should logout:', should_logout);  // Log the response from the server
                if (should_logout) {
                    console.log('Logging out...');  // Log when the user is being logged out
                    session.session_logout();
                } else {
                    setTimeout(self.check_logout.bind(self), 60000);  // Check every 1 minute
                }
            });
        },
    });
});