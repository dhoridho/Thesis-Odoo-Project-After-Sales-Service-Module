odoo.define('equip3_pos_general_fnb.pos_order', function (require) {
    'use strict';
    
    const Registries = require('point_of_sale.Registries');
    const PosOrder = require('equip3_pos_general.pos_order');
    const ProductScreen = PosOrder.ProductScreen;
    var models = require('point_of_sale.models');

    models.load_fields('pos.receipt.template', ['is_receipt_bom_info','is_receipt_combo_info','is_display_barcode_ean13','is_qrcode_link','is_table_guest_info']);
    
    models.load_fields('sale.order', ['reserve_order','reserve_from','reserve_to','reserve_table_id','reserve_no_of_guests','reserve_mobile']);

    const GenFnbProductScreenExt = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            } 

            async _onClickPayBtn() { 
                let selectedOrder = this.env.pos.get_order();
                let lines = selectedOrder.get_orderlines();
                let combo_and_bom_line = lines.filter( (l) => l.is_from_cross_sale && (l.product.pos_bom_id || l.product.is_combo_product_new) );
                if(combo_and_bom_line.length){
                    let confirmed = [];
                    for (var i = lines.length - 1; i >= 0; i--) {
                        let need_confirm = false;
                        if(lines[i].product.pos_bom_id){
                            if(!lines[i].bom_components){
                                need_confirm = true;
                            }
                        }else if(lines[i].product.is_combo_product_new){
                            if(!lines[i].pos_combo_options){
                                need_confirm = true;
                            }
                        }
                        if(need_confirm){
                            await lines[i].confirm_combo_and_bom_product();
                        }
                    }
                    console.log('ClickPayBtn:confirm_combo_and_bom_product')

                    let confirmed_combo_and_bom_line = lines.filter( (l)=>l.is_from_cross_sale && (l.bom_components || l.pos_combo_options) );
                    if(combo_and_bom_line.length == confirmed_combo_and_bom_line.length){
                        super._onClickPayBtn();
                    }
                }else{
                    super._onClickPayBtn();
                }
            }
    }

    Registries.Component.extend(ProductScreen, GenFnbProductScreenExt);
    return ProductScreen;
});


