odoo.define('equip3_pos_masterdata.big_data_load', function (require) {
    "use strict";

    const models = require('point_of_sale.models');
    const time = require('web.time');

    models.load_models([
        {
            label: 'Stock Production Lot',
            model: 'stock.production.lot',
            fields: ['active', 'write_date', 'name', 'ref', 'product_id', 'product_uom_id', 'create_date', 'product_qty', 'barcode', 'replace_product_public_price', 'public_price', 'expiration_date'],
            lot: true,
            installed: true,
            context: function (self) {
                return {sql_search_read: true}
            },
            domain: function (self) {
                let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                console.log('LOADED Stock Production Lot expiration_date is after or equal to: ', current_date)
                return  ['|', ['expiration_date','>=', current_date], ['expiration_date','=', false]];
            },
            loaded: function (self, lots) {
                let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                lots = lots.filter(l => {
                    let is_expired = !l.expiration_date;
                    if(l.expiration_date){
                        is_expired =  moment(l.expiration_date).isSameOrAfter(current_date);
                    }
                    return is_expired;
                });
                self.lots = lots;
                self.lot_by_name = {};
                self.lot_by_id = {};
                self.lot_by_product_id = {};
                for (let i = 0; i < self.lots.length; i++) {
                    let lot = self.lots[i];
                    self.lot_by_name[lot['name']] = lot;
                    self.lot_by_id[lot['id']] = lot;
                    if (!self.lot_by_product_id[lot.product_id[0]]) {
                        self.lot_by_product_id[lot.product_id[0]] = [lot];
                    } else {
                        self.lot_by_product_id[lot.product_id[0]].push(lot);
                    }
                }
            }
        },
    ], {
        before: 'product.pricelist'
    });

});