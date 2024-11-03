odoo.define('equip3_pos_general_fnb.Orderline', function (require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');
    const {useState} = owl.hooks;

    const FnbOrderLine = (Orderline) =>
        class extends Orderline {
            constructor() {
                super(...arguments);
            }
   
            async onChangeBomComponents(line, option) {
                let self = this;
                let product = line.product;
                //BoM Product
                let add_values = {};
                let {confirmed, payload: values} = await self.showPopup('CustomizeBomPopUps', {
                    title: product.display_name.replace(/[\[].*?[\]] */, ''),
                    components: self.env.pos.db.get_pos_bom_component_by_ids(option.pos_bom_line_ids),
                    bom_component_notes:option.bom_component_notes,
                    bom_components_select:option.bom_components,
                    confirmText: self.env._t('Save Change'),
                    cancelText: self.env._t('Cancel'),
                });
                if(confirmed){
                    add_values['bom_components'] = values['components'];
                    add_values['bom_component_notes'] = values['notes'];
                }

                if(add_values.bom_components && typeof add_values.bom_components != 'undefined' && add_values.bom_components.length){
                    for (var i = line.pos_combo_options.length - 1; i >= 0; i--) {
                        if(line.pos_combo_options[i].id == option.id){
                            line.pos_combo_options[i].bom_components = add_values.bom_components;
                            line.pos_combo_options[i].bom_component_notes = add_values.bom_component_notes;
                        }
                    } 
                }
            }

            isBomComponentsConfigurable(option){
                let self = this;
                if(option.bom_components){
                    let customize_bom = self.env.pos.config.customize_bom;
                    let components = self.env.pos.db.get_pos_bom_component_by_ids(option.pos_bom_line_ids);
                    let is_configure_components = components.length!=0?components[0].is_configure_components:false;
                    if(is_configure_components && customize_bom){
                        return true
                    }
                }
                return false;
            }

            async onChangeComboAndBomOptions(line){
                await line.confirm_combo_and_bom_product();
            }
            
            isShowChangeComboAndBomOptions(line){
                let need_confirm = false;
                if(line.product.pos_bom_id){
                    if(!line.bom_components){
                        need_confirm = true;
                    }
                }else if(line.product.is_combo_product_new){
                    if(!line.pos_combo_options){
                        need_confirm = true;
                    }
                }
                if(need_confirm){
                    return true
                }
                return false
            }

        }


    Registries.Component.extend(Orderline, FnbOrderLine);
    return FnbOrderLine;
});
