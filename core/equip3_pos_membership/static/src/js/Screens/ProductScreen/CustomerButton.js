odoo.define('equip3_pos_membership.CustomerButton', function (require) {
    'use strict';

    const CustomerButton = require('equip3_pos_masterdata.CustomerButton')
    const Registries = require('point_of_sale.Registries')

    const PosMemCustomerButton = (CustomerButton) =>
        class extends CustomerButton {
            constructor() {
                super(...arguments);
            }

            defaultLabel() {
                let res = super.defaultLabel();
                res = 'Member';
                return res;
            }
        }
        
    Registries.Component.extend(CustomerButton, PosMemCustomerButton);
    return PosMemCustomerButton;
});
