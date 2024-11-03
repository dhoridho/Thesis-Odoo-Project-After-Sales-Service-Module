odoo.define('equip3_pos_report.ProductReceiptWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { useState, useRef, useContext } = owl.hooks;
    const { debounce } = owl.utils;
    const { loadCSS } = require('web.ajax');
    const utils = require('web.utils');
    const { Gui } = require('point_of_sale.Gui');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Popup = require('point_of_sale.ConfirmPopup');
    var core = require('web.core');
    var QWeb = core.qweb;

    const ProductReceiptWidget = (ReceiptScreen) => {
        class ProductReceiptWidget extends ReceiptScreen {
       		constructor() {
            	super(...arguments);
        	}

        	back(){
				this.trigger('close-temp-screen');
				this.showScreen('ProductScreen');
			}

			get_pro_summery(){
				return this['props']['output_summery_product'];
			}
		
			get_product_st_date(){
				return this['props']['pro_st_date'];
			}
			get_product_ed_date(){
				return this['props']['pro_ed_date'];
			}

			get product_receipt_data() {
				return {
					widget: this,
					pos: this.pos,
					prod_current_session : this['props']['prod_current_session'],
					p_summery: this.get_pro_summery(),
					p_st_date: this.get_product_st_date(),
					p_ed_date: this.get_product_ed_date(),
					date_p: (new Date()).toLocaleString(),
				};
			}
		}
		ProductReceiptWidget.template = 'ProductReceiptWidget';
		return ProductReceiptWidget

    };
    

    Registries.Component.addByExtending(ProductReceiptWidget,ReceiptScreen);

    return ProductReceiptWidget;
});