odoo.define('equip3_pos_general.HeaderButton', function(require) {
    'use strict';

    const { useState } = owl;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    // Previously HeaderButtonWidget
    // This is the close session button
    class HeaderButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ label: '' });
            this.confirmed = null;
        }
        get translatedLabel() {
            return this.env._t(this.state.label);
        }
        onClick() {
            console.warn('Double click to close pos');
            if (!this.confirmed) {
                this.state.label = '';
                this.confirmed = setTimeout(() => {
                    this.state.label = '';
                    this.confirmed = null;
                }, 2000);
            } else {
                this.trigger('close-pos');
            }
        }
    }
    HeaderButton.template = 'HeaderButton';

    Registries.Component.add(HeaderButton);

    return HeaderButton;
});
