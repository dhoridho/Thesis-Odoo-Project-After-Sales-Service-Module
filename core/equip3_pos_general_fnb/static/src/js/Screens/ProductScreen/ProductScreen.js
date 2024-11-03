odoo.define('equip3_pos_general_fnb.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen')
    const Registries = require('point_of_sale.Registries')
    const {posbus} = require('point_of_sale.utils')
    const {useListener} = require('web.custom_hooks')
    const {useState} = owl.hooks
    const {Gui} = require('point_of_sale.Gui')
    const NumberBuffer = require('point_of_sale.NumberBuffer');


    const GenFnbProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            }

            mounted() {
                super.mounted();
            }

            willUnmount() {
                super.willUnmount()
            }
            
            continue_action(product){
                let self = this;
                let res = super.continue_action(product);
                if (self.env.pos.config.show_product_template) {
                    if(product.product_variant_ids){
                        product = self.env.pos.db.get_product_by_id(product.product_variant_ids[0]);
                    }
                }
                if(product && (product.pos_bom_id || product.is_combo_product_new)){
                    res = false;
                }
                return res;
            }

            is_combo_or_bom(product){
                let self = this;
                if (self.env.pos.config.show_product_template) {
                    if(product.product_variant_ids){
                        var product = self.env.pos.db.get_product_by_id(product.product_variant_ids[0]);
                    }
                }
                if(product && (product.pos_bom_id || product.is_combo_product_new)){
                    return true;
                }
                return false;
            }

            _is_merge_bom_components(val){
                let line = this.currentOrder.get_selected_orderline();
                if(line && val && line.bom_components && val.bom_components){
                    function getDifference(arr1, arr2) {
                        let array1 = Array.from(arr1, x => x).sort((a, b) => a.id - b.id);
                        let array2 = Array.from(arr2, x => x).sort((a, b) => a.id - b.id);
                        return array1.filter(
                            obj1 => !array2.some( obj2 => (obj1.id === obj2.id && (obj1.checked === obj2.checked)) ),
                        );
                    }
                    let arr1 = line.bom_components;
                    let arr2 = val.bom_components;
                    const difference = [...getDifference(arr1, arr2), ...getDifference(arr2, arr1)];
                    if(difference.length){
                        return false;
                    }
                }
                return true;
            }

            _is_merge_pos_combo_options(val){
                let line = this.currentOrder.get_selected_orderline();
                if(line && val && line.pos_combo_options && val.pos_combo_options){
                    function is_difference(array1, array2) {
                        const sortedArr1 = [...array1].sort();
                        const sortedArr2 = [...array2].sort();
                        return !(JSON.stringify(sortedArr1) === JSON.stringify(sortedArr2));
                    }
                    let arr1 = line.pos_combo_options.map((c)=>c.id);
                    let arr2 = val.pos_combo_options.map((c)=>c.id);
                    if(is_difference(arr1, arr2)){
                        return false;
                    }
                }
                return true;
            }

            async _clickProduct(event) {
                let self = this;
                let addProductBeforeSuper = false;
                let selectedOrder = null;

                let product = self.get_product_object(event.detail);
                let is_combo_or_bom = self.is_combo_or_bom(product);

                if(product && is_combo_or_bom){

                    console.warn('Click Product BOM & COMBO:', product);
                    let variants = self.get_product_variants(product);
                    if(variants.length > 1){
                        let {confirmed: variant_confirmed , payload: variant_selected} = await self.showPopup('SelectionPopup', {
                            title: self.env._t('Select Variant'),
                            list: variants,
                        });
                        if (variant_confirmed) {
                            product = variant_selected;
                        }
                        // Do not add product if cancel Select Variant.
                        if(!variant_confirmed){
                            return;
                        }
                    }else{
                        if(product.product_variant_ids){
                            product = self.env.pos.db.get_product_by_id(product.product_variant_ids[0]);
                        }
                    }
                    console.warn('Variant Object:', product);

                    //BoM Product
                    if(product && product.pos_bom_id){
                        let components = this.env.pos.db.get_pos_bom_components(product);
                        let customize_bom = self.env.pos.config.customize_bom;
                        let is_configure_components = components.length!=0?components[0].is_configure_components:false;
                        let add_values = {};
                        if(is_configure_components && customize_bom){
                            let {confirmed, payload: values} = await self.showPopup('CustomizeBomPopUps', {
                                title: product.display_name.replace(/[\[].*?[\]] */, ''),
                                components: components,
                                confirmText: self.env._t('Add Cart'),
                                cancelText: self.env._t('Cancel'),
                            });
                            if(confirmed){
                                add_values['bom_components'] = values['components'];
                                add_values['notes'] = values['notes'];
                            }
                            // Do not add product if cancel
                            if(!confirmed){
                                return;
                            }
                        }else{
                            let _components = [];
                            for (var i = components.length - 1; i >= 0; i--) {
                                if(!components[i].is_extra){
                                    let com = components[i];
                                    _components.push({
                                        additional_cost: com.additional_cost,
                                        bom_id: com.bom_id,
                                        id: com.id,
                                        is_extra: com.is_extra,
                                        product_id: com.product_id,
                                        product_qty: com.product_qty,
                                        product_tmpl_id: com.product_tmpl_id,
                                        checked: true,
                                    });
                                }
                            }
                            add_values['bom_components'] = _components;
                        }

                        if (!addProductBeforeSuper) {
                            if (!self.currentOrder) {
                                self.env.pos.add_new_order();
                            }
                            let options = await this._getAddProductOptions(product);

                            if(!self._is_merge_bom_components(add_values)){
                                options['merge'] = false;
                            }

                            // Do not add product if options is undefined.
                            if (!options){
                                // Do Nothing
                            } else{
                                // Add the product after having the extra information.
                                self.currentOrder.add_product(product, options);
                                NumberBuffer.reset();

                                if(add_values){
                                    let selectedLine = self.currentOrder.get_selected_orderline();
                                    if(add_values.bom_components && add_values.bom_components.length){
                                        selectedLine.bom_components = add_values.bom_components;
                                    }
                                    if(add_values.notes){
                                        selectedLine.set_note(add_values.notes);
                                    }
                                    selectedLine.trigger('change', selectedLine);
                                }
                            }
                        }
                        
                        //Skip Super super._clickProduct;
                        return;
                    }

                    // Combo Product New
                    if(product && product.is_combo_product_new){
                        if(!product.pos_bom_id){
                            let add_values = {};
                            let {confirmed, payload: values} = await self.showPopup('ComboOptionPopUps', {
                                title: product.display_name.replace(/[\[].*?[\]] */, ''),
                                combo: this.env.pos.db.get_pos_combo_product(product),
                            });
                            if(confirmed){
                                add_values['pos_combo_options'] = values['combo_options'];
                            }
                            // Do not add product if cancel
                            if(!confirmed){
                                return;
                            }

                            if (!addProductBeforeSuper) {
                                if (!self.currentOrder) {
                                    self.env.pos.add_new_order();
                                }
                                let options = await this._getAddProductOptions(product);

                                if(!self._is_merge_pos_combo_options(add_values)){
                                    options['merge'] = false;
                                }

                                // Do not add product if options is undefined.
                                if (!options){
                                    // Do Nothing
                                } else{
                                    // Add the product after having the extra information.
                                    self.currentOrder.add_product(product, options);
                                    NumberBuffer.reset();

                                    if(add_values){
                                        let selectedLine = self.currentOrder.get_selected_orderline();
                                        if(add_values.pos_combo_options && typeof add_values.pos_combo_options != 'undefined' && add_values.pos_combo_options.length){
                                            selectedLine.pos_combo_options = add_values.pos_combo_options;
                                        }
                                        selectedLine.trigger('change', selectedLine);
                                    }
                                }
                            }
                            
                            //Skip Super super._clickProduct;
                            return;
                        }
                    }

                }
                super._clickProduct(event);


            }
 
        }

    Registries.Component.extend(ProductScreen, GenFnbProductScreen);
    return GenFnbProductScreen;
});
