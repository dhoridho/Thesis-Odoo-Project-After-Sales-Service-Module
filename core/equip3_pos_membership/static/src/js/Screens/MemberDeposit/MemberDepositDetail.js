odoo.define('equip3_pos_membership.MemberDepositDetail', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');

    class MemberDepositDetail extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        getDate(date){
            return field_utils.format.datetime(field_utils.parse.datetime(date));
        }

    }

    MemberDepositDetail.template = 'MemberDepositDetail';
    Registries.Component.add(MemberDepositDetail);
    return MemberDepositDetail;
});
