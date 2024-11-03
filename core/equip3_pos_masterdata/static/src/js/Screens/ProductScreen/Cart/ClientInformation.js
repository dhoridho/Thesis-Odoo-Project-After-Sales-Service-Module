odoo.define('equip3_pos_masterdata.ClientInformation', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ClientInformation extends PosComponent {
        constructor() {
            super(...arguments);
            this.currentOrder = this.props.currentOrder
        }

        async showPurchasedHistories() {
            if (this.env.pos.get_order()) {
                const {confirmed, payload: result} = await this.showTempScreen(
                    'PosOrderScreen',
                    {
                        order: null,
                        selectedClient: this.env.pos.get_order().get_client()
                    }
                );
            } else {
                const {confirmed, payload: result} = await this.showTempScreen(
                    'PosOrderScreen',
                    {
                        order: null,
                        selectedClient: null
                    }
                );
            }
        }

    }

    ClientInformation.template = 'ClientInformation';

    Registries.Component.add(ClientInformation);

    return ClientInformation;
});
