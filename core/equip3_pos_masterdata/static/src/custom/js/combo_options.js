odoo.define('equip3_pos_masterdata.combo_options', function(require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');

    class PosComboProductItem extends PosComponent {
        constructor() {
            super(...arguments);
        }
        get imageUrl() {
            const product = this.props.product;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }
        OnSelectComboProduct(event) {
            $(event.currentTarget).addClass('pselected');
        }
        onProductRemoveClick(event) {
            $(event.currentTarget).closest('.pselected').removeClass('pselected');
        }
        get price(){
            return this.env.pos.format_currency(this.props.extra_price);
        }
    }

    PosComboProductItem.template = 'PosComboProductItem';
    Registries.Component.add(PosComboProductItem);
    return PosComboProductItem;
});