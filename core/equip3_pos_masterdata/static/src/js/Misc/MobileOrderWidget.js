odoo.define('equip3_pos_masterdata.MobileOrderWidget', function (require) {
    'use strict';

    const MobileOrderWidget = require('point_of_sale.MobileOrderWidget');
    const Registries = require('point_of_sale.Registries');

    let updateRenderOrderTimeout = null;
    let updateRenderOrderLineTimeout = null;

    const RetailMobileOrderWidget = (MobileOrderWidget) =>
        class extends MobileOrderWidget {

            // OVERRIDE
            mounted() {
                let self = this;
                this.order.on('change', () => {
                    clearTimeout(updateRenderOrderTimeout);
                    updateRenderOrderTimeout = setTimeout(function() {
                        self.update();
                        self.render();
                    }, 300);
                });
                this.order.orderlines.on('change', () => {
                    clearTimeout(updateRenderOrderLineTimeout);
                    updateRenderOrderLineTimeout = setTimeout(function() {
                        self.update();
                        self.render();
                    }, 300);
                });
            }

            async selectClient() {
                const selectedOrder = this.env.pos.get_order()
                if (selectedOrder) {
                    this.currentOrder = selectedOrder
                    const currentClient = this.currentOrder.get_client();
                    const {confirmed, payload: newClient} = await this.showTempScreen(
                        'ClientListScreen',
                        {client: currentClient}
                    );
                    if (confirmed) {
                        this.currentOrder.set_client(newClient);
                        this.currentOrder.updatePricelist(newClient);
                    }
                }

            }
        }
    Registries.Component.extend(MobileOrderWidget, RetailMobileOrderWidget);

    return RetailMobileOrderWidget;
});
