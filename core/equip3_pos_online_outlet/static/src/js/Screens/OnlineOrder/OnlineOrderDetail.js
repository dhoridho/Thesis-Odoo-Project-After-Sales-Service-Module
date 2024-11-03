odoo.define('equip3_pos_online_outlet.OnlineOrderDetail', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');

    class OnlineOrderDetail extends PosComponent {
        constructor() {
            super(...arguments);
        }

        get OrderUrl() {
            const order = this.props.order;
            return window.location.origin + "/web#id=" + order.id + "&action=1569&model=pos.online.outlet.order&view_type=form&cids=&menu_id=";
        }

        get getOnlineOrderLines(){
            let lines = [];
            for(let id of this.props.order.line_ids){
                lines.push(this.env.pos.db.online_order_line_by_id[id]);
            }
            return lines.sort((a, b) => a.sequence - b.sequence);
        }
        
        getDate(date){
            return field_utils.format.datetime(field_utils.parse.datetime(date));
        }

        getOrderFrom(val){
            if(val == 'grabfood'){
                return 'GrabFood';
            }
            if(val == 'gofood'){
                return 'GoFood';
            }
            return val;
        }

        getOrderType(val){
            if(val == 'self-pickup'){
                return 'Self-pickup'; //Pickup/TakeAway/Self-Collection
            }
            if(val == 'grab-delivery'){
                return 'Grab delivery';
            }
            if(val == 'outlet-delivery'){
                return 'Outlet delivery';
            }
            if(val == 'dine-in'){
                return 'Dine-in';
            }
            return val;
        }

    }

    OnlineOrderDetail.template = 'OnlineOrderDetail';
    Registries.Component.add(OnlineOrderDetail);
    return OnlineOrderDetail;
});
