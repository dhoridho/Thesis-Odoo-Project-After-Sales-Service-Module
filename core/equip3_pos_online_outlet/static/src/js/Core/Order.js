odoo.define('equip3_pos_online_outlet.Order', function (require) {
    'use strict';

    const models = require('point_of_sale.models');

    let _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            _super_Order.initialize.apply(this, arguments);

        },
        add_product: async function (product, options) {
            let res = _super_Order.add_product.call(this, product, options);
	        if (options.force_price_price !== undefined){
	            this.selected_orderline.price = options.force_price_price;
	        }
            return res
        },
    });
});
