odoo.define('equip3_pos_masterdata_fnb.EditBar', function(require) {
    'use strict';

    const EditBar = require('pos_restaurant.EditBar');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;

    EditBar.template = 'EditBarFnB';
    return EditBar;
});
