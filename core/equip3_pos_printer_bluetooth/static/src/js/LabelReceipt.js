odoo.define('equip3_pos_printer_bluetooth.LabelReceipt', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class LabelReceipt extends PosComponent {
        constructor() {
            super(...arguments);

            this._receiptEnv = this.props.order.getOrderReceiptEnv();
            // console.log(this._receiptEnv)
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
    LabelReceipt.template = 'LabelReceipt';

    Registries.Component.add(LabelReceipt);

    class LabelReceiptCancelled extends PosComponent {
        constructor() {
            super(...arguments);
            this._receiptEnv = this.props.changes;
        }
        willUpdateProps(nextProps) {
            this._receiptEnv = nextProps.changes;
        }
        get changes() {
            return this.receiptEnv;
        }
        get receiptEnv () {
          return this._receiptEnv;
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
    LabelReceiptCancelled.template = 'LabelReceiptCancelled';

    Registries.Component.add(LabelReceiptCancelled);

    class LabelReceiptNew extends PosComponent {
        constructor() {
            super(...arguments);
            this._receiptEnv = this.props.changes;
        }
        willUpdateProps(nextProps) {
            this._receiptEnv = nextProps.changes;
        }
        get changes() {
            return this.receiptEnv;
        }
        get receiptEnv () {
          return this._receiptEnv;
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
    LabelReceiptNew.template = 'LabelReceiptNew';

    Registries.Component.add(LabelReceiptNew);

    return {LabelReceipt, LabelReceiptNew, LabelReceiptCancelled};
});
