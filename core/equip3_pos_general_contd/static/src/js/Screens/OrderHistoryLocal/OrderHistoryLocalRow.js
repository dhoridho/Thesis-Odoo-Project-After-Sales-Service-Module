odoo.define('equip3_pos_general_contd.OrderHistoryLocalRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class OrderHistoryLocalRow extends PosComponent {
        constructor() {
            super(...arguments);
        } 

        getDate(order){
            return moment(order.creation_date).format('YYYY-MM-DD hh:mm A');
        }

        getCustomer(order){
            if (order.partner_id) {
                if(this.env.pos.db.partner_by_id){
                    let partner = this.env.pos.db.partner_by_id[order.partner_id]
                    return partner.name;
                }
            }
            return '';
        }

        getCashier(order){
            if (order.cashier_id) {
                let cashier = this.env.pos.user_by_id[order.cashier_id];
                if (cashier) {
                    return cashier.name;
                }
            }
            return '';
        }

        getSyncState(order){
            if (order.sync_state) {
                return order.sync_state;
            }
            return 'Not Sync';
        }

    }

    OrderHistoryLocalRow.template = 'OrderHistoryLocalRow';
    Registries.Component.add(OrderHistoryLocalRow);
    return OrderHistoryLocalRow;
});
