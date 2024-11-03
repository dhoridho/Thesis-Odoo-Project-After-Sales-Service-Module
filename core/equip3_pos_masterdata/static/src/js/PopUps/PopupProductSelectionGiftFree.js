odoo.define('equip3_pos_masterdata.PopupProductSelectionGiftFree', function (require) {
    'use strict';

    const {useState, useRef, useContext} = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');
    const {useExternalListener} = owl.hooks;

    class PopupProductSelectionGiftFree extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }

        get imageUrl() {
            const product = this.props.product;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }

        clickProduct(product) {
            var qty = this.props.qty_free * this.props.directly.quantity_free
            this.props.order.add_promotion_gift(product, 0, qty, {
                promotion: true,
                promotion_id: this.props.promotion.id,
                promotion_reason: this.props.promotion.name
            })
            this.confirm()
        }

        selectTabApply(products){
            this.props.tab_active = products
            this.render()
        }

        selectTypeApply(type_apply) {
            var quickly_add = false
            if(type_apply=='same_product'){
                quickly_add = true
                var qty = this.props.qty_free * this.props.same_product.quantity_free
                var product = this.props.product
            }
            if(type_apply=='selected_product'){
                if(this.props.selected_products_gift_free.length==1){
                    var qty = this.props.qty_free * this.props.selected_product.quantity_free
                    var product = this.props.selected_products_gift_free[0]
                    quickly_add = true
                }
                else {
                    this.props.list_products = this.props.selected_products_gift_free
                    this.props.directly = this.props.selected_product
                    this.render()
                }
            }
            if(type_apply=='same_lower_price'){
                if(this.props.same_lower_price_gift_free.length==1){
                    var qty = this.props.qty_free * this.props.same_lower_price.quantity_free
                    var product = this.props.same_lower_price_gift_free[0]
                    quickly_add = true
                }
                else {
                    this.props.directly = this.props.same_lower_price
                    this.props.list_products = this.props.same_lower_price_gift_free
                    this.render()
                }
            }


            if(quickly_add){
                this.props.order.add_promotion_gift(product, 0, qty, {
                    promotion: true,
                    promotion_id: this.props.promotion.id,
                    promotion_reason: this.props.promotion.name
                })
                this.confirm()
            }

        }

        

    }

    PopupProductSelectionGiftFree.template = 'PopupProductSelectionGiftFree';
    PopupProductSelectionGiftFree.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        array: [],
        isSingleItem: false,
    };

    Registries.Component.add(PopupProductSelectionGiftFree);

    return PopupProductSelectionGiftFree
});
