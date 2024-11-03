odoo.define('equip3_kitchen_operations.kitchenDashboardView', function (require) {
"use strict";

var core = require('web.core');
var viewRegistry = require('web.view_registry');
var ListView = require('web.ListView');
var ListModel = require('web.ListModel');
var {ListController, ListRenderer} = require('ks_list_view_manager.renderer');
var SampleServer = require('web.SampleServer');

var QWeb = core.qweb;

let kitchenContext;
SampleServer.mockRegistry.add('product.product/retrieve_kitchen_dashboard', () => {
    return Object.assign({}, kitchenContext);
});


var kitchenRenderer = ListRenderer.extend({
    events:_.extend({}, ListRenderer.prototype.events, {
        'change .o_kitchen_dashboard_value': '_onKitchenValueChange'
    }),

    _renderView: function(){

        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var values = self.state.kitchenContext;
            var kitchen_dashboard_view = QWeb.render('equip3_kitchen_operations.kitchen_dashboard_header', {
                values: values
            });
            self.$el.prepend(kitchen_dashboard_view);
            if (!values['has_access']){
                var helpElement = self.$el.find('.o_nocontent_help');
                if (helpElement){
                    helpElement.children().last().replaceWith('<p>Sorry, You do not have permission to view this record.</p>');
                }
            }
        });
    },

    _onKitchenValueChange: function(e){
        e.preventDefault();
        var $action = $(e.currentTarget);
        this.trigger_up('kitchen_open_action', {
            fieldName: $action.attr('name'),
            fieldValue: e.currentTarget.value
        });
    }
});

var kitchenModel = ListModel.extend({
    /**
     * @override
     */
    init: function () {
        this.kitchenContext = {};
        this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    __get: function (localID) {
        var result = this._super.apply(this, arguments);
        if (_.isObject(result)) {
            result.kitchenContext = this.kitchenContext[localID];
        }
        return result;
    },
    /**
     * @override
     * @returns {Promise}
     */
    __load: function () {
        return this._loadKitchenViewDashboard(this._super.apply(this, arguments));
    },
    /**
     * @override
     * @returns {Promise}
     */
    __reload: function () {
        return this._loadKitchenViewDashboard(this._super.apply(this, arguments));
    },

    /**
     * @private
     * @param {Promise} super_def a promise that resolves with a dataPoint id
     * @returns {Promise -> string} resolves to the dataPoint id
     */
    _loadKitchenViewDashboard: async function (super_def) {
        var self = this;
        var dashboard_def = await this._rpc({
            model: 'product.product',
            method: 'retrieve_kitchen_dashboard',
            context: this.loadParams.context
        });

        return Promise.all([super_def, dashboard_def]).then(function(results) {
            var id = results[0];
            kitchenContext = results[1];
            self.kitchenContext[id] = kitchenContext;
            if (self.kitchenContext[id].context.change !== undefined) {
                setTimeout(function() {
                    $('select[name="warehouse"]').change();
                }, 500);
            }
            return id;
        });
    },
});

var kitchenController = ListController.extend({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        kitchen_open_action: '_onKitchenOpenAction',
    }),

    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.fieldDomain = 'produceable_in_kitchen';
    },

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onKitchenOpenAction: async function (e) {
        var self = this;
        let state = this.model.get(this.handle);
        let fieldName = e.data.fieldName;
        let fieldValue = e.data.fieldValue;

        if (fieldName === 'warehouse' && fieldValue !== false){
            fieldValue = parseInt(fieldValue);
        } else if (fieldValue === ''){
            fieldValue = false;
        }
        kitchenContext.context[fieldName] = fieldValue;

        if (kitchenContext.context.warehouse !== false){
            let context = state.getContext();
            for (let field of ['from_date', 'to_date', 'warehouse']){
                context[field] = kitchenContext.context[field]
            }

            let action = this.controlPanelProps.action;
            return this._rpc({
                model: 'product.product',
                method: 'assign_kitchen_bom',
                args: [[[this.fieldDomain, '=', true]]]
            }).then(function(productIds){
                return self.do_action({
                    name: action.name,
                    type: action.type,
                    res_model: action.res_model,
                    views: [action._views[0]],
                    search_view_id: action.search_view_id,
                    help: action.help,
                    target: 'main',
                    context: context,
                    domain: [['id', 'in', productIds]]
                });
            });
        }
    },

    // ks_list_view_manager issue
    update: function (params, options) {
        var self = this;
        var ks_lvm_mode = this.ks_lvm_mode;

        this.ks_lvm_mode = false;
        return this._super.apply(this,arguments).then(function(){
            self.ks_lvm_mode = ks_lvm_mode;
        });
    },

    reload: async function (params) {
        var self = this;
        var ks_lvm_mode = this.ks_lvm_mode;

        this.ks_lvm_mode = false;
        return this._super.apply(this,arguments).then(function(){
            self.ks_lvm_mode = ks_lvm_mode;
        });
    },
});

var kitchenListViewDashboard = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Model: kitchenModel,
        Renderer: kitchenRenderer,
        Controller: kitchenController,
    }),
});

viewRegistry.add('kitchen_dashboard_list_view', kitchenListViewDashboard);

return {
    kitchenModel: kitchenModel,
    kitchenRenderer: kitchenRenderer,
    kitchenController: kitchenController,
    kitchenListViewDashboard: kitchenListViewDashboard
};
});
