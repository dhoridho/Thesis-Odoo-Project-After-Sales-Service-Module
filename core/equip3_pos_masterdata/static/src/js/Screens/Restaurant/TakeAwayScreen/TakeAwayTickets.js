odoo.define('equip3_pos_masterdata.TakeAwayTickets', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class TakeAwayTickets extends PosComponent {
        async onClick() {
            await this.showScreen('TakeAwayScreen');
        }
    }
    TakeAwayTickets.template = 'TakeAwayTickets';

    Registries.Component.add(TakeAwayTickets);

    return TakeAwayTickets;
});