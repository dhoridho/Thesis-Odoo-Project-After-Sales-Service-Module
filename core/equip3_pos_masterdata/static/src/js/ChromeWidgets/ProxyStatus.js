odoo.define('equip3_pos_masterdata.ProxyStatus', function (require) {
    'use strict';

    const ProxyStatus = require('point_of_sale.ProxyStatus');
    const Registries = require('point_of_sale.Registries');

    const RetailProxyStatus = (ProxyStatus) =>
        class extends ProxyStatus {
            constructor() {
                super(...arguments);
            }

            _setStatus(newStatus) {
                super._setStatus(newStatus)
                if (this.env.pos.config.proxy_ip && this.env.pos.config.iface_print_via_proxy && newStatus['drivers'] && !newStatus['drivers']['printer'] && newStatus['drivers']['escpos']) {
                    this.state.status = newStatus['status'];
                    this.state.msg = '';
                    console.log('Epson Printer worked')
                }
            }
        }
    Registries.Component.extend(ProxyStatus, RetailProxyStatus);

    return RetailProxyStatus;
});
