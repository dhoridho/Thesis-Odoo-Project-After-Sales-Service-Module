odoo.define('equip3_pos_general_fnb.KitchenOrderLineDetail', function (require) {
    'use strict';

    const KitchenOrderLineDetail = require('equip3_pos_masterdata.KitchenOrderLineDetail');
    const Registries = require('point_of_sale.Registries');

    const KitchenOrderLineDetailExt = (KitchenOrderLineDetail) =>
     class extends KitchenOrderLineDetail {
        constructor() {
            super(...arguments)
        } 

        bom_combo_display_name(rec){
            let self = this;
            let display_name = rec.product_id[1];
            if(self.env.pos.config && self.env.pos.config.display_product_name_without_product_code){
                return display_name.replace(/[\[].*?[\]] */, '');
            }
            return display_name;
        }

        get_bom_components_display() {
            let self = this;
            let html = '';
            if(this.props.line){

                function display_name(rec){
                    let display_name = rec.product_id[1];
                    if(self.env.pos.config && self.env.pos.config.display_product_name_without_product_code){
                        return display_name.replace(/[\[].*?[\]] */, '');
                    }
                    return display_name;
                }

                let components = this.props.line.bom_components;
                if(components){
                    for (var i = components.length - 1; i >= 0; i--) {
                        let com = components[i];
                        let product_name = display_name(com);
                        let product_qty = com.product_qty;
                        if(com.is_extra){
                            if(com.checked){
                                html += ' <div class="extra-component"> '+ product_qty + 'X Extra ' + product_name + '</div> ';
                            }
                        }else{
                            if(!com.checked){
                                html += ' <div class="extra-component">No ' + product_name + '</div> ';
                            }
                        }
                    }
                }
            }
            return html;
        }

    }

    Registries.Component.extend(KitchenOrderLineDetail, KitchenOrderLineDetailExt);
    return KitchenOrderLineDetailExt;

});