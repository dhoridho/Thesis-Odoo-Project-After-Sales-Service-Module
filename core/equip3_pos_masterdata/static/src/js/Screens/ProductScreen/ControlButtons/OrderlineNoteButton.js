odoo.define('equip3_pos_masterdata.OrderlineNoteButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const OrderlineNoteButton = require('pos_restaurant.OrderlineNoteButton');
    const Registries = require('point_of_sale.Registries');

    const RetailOrderlineNoteButton = (OrderlineNoteButton) => class extends OrderlineNoteButton { }

    
    OrderlineNoteButton.template = 'RetailOrderlineNoteButton';
    Registries.Component.extend(OrderlineNoteButton, RetailOrderlineNoteButton);

    return RetailOrderlineNoteButton;
});
