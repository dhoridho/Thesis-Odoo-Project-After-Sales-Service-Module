odoo.define('equip3_pos_masterdata.BarcodeReader', function (require) {
    var BarcodeReader = require('point_of_sale.BarcodeReader');
    const {posbus} = require('point_of_sale.utils');

    BarcodeReader.include({
        scan: async function (code) {
            this._super(code)
            const callbacks = Object.keys(this.exclusive_callbacks).length
                ? this.exclusive_callbacks
                : this.action_callbacks;

            let response = null
            if (callbacks && callbacks['loginBadgeId']) {
                response =  await [...callbacks['loginBadgeId']][0](code)
            }
            if (!response && callbacks && callbacks['validateManager']) {
                response =  await [...callbacks['validateManager']][0](code)
            }
            if (!response && callbacks && callbacks['voucher']) {
                response =  await [...callbacks['voucher']][0](code)
            }
            if (!response && callbacks && callbacks['new_order']) {
                response =  await [...callbacks['new_order']][0](code)
            }
        },
    });
});
