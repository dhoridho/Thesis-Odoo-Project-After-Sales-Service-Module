odoo.define('equip3_pos_general.CrossSalePopUps', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const {useExternalListener} = owl.hooks;

    class CrossSalePopUps extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */

        constructor() {
            super(...arguments);

            useExternalListener(window, 'keyup', this._keyUp);
            this.env.pos.lockedUpdateOrderLines = true; // todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
        }

        mounted() {
            super.mounted();
            this.env.pos.lockedUpdateOrderLines = true; // todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
        }

        willUnmount() {
            super.willUnmount();
            const self = this;
            setTimeout(function () {
                self.env.pos.lockedUpdateOrderLines = false; // timeout 0.5 seconds unlock todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
            }, 500)
        }

        async _keyUp(event) {
            console.log('[CrossSalePopUps_keyboardHandler]: ', event.key)
            if (event.key == 'Enter') {
                await this.confirm();
            }
            const key = parseInt(event.key)
            if ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9].includes(key)) {
                let $target = $('.cross-sale-inner > .cross-card-box:nth-child('+ event.key +')');
                if($target.length){
                    $target.click();
                }
            }
        }

        display_name(rec){
            let self = this;
            let display_name = rec.product_id[1];
            if(self.env.pos.config && self.env.pos.config.display_product_name_without_product_code){
                return display_name.replace(/[\[].*?[\]] */, '');
            }
            return display_name;
        }

        image_url(rec){
            return `/web/image?model=product.product&field=image_128&id=${rec.product_id[0]}&write_date=1&unique=1`;
        }
        async get_product_object(product_id){
            console.warn('[get_product_object] product_id:', product_id);
            let self = this;
            if (self.env.pos.config.show_product_template) {
                var product = self.env.pos.db.get_product_template_by_id(product_id); 
            } else {
                var product = self.env.pos.db.get_product_by_id(product_id);
            }
            return product;
        }
        
        display_price(rec){
            return this.env.pos.format_currency(rec.list_price);
        }

        _view_mode(){
            if (this.env.pos.config.hide_product_image) {
                return 'list-view';
            }
            return 'card-view';
        }

        get view_mode(){
            if (this.env.pos.config.hide_product_image) {
                return 'list-view';
            }
            return 'card-view';
        }

        async selectOption(event){
            let $target = $(event.target).closest('.cross-card-box')
            if($target.hasClass('selected')){
                $target.removeClass('selected');
            }else{
                $target.addClass('selected');
            }
        }

        getSelectedItemIds(){
            let item_ids = [];
            if(this._view_mode() == 'list-view'){
                $('.cross_sale_popups .cross-sale-line input[type=checkbox]:checked').each(function(){
                    item_ids.push($(this).data('id'))
                });
            }
            if(this._view_mode() == 'card-view'){
                $('.cross_sale_popups .cross-card-box.selected').each(function(){
                    item_ids.push($(this).data('id'))
                });
            }
            return item_ids;
        }
        
        getPayload() {
            let item_ids = this.getSelectedItemIds();
            return {
                items: this.props.items.filter((i)=>item_ids.includes(i.id)),
            }
        }

        confirm(){
            if(!this.getSelectedItemIds().length){
                return;
            }
            super.confirm();
        }
    }
    
    CrossSalePopUps.template = 'CrossSalePopUps';
    CrossSalePopUps.defaultProps = {
        confirmText: 'Add Cart',
        cancelText: 'Cancel',
        title: 'Product Suggestions',
        body: '',
    };
    Registries.Component.add(CrossSalePopUps);
    return CrossSalePopUps;
});
