odoo.define('equip3_pos_general.ProductsWidgetControlPanel', function (require) {
    'use strict';

    const {Gui} = require('point_of_sale.Gui');
    const ProductsWidgetControlPanel = require('point_of_sale.ProductsWidgetControlPanel');
    const Registries = require('point_of_sale.Registries');

    const GeneralProductsWidgetControlPanel = (ProductsWidgetControlPanel) =>
        class extends ProductsWidgetControlPanel {
            async mounted() {
                await super.mounted;
                this.env.pos.showAllCategory = false;
                this.state.showAllCategory = true;
                this.trigger('show-categories');
            }
            async setProductsView() {
                if (this.env.pos.config.product_view == 'list') {
                    this.env.pos.config.product_view = 'box'
                } else {
                    this.env.pos.config.product_view = 'list'
                }
                await this.rpc({
                    model: 'pos.config',
                    method: 'write',
                    args: [[this.env.pos.config.id], {
                        product_view: this.env.pos.config.product_view,
                    }],
                })
                this.env.qweb.forceUpdate();
            }

            async addCustomSale() {
                
                let {confirmed, payload: productName} = await this.showPopup('TextAreaPopup', {
                    title: this.env._t('What a Custom Sale (Product Name)'),
                    startingValue: ''
                })
                console.log("Hello world!");
                if (confirmed) {
                    let product = this.env.pos.db.get_product_by_id(this.env.pos.config.custom_sale_product_id[0]);
                    if (product) {
                        let {confirmed, payload: number} = await this.showPopup('NumberPopup', {
                            'title': this.env._t('What Price of ') + productName,
                            'startingValue': 0,
                        });
                        if (confirmed) {
                            const selectedOrder = this.env.pos.get_order()
                            product.display_name = productName
                            selectedOrder.add_product(product, {
                                //price_extra: 0,
                                price: parseFloat(number),
                                quantity: 1,
                                merge: false,
                            })
                            let selectedLine = selectedOrder.get_selected_orderline()
                            selectedLine.set_full_product_name(productName)
                            this.showPopup('ConfirmPopup', {
                                title: productName + this.env._t(' add to Cart'),
                                body: this.env._t('You can modifiers Price and Quantity of Item'),
                                disableCancelButton: true,
                            })
                        }

                    } else {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env.pos.config.custom_sale_product_id[1] + this.env._t(' not Available In POS'),
                        })
                    }
                }
            }
        }
    Registries.Component.extend(ProductsWidgetControlPanel, GeneralProductsWidgetControlPanel);

    return GeneralProductsWidgetControlPanel;
});
