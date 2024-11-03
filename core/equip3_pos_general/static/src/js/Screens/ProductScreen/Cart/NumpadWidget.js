odoo.define('equip3_pos_general.NumpadWidget', function (require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const {useState} = owl.hooks;
    const Registries = require('point_of_sale.Registries');

    NumpadWidget.template = 'NumpadWidgetRetail2';
    Registries.Component.add(NumpadWidget);
    const {Gui} = require('point_of_sale.Gui');

});