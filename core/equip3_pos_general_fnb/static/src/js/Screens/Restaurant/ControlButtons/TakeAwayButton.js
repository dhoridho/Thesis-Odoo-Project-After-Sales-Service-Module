odoo.define('equip3_pos_general_fnb.TakeAwayButton', function (require) {
    'use strict';

    const TakeAwayButton = require('equip3_pos_masterdata.TakeAwayButton');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const core = require('web.core');
    const QWeb = core.qweb;

    const GenFnbTakeAwayButton = (TakeAwayButton) =>
        class extends TakeAwayButton { 
            constructor() {
                super(...arguments);
            }

            async onClick() {
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

                    console.log('TakeAwayButton:confirm_combo_and_bom_product')

                    let confirmed_combo_and_bom_line = lines.filter( (l)=>l.is_from_cross_sale && (l.bom_components || l.pos_combo_options) );
                    if(combo_and_bom_line.length == confirmed_combo_and_bom_line.length){
                        super.onClick();
                    }
                }else{
                    super.onClick();
                }
            } 

        }

    ProductScreen.controlButtons = ProductScreen.controlButtons.filter((ar)=> ar.name != 'TakeAwayButton');
    Registries.Component.extend(TakeAwayButton, GenFnbTakeAwayButton);
    return GenFnbTakeAwayButton;
});