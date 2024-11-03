odoo.define('equip3_pos_membership.MemberDepositRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {Gui} = require('point_of_sale.Gui');
    const {useState} = owl.hooks;

    class MemberDepositRow extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                refresh: 'done',
            });
        }

        getDate(date){
            return field_utils.format.datetime(field_utils.parse.datetime(date));
        }

        async addDeposit(deposit) {
            await Gui.showPopup('MemberDepositAddPopups', {deposit:deposit});
        }

    }

    MemberDepositRow.template = 'MemberDepositRow';
    Registries.Component.add(MemberDepositRow);
    return MemberDepositRow;
});
