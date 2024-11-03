odoo.define('point_of_sale.CopyRight', function (require) {
    'use strict';

    const {useState} = owl;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CopyRight extends PosComponent {
        constructor() {
            super(...arguments);
        }

        async onClick() {
            let {confirmed, payload: result} = await this.showPopup('ConfirmPopup', {
                    title: 'Welcome to HashMicro POS',
                    body: 'Copyright (c) of HashMicro \n' +
                        '  Email: support@hashmicro.com \n' +
                        '  Website: www.hashmicro.com',
                disableCancelButton: true,
            })
            if (confirmed) {
                window.open('https://join.skype.com/invite/j2NiwpI0OFND', '_blank')
            } else {
                window.open('https://apps.odoo.com/apps/modules/14.0/pos_retail/', '_blank')
            }
        }
    }

    CopyRight.template = 'CopyRight';

    Registries.Component.add(CopyRight);

    return CopyRight;
});
