odoo.define('equip3_pos_masterdata.SaleOrderRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {useState} = owl.hooks;

    class SaleOrderRow extends PosComponent {

        constructor() {
            super(...arguments);
            this.state = useState({
                refresh: 'done',
            });
        }


        get getHighlight() {
            return this.props.order !== this.props.selectedOrder ? '' : 'highlight';
        }

        showMore() {
            const order = this.props.order;
            const link = window.location.origin + "/web#id=" + order.id + "&view_type=form&model=sale.order";
            window.open(link, '_blank')
        }
    }

    SaleOrderRow.template = 'SaleOrderRow';

    Registries.Component.add(SaleOrderRow);

    return SaleOrderRow;
});
