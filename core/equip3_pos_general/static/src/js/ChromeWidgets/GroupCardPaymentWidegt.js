odoo.define('equip3_pos_masterdata.GroupCardPaymentWidegt', function(require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class GroupCardPaymentWidegt extends PosComponent {
    };
    GroupCardPaymentWidegt.template = 'GroupCardPaymentWidegt';

    Registries.Component.add(GroupCardPaymentWidegt);

    return GroupCardPaymentWidegt;
});