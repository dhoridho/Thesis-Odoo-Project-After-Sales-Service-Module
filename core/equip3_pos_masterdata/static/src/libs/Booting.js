odoo.define('equip3_pos_masterdata.web_client', function (require) {
    'use strict';
    
    const  WebClient = require('web.WebClient');
    const indexed_db = require('equip3_pos_masterdata.indexedDB');

    WebClient.include({
        async startPosApp(webClient, indexed_db) {
            let initIndexDB = new indexed_db(webClient.env.session);
            await initIndexDB.get_datas('product.product', 1)
            await initIndexDB.get_datas('product.template', 1)
            await initIndexDB.get_datas('product.template.barcode', 1)
            await initIndexDB.get_datas('stock.production.lot', 1)
            await initIndexDB.get_datas('stock.quant', 1)
            await initIndexDB.get_datas('product.brand', 1)
            await initIndexDB.get_datas('pos.voucher', 1)
            await initIndexDB.get_datas('product.pricelist.item', 1)
            await initIndexDB.get_datas('res.partner', 1)
            await initIndexDB.get_datas('pos.order', 1)
            await initIndexDB.get_datas('pos.order.line', 1)
            webClient.env.session.indexed_db = initIndexDB;
        },

        show_application: function () {
            const res = this._super.apply(this, arguments);
            this.startPosApp(this, indexed_db);
            return res
        },
    });
});
