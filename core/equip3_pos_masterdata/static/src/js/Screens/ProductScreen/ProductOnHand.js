odoo.define('equip3_pos_masterdata.ProductOnHand', function (require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useState} = owl.hooks;

    class ProductOnHand extends PosComponent {
        constructor() {
            super(...arguments);
            if (this.props.product.get_qty_available() <= 0) {
                var outstock = true
            } else {
                var outstock = false
            }
            this.state = useState({
                refreshStock: 'done',
                outstock: outstock,
                qty_available: this.props.product.get_qty_available()
            });
        }

        mounted() {
            const self = this
            super.mounted();
            this.env.pos.on('reload.quantity.available', () => this.reloadStock(), this);
        }

        willUnmount() {
            super.willUnmount();
            this.env.pos.off('reload.quantity.available', null, this);
        }

        reloadStock() {
            const self = this
            this.state.refreshStock = 'connecting'
            if (this.env.pos.config.show_product_template) {
                var name_model = 'product.template'
            }
            else{
                var name_model = 'product.product'
            }
            var qty_available = self.props.product.get_qty_available()
            if (qty_available <= 0) {
                self.state.outstock = true
            } else {
                self.state.outstock = false
            }
            self.state.qty_available = qty_available
            self.state.refreshStock = 'done'

            
        }
    }

    ProductOnHand.template = 'ProductOnHand';

    Registries.Component.add(ProductOnHand);

    return ProductOnHand;
});
