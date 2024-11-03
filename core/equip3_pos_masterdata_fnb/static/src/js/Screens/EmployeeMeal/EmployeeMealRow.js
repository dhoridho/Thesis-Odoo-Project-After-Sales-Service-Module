odoo.define('equip3_pos_masterdata_fnb.EmployeeMealRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {useState} = owl.hooks;

    class EmployeeMealRow extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                refresh: 'done',
            });
        }
         
        async _autoSyncBackend() {
           
        }

        get getHighlight() {
            return this.props.employee !== this.props.selectedEmployee ? '' : 'highlight';
        }

        getDate(date){
            return field_utils.format.datetime(field_utils.parse.datetime(date));
        }

        getformatCurrency(price){
            return this.env.pos.format_currency(price);
        }
    }

    EmployeeMealRow.template = 'EmployeeMealRow';
    Registries.Component.add(EmployeeMealRow);
    return EmployeeMealRow;
});
