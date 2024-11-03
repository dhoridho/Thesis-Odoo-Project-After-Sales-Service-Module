odoo.define('pos_product_view_app.screens', function (require) {
"use strict";

	var models = require('point_of_sale.models');
	var core = require('web.core');
	var rpc = require('web.rpc');
	const { useState } = owl.hooks;
	const PosComponent = require('point_of_sale.PosComponent');
	const { useListener } = require('web.custom_hooks');
	const Registries = require('point_of_sale.Registries');
	const ProductsWidget = require('point_of_sale.ProductsWidget');
	const ProductsWidgetControlPanel = require('point_of_sale.ProductsWidgetControlPanel');
	var utils = require('web.utils');
	var field_utils = require('web.field_utils');
	var QWeb = core.qweb;
	var _t = core._t;

	var _super_posmodel = models.PosModel.prototype;      
	  models.PosModel = models.PosModel.extend({
		initialize: function (session, attributes) {
			var self = this;
		  
			this.is_list = false;
		  _super_posmodel.initialize.apply(this, arguments);
		},
	 });

	var _super_order = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function(attr, options) {
			_super_order.initialize.call(this,attr,options);
			this.is_list = this.is_list || "";
		},
		set_is_list: function(is_list){
			this.is_list = is_list;
			this.trigger('change',this);
		},
		get_is_list: function(is_list){
			return this.is_list;
		},        
		export_as_JSON: function(){
			var json = _super_order.export_as_JSON.call(this);
			json.is_list = this.is_list;
			return json;
		},
		init_from_JSON: function(json){
			_super_order.init_from_JSON.apply(this,arguments);
			this.is_list = json.is_list;
		},       
	});
	const PosViewProductsWidget = (ProductsWidget) =>
		class extends ProductsWidget {
			constructor() {
	            super(...arguments);
	            useListener('change-view', this.changeView);
	            $('.product-list-grid-container').hide();
	        }
	        changeView(event){
	        	if (event.detail == true){
	        		$('.product-list-container').hide();
	        		$('.product-list-grid-container').show();
	        		this.productsToDisplay;
	        	}
	        	else{
	        		$('.product-list-container').show();
	        		$('.product-list-grid-container').hide();
	        	}
	        }
			get productsToDisplay() {
	            if (this.searchWord !== '') {
	                return this.env.pos.db.search_product_in_category(
	                    this.selectedCategoryId,
	                    this.searchWord
	                );
	            } else {
	                return this.env.pos.db.get_product_by_category(this.selectedCategoryId);
	            }
	        }
		};
	Registries.Component.extend(ProductsWidget, PosViewProductsWidget);

	const PosViewProductsWidgetControlPanel = (ProductsWidgetControlPanel) =>
		class extends ProductsWidgetControlPanel {
			constructor() {
	            super(...arguments);
	            // useListener('change-view', this._tryAddProduct);
	        }
			listView(){
				this.env.pos.is_list = true;
	            this.env.pos.get_order().set_is_list(true);
				this.trigger('change-view', this.env.pos.is_list)
			}
			gridView(){
				this.env.pos.is_list = false;
	            this.env.pos.get_order().set_is_list(false);
	            this.trigger('change-view', this.env.pos.is_list)
			}
		};
	Registries.Component.extend(ProductsWidgetControlPanel, PosViewProductsWidgetControlPanel);


	class ProductGridWidget extends PosComponent {
		get imageUrl() {			
            const product = this.product;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }
    }
    ProductGridWidget.template = 'ProductGridWidget';

    Registries.Component.add(ProductGridWidget);


    class ProductListLine extends PosComponent {
    	get imageUrl() {
            const product = this.props.product;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }
    }
    ProductListLine.template = 'ProductListLine';

    Registries.Component.add(ProductListLine);

	return {
			ProductsWidget,
			ProductsWidgetControlPanel,
			ProductGridWidget,
			ProductListLine,
		};
});