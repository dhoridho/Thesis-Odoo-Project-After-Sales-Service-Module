odoo.define('equip3_pos_emenu.EmenuQRCodeLabel', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const core = require('web.core');
    const QWeb = core.qweb;
    const { useState } = owl.hooks;


    class EmenuQRCodeLabel extends PosComponent {
        constructor() {
            super(...arguments);

            this.receipt_template = this.env.pos.get_receipt_template();
            let order = this.env.pos.get_order();
            this.default = {
                company_logo_url: '/web/image?model=res.company&id=' + this.env.pos.company.id + '&field=logo',
                company_name: this.env.pos.company.name,
                outlet_name: this.env.pos.config.name,
                floor_table: false,
                printed_date: moment.utc(this.props.printed_date).local().format("DD MMM YYYY  hh:mm a"),
            }
            if(order.floor){
                this.default.floor_table = order.floor.name;
            }
            if(order.table){
                this.default.floor_table += '/' + order.table.name;
            }
        }

        get_emenu_qrcode_url(){
            return '/report/barcode?type=QR&value=' + this.props.emenu_url + ' &width=300&height=300';
        }
 
    }

    EmenuQRCodeLabel.template = 'EmenuQRCodeLabel';
    Registries.Component.add(EmenuQRCodeLabel);
    return EmenuQRCodeLabel;
});
