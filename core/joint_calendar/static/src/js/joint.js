odoo.define('joint_calendar.menu', function (require) {
"use strict";

    var Notification = require('web.Notification');
    var session = require('web.session');
    var WebClient = require('web.WebClient');

    var JointCalendarNotification = Notification.extend({
        /*                
        * The model for notification by joint events 
        */
        template: "CalendarNotification",
        xmlDependencies: (Notification.prototype.xmlDependencies || [])
            .concat(['/calendar/static/src/xml/notification_calendar.xml']),
        init: function(parent, params) {
            this._super(parent, params);
            this.eid = params.eventID;
            this.joint = params.jointID;
            this.events = _.extend(this.events || {}, {
                'click .link2event': function() {
                    var self = this;
                    this._rpc({
                        route: '/web/action/load',
                        params: {action_id: "joint_calendar.joint_event_action"}
                    }).then(function(r) {
                        r.res_id = self.eid;
                        return self.do_action(r);
                    });
                },
                'click .link2recall': function() {
                    this.destroy(true);
                },
                'click .link2showed': function() {
                    this._rpc({route: '/calendar/notify_ack'})
                        .then(this.destroy.bind(this), this.destroy.bind(this));
                },
            });
        },
    });

    WebClient.include({
        /*
        * Method to manage joint events popups
        */
        display_calendar_joint_notif: function(notifications) {
            var self = this;
            var last_notif_joint_timer  = 0;
            clearTimeout(this.get_next_calendar_joint_notif_timeout);
            _.each(this.calendar_notif_joint_timeouts, clearTimeout);
            _.each(this.calendar_joint_notif, function (notificationID) {
                self.call('notification', 'close', notificationID, true);
            });
            this.calendar_notif_joint_timeouts = {};
            this.calendar_joint_notif = {};
            _.each(notifications, function(notif) {
                self.calendar_notif_joint_timeouts[notif.event_id] = setTimeout(function() {
                    var notificationID = self.call('notification', 'notify', {
                        Notification: JointCalendarNotification,
                        title: notif.title,
                        message: notif.message,
                        eventID: notif.event_id,
                        jointID: notif.joint,
                        sticky: true,
                    });
                    self.calendar_joint_notif[notif.event_id] = notificationID;
                }, notif.timer * 1000);
                last_notif_joint_timer  = Math.max(last_notif_joint_timer , notif.timer);
            });
            if (last_notif_joint_timer  > 0) {
                this.get_next_calendar_joint_notif_timeout = setTimeout(
                    this.get_next_calendar_notif.bind(this), last_notif_joint_timer  * 1000
                );
            }
        },
        /*
        * Re-write to call joint event notifications in addition to standard events
        */
        get_next_calendar_notif: function() {
            this._super.apply(this, arguments);
            session.rpc("/calendar/jointnotify", {}, {shadow: true})
                .then(this.display_calendar_joint_notif.bind(this))
                .guardedCatch(function(reason) { //
                    var err = reason.message;
                    var ev = reason.event;
                    if(err.code === -32098) {
                        ev.preventDefault();
                    }
            });
        },
        /*
        * Re-write to manage joint events alarms send by bus
        */
        async show_application() {
            var self = this;
            this.calendar_notif_joint_timeouts = {};
            this.calendar_joint_notif = {};
            this.call('bus_service', 'onNotification', this, function (notifications) {
                _.each(notifications, (function (notification) {
                    if (notification[0][1] === 'joint.event') {
                        this.display_calendar_joint_notif(notification[1]);
                    }
                }).bind(this));
            });
            return this._super.apply(this, arguments);
        },
    });

});
