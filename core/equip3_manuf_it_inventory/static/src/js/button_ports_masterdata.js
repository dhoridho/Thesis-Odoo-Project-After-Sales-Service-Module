odoo.define('equip3_manuf_it_inventory.button_ports', function(require){
    'use strict';

    var ListControllers = require('web.ListController');
    var ListViews = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var ListControllerReports = ListControllers.extend({
        buttons_template: 'button_ports.buttons',
        events: _.extend({}, ListControllers.prototype.events, {
            'click .o_national_masterdata': '_onNationalMasterData',
            'click .o_overseas_masterdata': '_onOverseasMasterData',
        }),

        _onNationalMasterData: async function(e){
            e.preventDefault();
            var self = this;
            self._rpc({
                model: self.modelName,
                method: 'get_national_masterdata'
            }).then(function() {
                return self.do_action();
            });
        },

        _onOverseasMasterData: async function(e){
            e.preventDefault();
            var self = this;
            self._rpc({
                model: self.modelName,
                method: 'get_oversea_masterdata'
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

    viewRegistry.add('button_ports_masterdata', ListViewReports);
});