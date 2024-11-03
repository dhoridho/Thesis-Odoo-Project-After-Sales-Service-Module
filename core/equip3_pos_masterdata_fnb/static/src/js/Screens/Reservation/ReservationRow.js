odoo.define('equip3_pos_masterdata_fnb.ReservationRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {useState} = owl.hooks;

    class ReservationRow extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                refresh: 'done',
            });
        }

        async cancelOrder(order){
            let reserve_order = await this.rpc({
                model: 'reserve.order',
                method: 'cancel_order',
                args: [[order.id]]
            });

            let orders = this.env.pos.db.get_reserve_order();
            for (var i = orders.length - 1; i >= 0; i--) {
                if(orders[i].id == order.id){
                    orders[i].state = 'cancel';
                    break;
                }
            }
        }

        async _autoSyncBackend() {
            if(this.props.order){
                this.state.refresh = 'connecting';
                let _object = this.env.pos.get_model('reserve.order');
                let fields = _object.fields; 
                let orders = await this.rpc({
                    model: 'reserve.order',
                    method: 'search_read',
                    fields: fields,
                    args: [[['id', '=', this.props.order.id]]]
                })
                this.state.refresh = 'done';
                this.props.order = orders[0];
                this.render();
            }
        }

        get getHighlight() {
            return this.props.order !== this.props.selectedOrder ? '' : 'highlight';
        }
    }

    ReservationRow.template = 'ReservationRow';
    Registries.Component.add(ReservationRow);
    return ReservationRow;
});
