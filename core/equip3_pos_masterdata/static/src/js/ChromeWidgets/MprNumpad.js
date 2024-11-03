odoo.define('point_of_sale.MprNumpad', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class MprNumpad extends PosComponent {
        constructor() {
            super(...arguments);
            this.decimalPoint = this.env._t.database.parameters.decimal_point;
        }
    }
    MprNumpad.template = 'MprNumpad';

    Registries.Component.add(MprNumpad);

    return MprNumpad;
});
