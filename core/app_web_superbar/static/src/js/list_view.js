odoo.define('app_web_superbar.ListView', function (require) {
    "use strict";

    const ListView = require('web.ListView');
    const ListController = require('web.ListController');
    const ListRenderer = require('web.ListRenderer');
    const Superbar = require("app_web_superbar.Superbar");

    ListView.include({
        config: _.extend({}, ListView.prototype.config, {
            SearchPanel: Superbar,
        }),
    });
});

