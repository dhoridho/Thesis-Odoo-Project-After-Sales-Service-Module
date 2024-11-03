odoo.define('equip3_pos_masterdata.ProductsWidgetControlPanel', function (require) {
    'use strict';

    const ProductsWidgetControlPanel = require('point_of_sale.ProductsWidgetControlPanel');
    const {useState} = owl.hooks;
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    const RetailProductsWidgetControlPanel = (ProductsWidgetControlPanel) =>
        class extends ProductsWidgetControlPanel {
            constructor() {
                super(...arguments)
                var self = this
                useListener('filter-selected', this._onFilterSelected)
                useListener('search', this._onSearch)
                useListener('clear-search-product-filter', this.clearFilter)
                useListener('show-categories', this._showCategories)
                this.state = useState({
                    activeExtendFilter: false,
                    showAllCategory: this.env.pos.showAllCategory
                })
                this.searchDetails = {}
                this.filter = null
                this._initializeSearchFieldConstants()
                var sepecialFilter = [
                    this.env._t('All Items'),
                    this.env._t('[Only] Out of Stock'),
                    this.env._t('[Only] Available in Stock'),
                    this.env._t('[Only] Tracking by Lot/Serial'),
                    this.env._t('[Only] Bundle Pack/Combo'),
                    this.env._t('[Only] Included Add-ons Items'),
                    this.env._t('[Only] Multi Variant'),
                    this.env._t('[Only] Multi Unit'),
                    this.env._t('[Only] Multi Barcode'),
                ]
                var hide_product_when_outof_stock = this.env.pos.config.hide_product_when_outof_stock
                if(hide_product_when_outof_stock){
                    sepecialFilter = jQuery.grep(sepecialFilter, function(value) {
                      return value != self.env._t('[Only] Out of Stock');
                    });
                }
                else{
                    sepecialFilter = jQuery.grep(sepecialFilter, function(value) {
                      return value != self.env._t('[Only] Available in Stock');
                    });
                }
                this.sepecialFilter = sepecialFilter
            }

            mounted() {
                super.mounted();
            }

            willUnmount() {
                super.willUnmount()
            }

            _showCategories() {
                this.env.pos.showAllCategory = !this.env.pos.showAllCategory
                this.state.showAllCategory = this.env.pos.showAllCategory
                this.trigger('switch-category', 0)
            }

            get rootCategoryNotSelected() {
                let selectedCategoryId = this.env.pos.get('selectedCategoryId')
                if (selectedCategoryId == 0) {
                    return true
                } else {
                    return false
                }
            }

            get Categories() {
                const allCategories = this.env.pos.db.category_by_id
                let categories = []
                for (let index in allCategories) {
                    categories.push(allCategories[index])
                }
                return categories
            }

            showExtendSearch() {
                this.state.activeExtendFilter = !this.state.activeExtendFilter
            }

            async reloadMasterData() {
                await this.env.pos.syncProductsPartners()
                const coupon_model = this.env.pos.models.find(m => m.model == 'coupon.coupon')
                if (coupon_model) {
                    await this.env.pos.load_server_data_by_model(coupon_model)
                }
                const pricelist_model = this.env.pos.models.find(m => m.model == 'product.pricelist')
                if (pricelist_model) {
                    await this.env.pos.load_server_data_by_model(pricelist_model)
                    this.env.pos.getProductPricelistItems()
                }
            }

            // suggestProducts() {
            //     const self = this;
            //     var sources = this.env.pos.db.get_products_source();
            //     $('.search >input').autocomplete({
            //         source: sources,
            //         minLength: 3,
            //         select: function (event, ui) {
            //             const selectedOrder = self.env.pos.get_order()
            //             if (ui && ui['item'] && ui['item']['value']) {
            //                 var product = self.env.pos.db.get_product_by_id(ui['item']['value']);
            //                 if (product) {
            //                     selectedOrder.add_product(product)
            //                     setTimeout(() => {
            //                         self.clearSearch()
            //                     }, 200)
            //                 }
            //             }
            //         }
            //     });
            // }

            clearSearch() {
                this.env.pos.set('search_extends_results', null)
                this.searchDetails = {};
                super.clearSearch()
                posbus.trigger('reload-products-screen')
                posbus.trigger('remove-filter-attribute')
            }

            clearFilter() {
                this.env.pos.set('search_extends_results', null)
                this.searchDetails = {};
                posbus.trigger('reload-products-screen')
                posbus.trigger('remove-filter-attribute')
                this.render()
            }

            // TODO: ==================== Search bar example ====================
            get searchBarConfig() {
                return {
                    searchFields: this.constants.searchFieldNames,
                    filter: {show: true, options: this.filterOptions},
                };
            }

            // TODO: define search fields
            get _searchFields() {
                var fields = {
                    'String': (product) => product.search_extend,
                    'Product Name': (product) => product.name,
                    'Barcode': (product) => product.barcode,
                    'String': (product) => product.search_extend,
                };
                return fields;
            }

            get filterOptions() {
                return this.sepecialFilter
            }

            get _stateSelectionFilter() {
                return {}
            }

            _initializeSearchFieldConstants() {
                this.constants = {};
                Object.assign(this.constants, {
                    searchFieldNames: Object.keys(this._searchFields),
                    stateSelectionFilter: this._stateSelectionFilter,
                });
            }

            _onFilterSelected(event) {
                this.filter = event.detail.filter;
                this._autoComplete()
            }

            _onSearch(event) {
                const searchDetails = event.detail;
                Object.assign(this.searchDetails, searchDetails);
                this._autoComplete()
            }

            _autoComplete() {
                const filterCheck = (product) => {
                    if (this.filter && !this.sepecialFilter.includes(this.filter)) {
                        if (product.pos_categ_id) {
                            const pos_category_id = product.pos_categ_id[0];
                            const isTheSameCategory = this.filter === this.constants.stateSelectionFilter[pos_category_id]
                            return isTheSameCategory;
                        } else {
                            return false
                        }
                    }
                    if (this.filter && this.filter == 'All Items') {
                        return true
                    }
                    if (this.filter && this.filter == '[Only] Out of Stock') {
                            if (product.get_qty_available() <= 0) {
                                return true
                            } else {
                                return false
                            }
                   
                    }
                    if (this.filter && this.filter == '[Only] Available in Stock') {
             
                            if (product.get_qty_available() > 0) {
                                return true
                            } else {
                                return false
                            }
                     
                    }
                    if (this.filter && this.filter == '[Only] Tracking by Lot/Serial') {
                        if (product.tracking != 'none') {
                            return true
                        } else {
                            return false
                        }
                    }
                    if (this.filter && this.filter == '[Only] Bundle Pack/Combo') {
                        if (product.is_combo || product.is_combo_product_new) {
                            return true
                        } else {
                            return false
                        }
                    }
                    if (this.filter && this.filter == '[Only] Included Add-ons Items') {
                        return false
                    }
                    if (this.filter && this.filter == '[Only] Multi Variant') {
                        if (product.multi_variant) {
                            return true
                        } else {
                            return false
                        }
                    }
                    if (this.filter && this.filter == '[Only] Multi Unit') {
                        if (product.multi_uom) {
                            return true
                        } else {
                            return false
                        }
                    }
                    if (this.filter && this.filter == '[Only] Multi Barcode') {
                        return false
                    }
                    return true;
                };
                const {fieldValue, searchTerm} = this.searchDetails;
                const fieldAccessor = this._searchFields[fieldValue];
                const searchCheck = (product) => {
                    if (!fieldAccessor) return true;
                    const fieldValue = fieldAccessor(product);
                    if (fieldValue === null) return true;
                    if (!searchTerm) return true;
                    return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
                };
                const predicate = (product) => {
                    return filterCheck(product) && searchCheck(product);
                };
                let products = []
                if (this.filter == 'All Items') {
                    products = this.env.pos.db.getAllProducts();
                } else {
                    products = this.env.pos.db.getAllProducts();
                }

                this.clearSearch();

                products = products.filter(predicate);
                this.env.pos.set('search_extends_results', products)
                posbus.trigger('reload-products-screen')
                posbus.trigger('remove-filter-attribute')
            }
        }
    Registries.Component.extend(ProductsWidgetControlPanel, RetailProductsWidgetControlPanel);

    return RetailProductsWidgetControlPanel;
});
