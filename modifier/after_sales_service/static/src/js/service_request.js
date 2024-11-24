odoo.define('after_sales_service.service_request', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.ServiceRequest = publicWidget.Widget.extend({
        selector: '.service-request-form',
        events: {
            'change #sale_order_id': '_onSaleOrderChange',
        },

        /**
         * Handle sale order selection change
         */
        _onSaleOrderChange: function (ev) {
            var self = this;
            var sale_order_id = $(ev.currentTarget).val();
            var $productSelect = this.$('#product_id');

            $productSelect.empty().append($('<option>', {
                value: '',
                text: 'Loading...'
            }));

            this._rpc({
                route: '/service/get_products',
                params: {
                    sale_order_id: sale_order_id || false
                },
            }).then(function (data) {
                $productSelect.empty().append($('<option>', {
                    value: '',
                    text: 'Select Product'
                }));

                if (data.products) {
                    data.products.forEach(function (product) {
                        $productSelect.append($('<option>', {
                            value: product[0],
                            text: product[1]
                        }));
                    });
                }
            }).guardedCatch(function () {
                $productSelect.empty().append($('<option>', {
                    value: '',
                    text: 'Error loading products'
                }));
            });
        },

        /**
         * Initialize the widget
         */
        start: function () {
            var def = this._super.apply(this, arguments);
            // Load all products initially if no sale order is selected
            if (!this.$('#sale_order_id').val()) {
                this._onSaleOrderChange({ currentTarget: this.$('#sale_order_id') });
            }
            return def;
        },
    });

    return publicWidget.registry.ServiceRequest;
});