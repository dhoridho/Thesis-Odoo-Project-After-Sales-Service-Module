odoo.define('equip3_pos_masterdata.CustomerButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class CustomerButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.currentOrder = this.env.pos.get_order();
        }

        async OnClickCustomer() {
            await this.env.pos.syncPartner(false); 
            const currentClient = this.currentOrder.get_client();
            if (this.env.isMobile) {
                const { confirmed, payload: newClient } = await this.showTempScreen(
                    'ClientListScreen',
                    { client: currentClient }
                );
                if (confirmed) {
                    this.currentOrder.set_client(newClient);
                    this.currentOrder.updatePricelist(newClient);
                }
            } else {
                posbus.trigger('set-screen', 'Clients') // single screen
                setTimeout(function () {
                    $('.searchbox-client >input').focus()
                }, 200)
            }
        }

        defaultLabel(){
            return 'Customers';
        }

        get buttonLabel(){
            const currentClient = this.env.pos.get_order().get_client();
            return currentClient ? currentClient.name : this.defaultLabel();
        }

    }

    CustomerButton.template = 'CustomerButton';
    Registries.Component.add(CustomerButton);
    return CustomerButton;
});
