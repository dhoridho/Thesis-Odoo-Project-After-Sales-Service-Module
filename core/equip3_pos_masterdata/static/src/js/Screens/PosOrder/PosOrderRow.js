odoo.define('equip3_pos_masterdata.PosOrderRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useState} = owl.hooks;
    const field_utils = require('web.field_utils');

    class PosOrderRow extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                refresh: 'done',
            });
        }

        get highlight() {
            return this.props.order !== this.props.selectedOrder ? '' : 'highlight';
        }

        async showMore() {
            const order = this.props.order;
            let link = await this.rpc({
                model: 'pos.order',
                method: 'get_pos_order_backend_link',
                args: [[this.props.order.id],],
            }).then(function(data) {
                return data
            });
            window.open(link, '_blank');
        }

        getDate(date){
            if(!date){
                return 'N/A';
            }
            return field_utils.format.datetime(field_utils.parse.datetime(date));
        }

    }

    PosOrderRow.template = 'PosOrderRow';

    Registries.Component.add(PosOrderRow);

    return PosOrderRow;
});
