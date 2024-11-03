odoo.define('equip3_pos_order_retail.PopUpCardComplementaryNote', function(require) {
    'use strict';

    const { useState, useSubEnv } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    class PopUpCardComplementaryNote extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }
        getPayload() {
            return '';
        }
    };
    PopUpCardComplementaryNote.template = 'PopUpCardComplementaryNote';
    Registries.Component.add(PopUpCardComplementaryNote);

    return {
        PopUpCardComplementaryNote: PopUpCardComplementaryNote
    };

});