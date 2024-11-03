odoo.define('equip3_inventory_control.tree_view_button', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var StockCountList = ListController.extend({
        buttons_template: 'equip3_inventory_control.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .open_import_action': '_OpenImport',
        }),

        _OpenImport: function () {
            const action = {
                type: 'ir.actions.client',
                tag: 'import',
                params: {
                    model: 'stock.inventory',
                }
            };
            this.do_action(action);
        }
    });

    var StockCountListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: StockCountList,
        }),
    });

    viewRegistry.add('button_in_tree', StockCountListView);
});
