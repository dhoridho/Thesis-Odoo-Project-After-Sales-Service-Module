odoo.define('equip3_pos_masterdata.RightHeaderButtons', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class RightHeaderButtons extends PosComponent {
       
    }

    RightHeaderButtons.template = 'RightHeaderButtons';
    Registries.Component.add(RightHeaderButtons);
    return RightHeaderButtons;
});
