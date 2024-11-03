odoo.define('equip3_pos_membership.OrderWidget', function (require) {
'use strict';

    const OrderWidget = require('point_of_sale.OrderWidget');
    const Registries = require('point_of_sale.Registries');
    const {useState, useRef, onPatched} = owl.hooks;

    const RetailOrderWidget = (OrderWidget) =>
        class extends OrderWidget {
            constructor() {
                super(...arguments);
            }
            _updateSummary() {
                if(this.env.pos.retail_loyalty){
                    if (this.order && this.order.get_client() && this.env.pos.retail_loyalty) {
                        let points = this.order.get_client_points()
                        let plus_point = points['plus_point']
                        this.order.plus_point = plus_point
                        this.order.redeem_point = points['redeem_point']
                        this.order.remaining_point = points['remaining_point']
                    }
                } 
                super._updateSummary(); 
            }
        }

    Registries.Component.extend(OrderWidget, RetailOrderWidget);
    return RetailOrderWidget;
});
