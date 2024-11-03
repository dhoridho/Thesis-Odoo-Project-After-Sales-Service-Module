odoo.define('acs_jitsi_meet.systray', function (require) {
"use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var session = require('web.session');
var Dialog = require('web.Dialog');

var QWeb = core.qweb;

var VideoCallPopup = Widget.extend({
    template:'VideoCallPopup',
    events: {
        "click": "on_click_video_button",
    },
	on_click_video_button: function (event) {
		var self = this;
        event.preventDefault();
        self._rpc({
            route: '/web/action/load',
            params: {action_id: "acs_jitsi_meet.action_acs_video_call_popup"},
        }).then(function(action) {
            self.do_action(action);
        });
    },
});

SystrayMenu.Items.push(VideoCallPopup);

});
