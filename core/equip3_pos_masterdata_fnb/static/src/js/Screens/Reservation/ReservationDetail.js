odoo.define('equip3_pos_masterdata_fnb.ReservationDetail', function (require) {
    'use strict';

    const {getDataURLFromFile} = require('web.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const core = require('web.core');
    const qweb = core.qweb;
    const {posbus} = require('point_of_sale.utils');

    class ReservationDetail extends PosComponent {
        constructor() {
            super(...arguments);
        }
        get OrderUrl() {
            const order = this.props.order;
            return window.location.origin + "/web#id=" + order.id + "&action=1547&model=reserve.order&view_type=form&cids=&menu_id=";
        }
    }

    ReservationDetail.template = 'ReservationDetail';
    Registries.Component.add(ReservationDetail);
    return ReservationDetail;
});
