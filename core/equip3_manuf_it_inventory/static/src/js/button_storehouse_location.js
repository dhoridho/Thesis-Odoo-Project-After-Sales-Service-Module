odoo.define('equip3_manuf_it_inventory.button_storehouse_location', function(require){
    'use strict';

    var ListControllers = require('web.ListController');
    var ListViews = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var ListControllerReports = ListControllers.extend({
        buttons_template: 'button_storehouse_location.buttons',
        events: _.extend({}, ListControllers.prototype.events, {
            'click .o_tps_masterdata': '_onTPSMasterData',
        }),

        _onTPSMasterData: async function(e){
            e.preventDefault();
            var self = this;
            self._rpc({
                model: self.modelName,
                method: 'get_storehouse_masterdata',
            }).then(function() {
                return self.do_action();
            });
        }
    });

    var ListViewReports = ListViews.extend({
        config: _.extend({}, ListViews.prototype.config, {
            Controller: ListControllerReports
        }),
    });

    viewRegistry.add('button_storehouse_location_masterdata', ListViewReports);
});