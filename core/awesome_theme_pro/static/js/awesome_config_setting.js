odoo.define('awesome.config.settings', function (require) {
    "use strict";

    var core = require('web.core');
    var Renderer = require('base.settings').Renderer


    Renderer.include({

        events: _.extend({}, Renderer.prototype.events, {
            'click .awesome_pwa_setting': '_on_awesome_pwa_setting',
        }),

        /**
         * awesome pwa setting
         */
        _on_awesome_pwa_setting: function (event) {
            event.preventDefault();
            event.stopPropagation();

            var self = this;
            this._rpc({
                "model": "res.config.settings",
                "method": "awesome_pwa_setting",
                "args": []
            }).then(function (action) {
                self.do_action(action)
            })
        }
    });

    return Renderer;
});
