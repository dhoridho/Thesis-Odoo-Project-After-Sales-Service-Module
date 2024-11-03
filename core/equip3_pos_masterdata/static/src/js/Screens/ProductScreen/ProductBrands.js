odoo.define('equip3_pos_masterdata.ProductBrands', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const {useState} = owl.hooks;
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class ProductBrands extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                selectedBrand: this.env._t('Brands'),
                selectedbrandId: 0
            });
        }

        willUnmount() {
            super.willUnmount();
            this.env.pos.off('change:selectedBrandId', null, this);

        }

        mounted() {
            super.mounted();
            this.env.pos.on('change:selectedBrandId', this.updateSelectedBrandToState, this);
        }

        updateSelectedBrandToState() {
            let selectedBrandId = this.env.pos.get('selectedBrandId')
            let selectedBrand = this.env.pos.productByBrandId[selectedBrandId]
            if (selectedBrand) {
                this.state.selectedBrand = selectedBrand['name']
                this.state.selectedbrandId = selectedBrand['id']
            }
            this.render()
        }

    }

    ProductBrands.template = 'ProductBrands';

    Registries.Component.add(ProductBrands);

    return ProductBrands;
});
