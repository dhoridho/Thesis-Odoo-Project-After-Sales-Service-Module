odoo.define('equip3_inventory_reports.StockPerWarehouse', function (require) {
"use strict";

    var viewRegistry = require('web.view_registry');
    var ListView = require('web.ListView');
    var ListModel = require('web.ListModel');
    var ListController = require('web.ListController');
    var SampleServer = require('web.SampleServer');
    var { StockPerWhControlPanel } = require('equip3_inventory_reports.StockPerWarehouseWidget');

    let stockPerWhValues;
    SampleServer.mockRegistry.add('stock.quant/get_warehouse_based_product', () => {
        return Object.assign({}, stockPerWhValues);
    });

    var stockPerWhModel = ListModel.extend({
        /**
         * @override
         */
        init: function () {
            this.stockPerWhValues = {};
            this.tempValues = {};
            this._super.apply(this, arguments);
        },
        /**
         * @override
         */
        __get: function (localID) {
            var result = this._super.apply(this, arguments);
            if (_.isObject(result)) {
                result.stockPerWhValues = this.stockPerWhValues[localID];

            }
            return result;
        },
        /**
         * @override
         * @returns {Promise}
         */
        __load: function () {
            return this._loadStockperWhDashboard(this._super.apply(this, arguments));
        },
        /**
         * @override
         * @returns {Promise}
         */
        __reload: function () {
            return this._loadStockperWhDashboard(this._super.apply(this, arguments));
        },
        /**
         * @private
         * @param {Promise} super_def a promise that resolves with a dataPoint id
         * @returns {Promise -> string} resolves to the dataPoint id
         */
        _loadStockperWhDashboard: function (super_def) {
            var self = this;
            var dashboard_def = this._rpc({
                model: 'stock.quant',
                method: 'get_warehouse_values',
                args: [this.tempValues],
            });
            return Promise.all([super_def, dashboard_def]).then(function(results) {
                var id = results[0];
                stockPerWhValues = results[1];
                self.stockPerWhValues[id] = stockPerWhValues;
                return id;
            });
        },
    });


    var stockPerWhController = ListController.extend({

        custom_events: _.extend({}, ListController.prototype.custom_events, {
            apply_filters: '_onApplyFilters',
        }),

        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.filters = new StockPerWhControlPanel(this);
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$el.addClass('o_stock_per_wh_list');
                self.filters.appendTo(self.$el.find('.o_control_panel'));
            });
        },

        _colorMovement: function(){
            var self = this;
            let movement = {fast: [], slow: [], non: []};
            let state = this.model.get(this.handle);
            _.each(state.data, function(record){
                let $tr = self.$el.find('tr[data-id="' + record.id + '"]');
                if (record.data.inv_report_stock_movement === 'Fast Moving'){
                    movement.fast.push($tr);
                } else if (record.data.inv_report_stock_movement === 'Slow Moving'){
                    movement.slow.push($tr);
                } else {
                    movement.non.push($tr);
                }
            });

            _.each(Object.keys(movement), function(key){
                $(movement[[key]]).toggleClass('o_move_' + key)
            });
        },

        _onApplyFilters: async function(values){
            // Location IDS
            let locationIds = [];
            let locationElm = document.getElementsByClassName("o_location_tags");
            if(locationElm) {
                let locationData = $(locationElm[0]).select2('data');
                _.each(locationData, function(item){
                    locationIds.push(item.id);
                });
            }
            // Brand Names
            let brandNames = [];
            let brandElm = document.getElementsByClassName("o_brand_tags");
            if(brandElm) {
                let brandData = $(brandElm[0]).select2('data');
                _.each(brandData, function(item){
                    brandNames.push(item.text);
                });
            }
            // Product Category IDS
            let productCategoryIds = [];
            let productCategoryElm = document.getElementsByClassName("o_product_category_tags");
            if(productCategoryElm) {
                let productCategoryData = $(productCategoryElm[0]).select2('data');
                _.each(productCategoryData, function(item){
                    productCategoryIds.push(item.id);
                });
            }
            // Lot IDS
            let lotIds = [];
            let lotElm = document.getElementsByClassName("o_lot_tags");
            if(lotElm) {
                let lotData = $(lotElm[0]).select2('data');
                _.each(lotData, function(item){
                    lotIds.push(item.id);
                });
            }
            // Product Codes
            let productCodes = [];
            let productCodeElm = document.getElementsByClassName("o_product_code_tags");
            if(productCodeElm) {
                let productCodeData = $(productCodeElm[0]).select2('data');
                _.each(productCodeData, function(item){
                    productCodes.push(item.text);
                });
            }
            // Product Names
            let productNames = [];
            let productNameElm = document.getElementsByClassName("o_product_name_tags");
            if(productNameElm) {
                let productNameData = $(productNameElm[0]).select2('data');
                _.each(productNameData, function(item){
                    productNames.push(item.text);
                });
            }

            values = values === undefined ? {} : values;
            let warehouseId = values.warehouse !== undefined ? values.warehouse : this.filters.warehouse.value;
            let soldProduct = values.sold_product != undefined ? values.sold_product : this.filters.sold_product.value;
            let minusStock = values.minus_stock != undefined ? values.minus_stock : this.filters.minus_stock.value;
            let fsnColor = values.fsn_color != undefined ? values.fsn_color : this.filters.fsn_color.value;

            Object.assign(this.model.tempValues, {
                warehouse: warehouseId,
                location: locationIds,
                brand: brandNames,
                product_category: productCategoryIds,
                lot: lotIds,
                product_code: productCodes,
                product_name: productNames,
                sold_product: soldProduct,
                minus_stock: minusStock,
                fsn_color: fsnColor
            });
            
            var resIds = await this._rpc({
                model:'stock.quant',
                method: 'get_warehouse_based_product',
                kwargs: {
                    warehouse_id: warehouseId,
                    location_ids: locationIds,
                    brand_names: brandNames,
                    product_category_ids: productCategoryIds,
                    lot_ids: lotIds,
                    product_codes: productCodes,
                    product_names: productNames,
                    sold_product: soldProduct,
                    minus_stock: minusStock,
                    fsn_color: fsnColor
                }
            });

            let state = this.model.get(this.handle);
            let context = state.getContext();
            Object.assign(context, {
                inv_warehouse: warehouseId,
                inv_location: locationIds,
                inv_sold_product: soldProduct
            });

            this.update({
                context: context,
                domain: [['id', 'in', resIds]]
            });
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments);
            let $quickSearch = this.$el.find('.o_search_panel_toggler');
            if ($quickSearch.length){
                $quickSearch.addClass('d-none');
            }
        },

        async _update(state, params) {
            await this._super.apply(this, arguments);
            if (this.filters){
                this.filters._applyModifiers();
                this.filters._clean();
                this.filters._checkButtons();
                if (this.filters.fsn_color.value){
                    this._colorMovement();
                }
            }
        }
    });

    var stockPerWhListViewDashboard = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Model: stockPerWhModel,
            Controller: stockPerWhController,
        }),
    });

    viewRegistry.add('stock_per_wh', stockPerWhListViewDashboard);

    return {
        stockPerWhModel: stockPerWhModel,
        stockPerWhController: stockPerWhController,
    };

});
