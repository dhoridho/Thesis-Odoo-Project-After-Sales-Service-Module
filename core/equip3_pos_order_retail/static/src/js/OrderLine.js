odoo.define('equip3_pos_order_retail.Orderline', function (require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const { useListener } = require('web.custom_hooks');
    const core = require('web.core');
    const Registries = require('point_of_sale.Registries');

    const ExtendRetailOrderline = (Orderline) =>
        class extends Orderline {
            constructor() {
                super(...arguments);
                useListener('remove-line-order', this._removeOrderLine);
            }

            async _removeOrderLine() {
                let {confirmed, payload: note} = await this.showPopup('CancelReasonPopup', {
                    title: this.env._t('Cancel Reason'),
                })
                if (confirmed) {
                    const selectedOrder = this.env.pos.get_order()
                    const result = await this.env.services.rpc({
                        model: "product.cancel",
                        method: "create",
                        args: [{
                            'order_ref': selectedOrder.name,
                            'product_id': selectedOrder.selected_orderline.product.id,
                            'qty': selectedOrder.selected_orderline.quantity,
                            'uom_id': selectedOrder.selected_orderline.product.uom_id[0],
                            'src_location_id': selectedOrder.location ? selectedOrder.location.id : false ,
                            'cashier_id': selectedOrder.pos.user.id,
                            'cancel_reason': note,
                        }]
                    });
                    if(this.env.pos.config.validate_by_manager){
                        let validate = await this.env.pos._validate_action(this.env._t('Cancel Item'));
                        if (!validate) {
                            return false;
                        }
                    }
                    this.props.line.set_quantity(0);
                    this.props.line.set_item_state('cancelled');
                    this.env.pos.alert_message({
                        title: this.env._t('Warning'),
                        body: this.props.line.product.name + this.env._t(' just cancel out of Cart.')
                    })
                }
            }
        }

    Registries.Component.extend(Orderline, ExtendRetailOrderline);
    return Orderline;

});