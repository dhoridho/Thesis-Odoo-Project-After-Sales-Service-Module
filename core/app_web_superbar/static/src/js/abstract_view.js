odoo.define('app_web_superbar.AbstractView', function (require) {
    "use strict";

    var AbstractView = require('web.AbstractView');
    const Superbar = require("app_web_superbar.Superbar");

    AbstractView.include({
        config: _.extend({}, AbstractView.prototype.config, {
            SearchPanel: Superbar,
        }),
        init: function (viewInfo, params) {
            this.config.SearchPanel = Superbar;
            this._super.apply(this, arguments);
        }
    });
});
