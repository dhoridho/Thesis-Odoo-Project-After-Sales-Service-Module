odoo.define('equip3_pos_report_ph.PosOrderDetail', function (require) {
    'use strict';

    const PosOrderDetail = require('equip3_pos_masterdata.PosOrderDetail');
    const GeneralPosOrderDetail = require('equip3_pos_general.PosOrderDetail');
    var models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    let _super_Order = models.Order.prototype;
    

    const PHGeneralPosOrderDetail = (PosOrderDetail) =>
        class extends PosOrderDetail {
            async addBackOrder(draft) {
                let res = await super.addBackOrder(draft);
                const order = this.props.order;
                res['is_ph_training_mode'] = order.is_ph_training_mode
                res['void_order_id'] = order.void_order_id
                res['is_exchange_order'] = order.is_exchange_order
                res['is_return_order'] = order.is_return_order
                return res;
            }
            
        }

    Registries.Component.extend(PosOrderDetail, PHGeneralPosOrderDetail);

    return PHGeneralPosOrderDetail;
});
