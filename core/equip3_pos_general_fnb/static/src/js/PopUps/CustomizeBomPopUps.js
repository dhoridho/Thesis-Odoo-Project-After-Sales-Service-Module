odoo.define('equip3_pos_general_fnb.CustomizeBomPopUps', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class CustomizeBomPopUps extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */
        constructor() {
            super(...arguments);
            this.state = useState({ notes: this.props.notes });
        }
        mounted() {

        } 

        display_name(rec){
            let self = this;
            let display_name = rec.product_id[1];
            if(self.env.pos.config && self.env.pos.config.display_product_name_without_product_code){
                return display_name.replace(/[\[].*?[\]] */, '');
            }
            return display_name;
        }

        covertCurrency(rec){
            var price = rec.additional_cost
            var order = this.env.pos.get_order()
            if(!order){
                this.env.pos.add_new_order();
                order = this.env.pos.get_order()
                price = this.env.pos.covertCurrency(order.pricelist,price)
            }
            else{
                price = this.env.pos.covertCurrency(order.pricelist,price)
            }
            return price
        }

        checkBomOptionalCheck(com){
            var res = false
            var bom_components_select = this.props.bom_components_select
            if (bom_components_select) {
                var checked_bom_js = bom_components_select.filter((c)=> c.id == com.id)
                    if(checked_bom_js && checked_bom_js[0].checked){
                        res = true
                    }
            }
            return res

        }


        configurableStatus(components){
            let not_configurable = components.filter((c)=> c.is_configurable == false);
            let state = 'configurable';
            if(not_configurable.length){
                state = 'partial_configurable';
            }
            if(components.length == not_configurable.length){
                state = 'not_configurable';
            }
            return state;
        }

        configurableShowingConfigurable(com){
            var class_show = '';
            if(!com.is_configurable){
                class_show = 'oe_hidden'
            }
            return class_show;
        }

        getPayload() {
            let self = this;
            let values = { notes: this.state.notes };
            let components = [];
            $('.bom-line input[type=checkbox]').each(function(){
                let $i = $(this);
                for (var i = self.props.components.length - 1; i >= 0; i--) {
                    let com = self.props.components[i];
                    if(com.id == parseInt($i.attr('data-id'))){
                        components.push({
                            additional_cost: self.covertCurrency(com),
                            bom_id: com.bom_id,
                            id: com.id,
                            is_extra: com.is_extra,
                            product_id: com.product_id,
                            product_qty: com.product_qty,
                            product_tmpl_id: com.product_tmpl_id,
                            full_product_name: com.full_product_name,
                            product_only_name: com.product_only_name,
                            checked: $i.is(':checked'),
                        });
                    }
                }
            });
            components.sort((a, b) => a.id - b.id);
            values['components'] = components;
            return values
        }
        confirm(){
            super.confirm();
        }
    }
    
    CustomizeBomPopUps.template = 'CustomizeBomPopUps';
    CustomizeBomPopUps.defaultProps = {
        confirmText: 'Add Cart',
        cancelText: 'Cancel',
        title: 'Customize BoM',
        body: '',
    };
    Registries.Component.add(CustomizeBomPopUps);
    return CustomizeBomPopUps;
});
