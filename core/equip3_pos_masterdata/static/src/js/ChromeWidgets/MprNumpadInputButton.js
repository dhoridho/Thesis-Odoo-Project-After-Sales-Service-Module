odoo.define('point_of_sale.MprNumpadInputButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class MprNumpadInputButton extends PosComponent {
        get _class() {
            return this.props.changeClassTo || 'input-button number-char';
        }
    }
    MprNumpadInputButton.template = 'MprNumpadInputButton';

    Registries.Component.add(MprNumpadInputButton);

    return MprNumpadInputButton;
});
