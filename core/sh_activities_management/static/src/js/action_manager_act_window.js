odoo.define("sh_create_multiple_activities.ActWindowActionManager", function (require) {
    "use strict";

    var ActionManager = require("web.ActionManager");
    var config = require("web.config");
    var Context = require("web.Context");

    ActionManager.include({
        _executeWindowAction: function (action, options) {
            var self = this;
            if (action.id) {
                action.context.action = action.id;
            }
            return this._super.apply(this, arguments);
        },
    });
});
