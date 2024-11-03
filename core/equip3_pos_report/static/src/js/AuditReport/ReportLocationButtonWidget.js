odoo.define('equip3_pos_report.ReportLocationButtonWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    let core = require('web.core');
    let _t = core._t;
    const Registries = require('point_of_sale.Registries');


    class ReportLocationButtonWidget extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
            
        async onClick(){
            var self = this;
            self.showPopup('PopupLocationWidget',{
                'title': 'Audit Report',
            });
        }
    }

    ReportLocationButtonWidget.template = 'ReportLocationButtonWidget';
    ProductScreen.addControlButton({
        component: ReportLocationButtonWidget,
        condition: function() {
            return this.env.pos.config.order_summery;
        },
    });
    Registries.Component.add(ReportLocationButtonWidget);
    return ReportLocationButtonWidget;
});