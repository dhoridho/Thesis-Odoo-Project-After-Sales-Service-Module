odoo.define('equip3_pos_masterdata.CustomPosComboConfigurePopup', function(require) {
    'use strict';

    const { useState, useSubEnv } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    class PosComboConfigurePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.title = this.props.title || '';
            this.product = this.props.product || false;
            this.pos_combo_id = this.props.pos_combo_id || false;
            this.combos = [];
        }
        get combo_items_ids(){
            return this.get_combo_products()
        }
        mounted(){
            jQuery('.ft-btn-container').show();
            jQuery('#btn-pr-apply, #btn-pr-back').hide();
            jQuery('#btn-pr-choose, #btn-pr-cancel').show();
            jQuery('.combo-product-container').hide();
        }
        get_combo_products(){
            // var self = this;
            // let items = _.filter(posmodel.db.pos_combos_items_by_id, (val, key)=>{
            //     return val.combo_option_id && val.combo_option_id[0] == self.pos_combo_id;
            // });
            // return _.map(posmodel.db.pos_combos_items_by_id, (val, key)=>{
            //     return val.id;
            // });
            return this.product.combo_option_items
        }
        get_product(item_id){
            var item = this.env.pos.db.get_pos_combos_items_by_id(item_id);
            var product = this.env.pos.db.get_product_by_id(item.product_variant_id[0]);
//            return (product && this.props.pos_categories_list.includes(product.pos_categ_id[0])) ? product : false;
            return (product) ? product : false;
        }
        get_extra_product(item_id){
            var item = this.env.pos.db.get_pos_combos_items_by_id(item_id);
            return item.extra_price;
        }
        get_product_items(){
            var self = this;
            let datas = [];
            var items = $(this.el).find('article.product.pselected');
            _.each(items, function(item){
                var skd = $(item).data();
                var product = self.env.pos.db.get_product_by_id(skd['product_id']);
                datas.push({'product':product, 'price': skd['extra_price']});
            });
            return datas;
        }
        getPayload() {
            return this.get_product_items();
        }
        loadComboOptions() {
            this.props.combo_selected_category_type = jQuery('#combo_pos_categ:checked').val();
            if (jQuery('#combo_pos_categ:checked').val() == 'appetizer') {
                jQuery('.combo_type_appetizer').show();
                jQuery('.combo_type_main, .combo_type_dessert').hide();
            } else if (jQuery('#combo_pos_categ:checked').val() == 'main') {
                jQuery('.combo_type_main').show();
                jQuery('.combo_type_appetizer, .combo_type_dessert').hide();
            } else if (jQuery('#combo_pos_categ:checked').val() == 'dessert') {
                jQuery('.combo_type_dessert').show();
                jQuery('.combo_type_appetizer, .combo_type_main').hide();
            } else {
                alert('Please select combo category option.');
                return 0;
            }
            jQuery('#btn-pr-apply, #btn-pr-back').show();
            jQuery('#btn-pr-choose, #btn-pr-cancel').hide();
            jQuery('.opt-categ-type-container').hide();
            jQuery('.combo-product-container').show();
        }
        backToOption() {
            jQuery('#btn-pr-apply, #btn-pr-back').hide();
            jQuery('#btn-pr-choose, #btn-pr-cancel').show();
            jQuery('.opt-categ-type-container').show();
            jQuery('.combo-product-container').hide();
        }
    };
    PosComboConfigurePopup.template = 'PosComboConfigurePopup';
    Registries.Component.add(PosComboConfigurePopup);

    return {
        PosComboConfigurePopup: PosComboConfigurePopup
    };

});