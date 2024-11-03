odoo.define('equip3_pos_masterdata.SaleOrderScreenWidget', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class SaleOrderScreenWidget extends PosComponent {
        async onClick() {
            if (this.env.pos.get_order()) {
                this.showTempScreen(
                    'SaleOrderList',
                    {
                        order: null,
                        selectedClient: this.env.pos.get_order().get_client()
                    }
                );
            } else {
                this.showTempScreen(
                    'SaleOrderList',
                    {
                        order: null,
                        selectedClient: null
                    }
                );
            }
        }

        mounted() {
            posbus.on('reload-orders', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-orders', this, null);
        }

        get isHidden() {
            if (!this.env || !this.env.pos || !this.env.pos.config || (this.env && this.env.pos && this.env.pos.config && !this.env.pos.config.booking_orders)) {
                return true
            } else {
                return false
            }
        }

        get count() {
            if (this.env.pos && this.env.pos.booking_in_state_sale_ids && this.env.pos.booking_in_state_sale_ids.length > 0) {
                return this.env.pos.booking_in_state_sale_ids.length;
            } else {
                return 0
            }
        }
    }

    SaleOrderScreenWidget.template = 'SaleOrderScreenWidget';

    Registries.Component.add(SaleOrderScreenWidget);

    return SaleOrderScreenWidget;
});
