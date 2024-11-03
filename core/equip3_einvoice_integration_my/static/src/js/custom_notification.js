odoo.define('equip3_einvoice_integration_my.custom_notification', function(require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var Notification = require('web.Notification');
    var notificationService = require('web.NotificationService');

    var CustomNotificationAction = AbstractAction.extend({
        start: function() {
            this._displayNotification();
            return this._super.apply(this, arguments);
        },
        _displayNotification: function() {
            var params = this.action.params;
            var title = params.title || '';
            var message = params.message || '';
            var sticky = params.sticky || false;

            this.do_notify(title, message, sticky);
            if (!sticky) {
                setTimeout(function() {
                    // Reload the page or perform another action
                    self.do_action({type: 'ir.actions.client', tag: 'reload'});
                }, 2500); // Adjust the timeout duration as needed
            }
        },
    });

    core.action_registry.add('display_notification', CustomNotificationAction);

    return CustomNotificationAction;
});