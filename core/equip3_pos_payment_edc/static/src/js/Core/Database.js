odoo.define('equip3_pos_payment_edc.Database', function (require) {
    'use strict';

    var PosDB = require('point_of_sale.DB'); 
    var _super_init_ = PosDB.prototype.init;
    const _super_db = PosDB.prototype;
    
    PosDB.prototype.init = function(options) {
        _super_init_.call(this, options);

        // TODO: stored pos payment installment tenor
        this.pos_payment_installment_tenor = [];
    };
    
    PosDB.include({
        save_payment_installment_tenor: function (records) {
            this.pos_payment_installment_tenor = records;
        },
    });
});