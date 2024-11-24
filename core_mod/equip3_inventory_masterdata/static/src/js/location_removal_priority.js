odoo.define('equip3_inventory_masterdata.LocationRemovalPriority', function (require) {
    "use strict";
    
    var core = require('web.core');
    var viewRegistry = require('web.view_registry');
    var ListView = require('web.ListView');
    var ListModel = require('web.ListModel');
    var ListRenderer = require('web.ListRenderer');
    var ListController = require('web.ListController');
    
    var QWeb = core.qweb;
    
    let locationPriorityValues;
    let is_change_warehouse = false;
    
    
    var locationPriorityRenderer = ListRenderer.extend({
        events:_.extend({}, ListRenderer.prototype.events, {
            'change .o_removal_priority_warehouse_input': '_onWarehouseChange',
            'change .o_removal_priority_location_input': '_onLocationChange',
            'click .reset_removal_priority_btn': '_onResetRemovalPriority',
        }),
    
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            if (!state.context.hasSelectors){
                this.hasSelectors = false;
            }
        },
    
        _renderView: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var values = self.state.locationPriorityValues;
                var stock_per_wh = QWeb.render('equip3_inventory_masterdata.location_removal_priority_dashboard_header', {
                    values: values,
                });
                self.$el.prepend(stock_per_wh);
            });
        },
    
        _onWarehouseChange: function(e){
            e.preventDefault();
            var $action = $(e.currentTarget);
            this.trigger_up('on_change_warehouse', {
                field_name: $action.attr('name'),
                field_value: e.currentTarget.value
            });
        },
    
        _onLocationChange: function(e){
            e.preventDefault();
            var $action = $(e.currentTarget);
            this.trigger_up('on_change_location', {
                field_name: $action.attr('name'),
                field_value: e.currentTarget.value
            });
        },

        _onResetRemovalPriority: function(e){
            e.preventDefault();
            var self = this;
            this.trigger_up('on_reset_removal_priority', {
                location_ids: self.state.res_ids,
            });
        },
    });
    
    var locationPriorityModel = ListModel.extend({
        /**
         * @override
         */
        init: function () {
            this.locationPriorityValues = {};
            this._super.apply(this, arguments);
        },
    
        /**
         * @override
         */
        __get: function (localID) {
            var result = this._super.apply(this, arguments);
            if (_.isObject(result)) 
            {
                result.locationPriorityValues = this.locationPriorityValues[localID];
            }
            return result;
        },
        /**
         * @override
         * @returns {Promise}
         */
        __load: function () {
            return this._loadRemovalPriorityDashboard(this._super.apply(this, arguments));
        },
        /**
         * @override
         * @returns {Promise}
         */
        __reload: function () {
            return this._loadRemovalPriorityDashboard(this._super.apply(this, arguments));
        },
    
        /**
         * @private
         * @param {Promise} super_def a promise that resolves with a dataPoint id
         * @returns {Promise -> string} resolves to the dataPoint id
         */
        _loadRemovalPriorityDashboard: function (super_def) {
            var self = this;
            var context = this.loadParams.context;
            context["is_change_warehouse"] = is_change_warehouse;
            var dashboard_def = this._rpc({
                model: 'stock.location',
                method: 'get_warehouse_location_values',
                args: [this.locationPriorityValues],
                context: context,
            });
            return Promise.all([super_def, dashboard_def]).then(function(results) {
                var id = results[0];
                locationPriorityValues = results[1];
                self.locationPriorityValues[id] = locationPriorityValues;
                return id;
            });
        },
    });
    
    var locationPriorityController = ListController.extend({
        custom_events: _.extend({}, ListController.prototype.custom_events, {
            on_change_warehouse: '_onChangeWarehouse',
            on_change_location: '_onChangeLocation',
            on_reset_removal_priority: '_onResetRemovalPriority',
        }),
    
        /**
         * @private
         * @param {OdooEvent} e
         */
        _onChangeWarehouse: async function (e) {
            var state = this.model.get(this.handle);
            var locationPriorityValues = {};
            locationPriorityValues[this.handle] = state.locationPriorityValues;
    
            if (e.data.field_name === "removal_priority_dashboard_warehouse_id"){
                locationPriorityValues[this.handle].warehouse_id = e.data.field_value;
            }
    
            var context = state.getContext();
            is_change_warehouse = true
            context["is_change_warehouse"] = is_change_warehouse;
    
            var res_ids = await this._rpc({
                model: 'stock.location',
                method: 'get_warehouse_location_values',
                args: [locationPriorityValues],
                context: context,
            });
    
            state.locationPriorityValues = res_ids;        
            
            this.reload({
                context: context,
                domain: [["id", "in", []]]
            });
        },
    
        /**
         * @private
         * @param {OdooEvent} e
         */
        _onChangeLocation: async function (e) {
            var state = this.model.get(this.handle);
            var locationPriorityValues = {};
            locationPriorityValues[this.handle] = state.locationPriorityValues;
    
            if (e.data.field_name === "removal_priority_dashboard_location_id"){
                locationPriorityValues[this.handle].location_id = e.data.field_value;
            }
    
            is_change_warehouse = false
            var context = state.getContext();
    
            var res_ids = await this._rpc({
                model: 'stock.location',
                method: 'get_related_child_location',
                args: [{
                    'location_id': parseInt(e.data.field_value),
                }],
            });
    
            this.reload({
                context: context,
                domain: [["id", "in", res_ids]]
            });
        },

        _onResetRemovalPriority: async function(e){
            var state = this.model.get(this.handle);
            var context = state.getContext();
            var res_ids = await this._rpc({
                model: 'stock.location',
                method: 'reset_location_priority',
                args: [{
                    'location_ids': e.data.location_ids,
                }],
            });
    
            this.reload({
                context: context,
                domain: [["id", "in", res_ids]]
            });
        },
    });
    
    var locationRemovalPriority = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Model: locationPriorityModel,
            Renderer: locationPriorityRenderer,
            Controller: locationPriorityController,
        }),
    });
    
    viewRegistry.add('location_removal_priority', locationRemovalPriority);
    
    return {
        locationPriorityModel: locationPriorityModel,
        locationPriorityRenderer: locationPriorityRenderer,
        locationPriorityController: locationPriorityController,
    };
    
});
    