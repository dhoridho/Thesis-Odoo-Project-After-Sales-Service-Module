odoo.define('equip3_pos_membership.PointsSummary', function(require) {
'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const utils = require('web.utils');

    class PointsSummary extends PosComponent {
        get get_points() {
            let points = this.env.pos.get_order().get_client_points();
            return points;
        }
        updatePoint() {
            const order = this.env.pos.get_order()
            if(order){
                if(this.env.pos.retail_loyalty){
                    if (order && order.get_client() && this.env.pos.retail_loyalty) {
                        let points = order.get_client_points()
                        let plus_point = points['plus_point']
                        order.plus_point = plus_point
                        order.redeem_point = points['redeem_point']
                        order.remaining_point = points['remaining_point']
                    }
                } 
            }
        }

        get order() {
            this.updatePoint();
            const order = this.env.pos.get_order()
            return order;
        }
    }
    
    PointsSummary.template = 'PointsSummary';
    Registries.Component.add(PointsSummary);
    return PointsSummary;
});
