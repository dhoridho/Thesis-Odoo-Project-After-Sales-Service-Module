odoo.define('equip3_pos_membership.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen')
    const Registries = require('point_of_sale.Registries')

    const PosMemProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            }

            async _onClickPay() {
                let selectedOrder = this.env.pos.get_order();
                if (!this.env.session.restaurant_order) {
                    if (this.env.pos.retail_loyalty && selectedOrder.get_client()) {
                        let pointsSummary = selectedOrder.get_client_points()
                        if (pointsSummary['pos_loyalty_point'] < pointsSummary['redeem_point']) {
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Error'),
                                body: this.env._t("You can not set Redeem points bigger than Customer's Points: ") + this.env.pos.format_currency_no_symbol(pointsSummary['pos_loyalty_point'])
                            })
                        }
                    }
                }
                super._onClickPay();
            }
        }
        
    Registries.Component.extend(ProductScreen, PosMemProductScreen);
    return PosMemProductScreen;
});
