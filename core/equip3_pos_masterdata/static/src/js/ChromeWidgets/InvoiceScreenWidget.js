odoo.define('equip3_pos_masterdata.InvoiceScreenWidget', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const {useState} = owl;

    class InvoiceScreenWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({  sync: '' });
        }

        async  onClick() {
            if(this.state.sync != 'connecting'){
                this.state.sync = 'connecting';
                await this.env.pos.syncInvoices();
                this.state.sync = 'done';
            }
            const {confirmed, payload: result} = await this.showTempScreen('AccountMoveScreen', { move: null,});
            if (confirmed) {
                debugger
            }
        }

        mounted() {
            posbus.on('reload-orders', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-orders', this, null);
        }

        get isHidden() {
            if (!this.env || !this.env.pos || !this.env.pos.config || (this.env && this.env.pos && this.env.pos.config && !this.env.pos.config.management_invoice)) {
                return true
            } else {
                return false
            }
        }

        get count() {
            if (this.env.pos && this.env.pos.db.invoice_ids && this.env.pos.db.invoice_ids.length > 0) {
                return this.env.pos.db.invoice_ids.length;
            } else {
                return 0
            }
        }
    }

    InvoiceScreenWidget.template = 'InvoiceScreenWidget';

    Registries.Component.add(InvoiceScreenWidget);

    return InvoiceScreenWidget;
});
