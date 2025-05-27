odoo.define('after_sales_service.warranty_claim', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.WarrantyClaim = publicWidget.Widget.extend({
        selector: '.warranty-claim-form',
        events: {
            'change #sale_order_id': '_onSaleOrderChange',
            'click #add-product-claim': '_onAddProductClaim',
            'click .remove-product-claim': '_onRemoveProductClaim',
        },

        /**
         * Initialize the widget
         */
        start: function () {
            this.claimCount = 1;
            return this._super.apply(this, arguments);
        },

        /**
         * Handle sale order selection change
         */
        _onSaleOrderChange: function (ev) {
            var self = this;
            var sale_order_id = $(ev.currentTarget).val();

            if (sale_order_id) {
                this._fetchAndPopulateProducts(sale_order_id);
            } else {
                this._resetProductSelects();
            }
        },

        /**
         * Fetch products from server and populate all product selects
         */
        _fetchAndPopulateProducts: function (sale_order_id) {
            var self = this;

            $.ajax({
                url: '/warranty/get_order_products',
                type: 'GET',
                data: {
                    'sale_order_id': sale_order_id
                },
                success: function (data) {
                    var products = JSON.parse(data).products;
                    self._populateProductSelects(products);
                },
                error: function () {
                    self._showErrorInProductSelects();
                }
            });
        },

        /**
         * Populate all product select elements with the given products
         */
        _populateProductSelects: function (products) {
            var self = this;
            this.$('.product-select').each(function() {
                var $select = $(this);
                $select.empty();

                // Add default option
                $select.append($('<option>', {
                    value: '',
                    text: 'Select a Product'
                }));

                // Add products
                products.forEach(function (product) {
                    $select.append($('<option>', {
                        value: product.id,
                        text: product.name
                    }));
                });
            });
        },

        /**
         * Reset all product selects to initial state
         */
        _resetProductSelects: function () {
            this.$('.product-select').empty().append($('<option>', {
                value: '',
                text: 'Select Sale Order First'
            }));
        },

        /**
         * Show error in all product selects
         */
        _showErrorInProductSelects: function () {
            this.$('.product-select').empty().append($('<option>', {
                value: '',
                text: 'Error loading products'
            }));
        },

        /**
         * Add new product claim form
         */
        _onAddProductClaim: function (ev) {
            this.claimCount++;
            var $container = this.$('#product-claims-container');
            var $newClaim = this._createProductClaimHTML(this.claimCount);
            $container.append($newClaim);

            // Show remove buttons if there's more than one claim
            if (this.claimCount > 1) {
                this.$('.remove-product-claim').show();
            }

            // If sale order is selected, populate the new product select
            var sale_order_id = this.$('#sale_order_id').val();
            if (sale_order_id) {
                this._fetchAndPopulateProducts(sale_order_id);
            }
        },

        /**
         * Remove product claim form
         */
        _onRemoveProductClaim: function (ev) {
            $(ev.currentTarget).closest('.product-claim-item').remove();
            this.claimCount--;

            // Hide remove buttons if only one claim remains
            if (this.claimCount === 1) {
                this.$('.remove-product-claim').hide();
            }

            // Update numbering
            this._updateClaimNumbers();
        },

        /**
         * Create HTML for new product claim
         */
        _createProductClaimHTML: function (index) {
            return $(`
                <div class="product-claim-item mb-4">
                    <div class="d-flex align-items-center justify-content-between">
                        <h5>Product Claim #${index}</h5>
                        <button type="button" class="btn btn-danger btn-sm remove-product-claim">Remove</button>
                    </div>
                    <div class="form-group">
                        <label>Product</label>
                        <select name="product_claims[${index-1}][product_id]" class="form-control product-select">
                            <option value="">Select Sale Order First</option>
                        </select>
                        <small style="color: #cc6666;">Note: Only products with active warranties will be listed.</small>
                    </div>
                    <div class="form-group">
                        <label>Issue Description</label>
                        <textarea name="product_claims[${index-1}][description]" class="form-control" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Attachments</label>
                        <input type="file" name="product_claims[${index-1}][attachments]" class="form-control" multiple="multiple"/>
                    </div>
                </div>
            `);
        },

        /**
         * Update claim numbers after removal
         */
        _updateClaimNumbers: function () {
            var self = this;
            this.$('.product-claim-item').each(function(index) {
                var $item = $(this);
                $item.find('h5').text(`Product Claim #${index + 1}`);
                $item.find('select').attr('name', `product_claims[${index}][product_id]`);
                $item.find('textarea').attr('name', `product_claims[${index}][description]`);
                $item.find('input[type="file"]').attr('name', `product_claims[${index}][attachments]`);
            });
        },
    });

    return publicWidget.registry.WarrantyClaim;
});