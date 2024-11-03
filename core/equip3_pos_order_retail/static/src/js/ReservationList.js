odoo.define('equip3_pos_order_retail.ReservationList', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class ReservationList extends PosComponent {
        onClick() {
            this.showScreen('ReservationScreen', {});
        }
        willPatch() {
            posbus.off('save-receipt', this);
        }

        patched() {
            posbus.on('save-receipt', this, this.render);
        }

        mounted() {
            posbus.on('save-receipt', this, this.render);
            $('#hm_pos_confg_name').text(this.env.pos.config.name)
        }

        willUnmount() {
            posbus.off('save-receipt', this);
        }

        get isHidden() {
            if (this.env.pos.config.table_reservation_list) {
                return true
            } else {
                return false
            }
        }

        get count() {
            return 0
        }
    }

    ReservationList.template = 'ReservationList';

    Registries.Component.add(ReservationList);

    return ReservationList;
});
