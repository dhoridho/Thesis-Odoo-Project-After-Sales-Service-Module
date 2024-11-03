odoo.define('equip3_pos_printer_bluetooth.CategoryReceipt', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CategoryReceipt extends PosComponent {
        constructor() {
            super(...arguments);
            this._receiptEnv = this.props.changes;
            // this._receiptEnvOrderReceipt = this.props.order.getOrderReceiptEnv();
            // console.log(this._receiptEnvOrderReceipt.receipt)
            var order = this.env.pos.get_order()
        }
        willUpdateProps(nextProps) {
            this._receiptEnv = nextProps.changes;
        }
        get changes() {
            return this.receiptEnv;
        }
        // get receipt() {
        //     return this.receiptEnvOrderReceipt.receipt;
        // }
        get receiptEnv () {
          return this._receiptEnv;
        }
        // get receiptEnvOrderReceipt () {
        //   return this._receiptEnvOrderReceipt;
        // }

        get currentOrder() {
            return this.env.pos.get_order();
        }

        get computeChanges_orderlines(){
            var add = this.changes.new;
            var rem = this.changes.cancelled;
            return {
                'all': add.concat(rem),

            };

        }
        isSimple(line) {
            return (
                line.discount === 0 &&
                line.unit_name === 'Units' &&
                line.quantity === 1 &&
                !(
                    line.display_discount_policy == 'without_discount' &&
                    line.price < line.price_lst
                )
            );
        }
    }
    CategoryReceipt.template = 'CategoryReceipt';

    Registries.Component.add(CategoryReceipt);

    class ReCategoryReceipt extends PosComponent {
        constructor() {
            super(...arguments);

            this._receiptEnv = this.props.order.getOrderReceiptEnv();
        }
        willUpdateProps(nextProps) {
            this._receiptEnv = nextProps.order.getOrderReceiptEnv();
        }
        get receipt() {
            return this.receiptEnv.receipt;
        }
        get orderlines() {
            return this.receiptEnv.orderlines;
        }
        get paymentlines() {
            return this.receiptEnv.paymentlines;
        }
        get isTaxIncluded() {
            return Math.abs(this.receipt.subtotal - this.receipt.total_with_tax) <= 0.000001;
        }
        get receiptEnv () {
          return this._receiptEnv;
        }
        isSimple(line) {
            return (
                line.discount === 0 &&
                line.is_in_unit &&
                line.quantity === 1 &&
                !(
                    line.display_discount_policy == 'without_discount' &&
                    line.price < line.price_lst
                )
            );
        }
    }
    ReCategoryReceipt.template = 'ReCategoryReceipt';

    Registries.Component.add(ReCategoryReceipt);


    return {CategoryReceipt, ReCategoryReceipt};
});
