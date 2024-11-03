odoo.define('equip3_pos_masterdata.PopUpConfirmPreOrder', function (require) {
    'use strict';

    const {useState, useRef, useContext} = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const {useExternalListener} = owl.hooks;
    const contexts = require('point_of_sale.PosContext');
    var core = require('web.core');
    var _t = core._t;

    class PopUpConfirmPreOrder extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            let order = this.props.order;
            useExternalListener(window, 'keyup', this._keyUp);
        }

        _keyUp(event) {
            if (event.key == 'Enter') {
                this.confirm()
            }
        }

        mounted() {
            var self = this;
            $(this.el).find('.datetimepicker').datetimepicker({
                format: 'YYYY-MM-DD',
                icons: {
                    time: "fa fa-clock-o",
                    date: "fa fa-calendar",
                    up: "fa fa-chevron-up",
                    down: "fa fa-chevron-down",
                    previous: 'fa fa-chevron-left',
                    next: 'fa fa-chevron-right',
                    today: 'fa fa-screenshot',
                    clear: 'fa fa-trash',
                    close: 'fa fa-remove'
                },
            })
        }

        confirm() {
            var $estimated_date = $('.PopUpConfirmPreOrder input[name="estimated_date"]');
            if(!$estimated_date.val() || $estimated_date.val()==''){
                this.env.pos.alert_message({
                    title: this.env._t('Warning'),
                    body: this.env._t(
                        'Please input Estimated Date first.'
                    ),
                });
            }
            else{
                this.props.resolve({confirmed: true, payload: {'estimated_date':$estimated_date.val()}});
                this.trigger('close-popup');
            }
        }

    }

    PopUpConfirmPreOrder.template = 'PopUpConfirmPreOrder';
    PopUpConfirmPreOrder.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        array: [],
        isSingleItem: false,
    };

    Registries.Component.add(PopUpConfirmPreOrder);

    return PopUpConfirmPreOrder
});
