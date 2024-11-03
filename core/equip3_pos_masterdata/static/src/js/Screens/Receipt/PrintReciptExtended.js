odoo.define('equip3_pos_masterdata.OrderReceiptBranchDetails', function (require) {'use strict';

    const Registries = require('point_of_sale.Registries');
    const OrderReceipt = require('point_of_sale.OrderReceipt');

    const RetailOrderReceiptNew = (OrderReceipt) =>
        class extends OrderReceipt {
            constructor() {
                super(...arguments);
                this._receiptEnv = this.props.order.getOrderReceiptEnv();
            }
            get branch_information() {
                var order = this.env.pos.get_order();
                return order.pos_config_branch_info;
            }
        }

    Registries.Component.extend(OrderReceipt, RetailOrderReceiptNew);
    Registries.Component.add(RetailOrderReceiptNew);
    return OrderReceipt;
});