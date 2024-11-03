odoo.define('equip3_pos_masterdata_fnb.ReservationListWidget', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class ReservationListWidget extends PosComponent {
        async onClick() {
            await this.env.pos.getReserveOrders();
            if (this.env.pos.get_order()) {
                const {confirmed, payload: nul} = await this.showTempScreen(
                    'ReservationList',
                    {
                        order: null,
                        selectedClient: this.env.pos.get_order().get_client()
                    }
                );
            } else {
                const {confirmed, payload: nul} = await this.showTempScreen(
                    'ReservationList',
                    {
                        order: null,
                        selectedClient: null
                    }
                );
            }
        }

        mounted() {
            posbus.on('reload-reservations', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-reservations', this, null);
        }

        get isHidden() {
            return false;
            if (!this.env || !this.env.pos || !this.env.pos.config || (this.env && this.env.pos && this.env.pos.config && !this.env.pos.config.table_reservation_list)) {
                return true;
            } else {
                return false;
            }
        }

        get count() {
            let reserve_orders = this.env.pos.db.get_reserve_order();
            if (this.env.pos &&  reserve_orders.length > 0) {
                return reserve_orders.length;
            } else {
                return 0;
            }
        }
    }

    ReservationListWidget.template = 'ReservationListWidget';
    Registries.Component.add(ReservationListWidget);
    return ReservationListWidget;
});
