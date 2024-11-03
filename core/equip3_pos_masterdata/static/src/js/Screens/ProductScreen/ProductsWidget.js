odoo.define('equip3_pos_masterdata.ProductsWidget', function (require) {
    'use strict';

    const ProductsWidget = require('point_of_sale.ProductsWidget')
    const Registries = require('point_of_sale.Registries')
    const {posbus} = require('point_of_sale.utils')

    const RetailProductsWidget = (ProductsWidget) =>
        class extends ProductsWidget {
            constructor() {
                super(...arguments);
                this.productsRecommendations = []
                this.env.pos.set('search_extends_results', null)
            }

            mounted() {
                const self = this;
                super.mounted();
                posbus.on('reload-products-screen', this, this.render);
                this.env.pos.on(
                    'change:search_extends_results',
                    (pos, products) => {},
                    this
                );
                this.env.pos.on(
                    'change:ProductRecommendations',
                    (pos, productRecommentIds) => {
                        self.productsRecommendations = []
                        for (let i = 0; i < productRecommentIds.length; i++) {
                            let product = self.env.pos.db.get_product_by_id(productRecommentIds[i]);
                            if (product) {
                                self.productsRecommendations.push(product)
                            }
                        }
                        self.render()
                        setTimeout(() => {
                            self.productsRecommendations = []
                        }, 1000)

                    },
                    this
                );
                this.env.pos.on(
                    'change:productsModifiers',
                    (pos, product_ids) => {
                        self.product_modifier_ids = product_ids
                        self.product_modifiers = []
                        for (let i = 0; i < product_ids.length; i++) {
                            let product = self.env.pos.db.get_product_by_id(product_ids[i]);
                            if (product) {
                                product.modifiers = true
                                self.product_modifiers.push(product)
                            }
                        }
                        self.render()
                        setTimeout(() => {
                            self.product_modifier_ids = []
                            self.product_modifiers = []
                        }, 1000)
                    },
                    this
                );
                this.env.pos.on('change:selectedBrandId', this.render, this);
                this.env.pos.on('change:selectedSaleCategoryId', this.render, this);
            }

            willUnmount() {
                super.willUnmount();
                posbus.off('reload-products-screen', null, this);
                this.env.pos.off('change:selectedBrandId', null, this);
                this.env.pos.off('change:selectedSaleCategoryId', null, this);
                this.env.pos.off('change:search_extends_results', null, this);
                this.env.pos.off('change:ProductRecommendations', null, this);
            }

            // TODO: odoo original used this.searchWordInput = useRef('search-word-input') from ProductsWidgetControlPanel
            // but we not use it, we trigger this function for get event press Enter of user and try add product
            async _tryAddProduct(event) {
                const {searchWordInput} = event.detail;
                if (searchWordInput && searchWordInput.el) {
                    return super._tryAddProduct(event)
                } else {
                    const searchResults = this.productsToDisplay;
                    if (searchResults.length == 0) {
                        return true
                    }
                    if (searchResults.length === 1) {
                        var order = this.env.pos.get_order()
                        if(order){
                            let product = false;
                            let product_template = searchResults[0];
                            if(product_template.product_variant_ids && product_template.product_variant_ids.length == 1){
                                product = this.env.pos.db.get_product_by_id(product_template.product_variant_ids[0]);
                            }
                            if(!product){
                                return true;
                            }
                            order.add_product( product, { 
                                quantity: 1,
                            });
                        }
                        posbus.trigger('clear-search-bar')
                        this._clearSearch()
                    }
                }
            }

            get subcategories() {
                /*
                if (this.env.pos.config.categ_dislay_type == 'all') {
                    this.env.pos.pos_categories = this.env.pos.pos_categories.sort(function (a, b) {
                        return a.sequence - b.sequence
                    })
                    return this.env.pos.pos_categories
                } else {
                    return super.subcategories
                }*/


                return this.env.pos.db
                .get_category_childs_ids(this.selectedCategoryId)
                .map(id => this.env.pos.db.get_category_by_id(id));

            }

            get hasNoCategories() {
                // kimanh: we force odoo for always return false, default odoo always hide if have not any categories
                return false
            }

            get selectedBrandId() {
                return this.env.pos.get('selectedBrandId');
            }

            get selectedSaleCategoryId() {
                return this.env.pos.get('selectedSaleCategoryId');
            }

            _updateSearch(event) {
                super._updateSearch(event)
                if (this.env.pos.config.quickly_look_up_product) {
                    const products = this.env.pos.db.getAllProducts().filter(p => p['plu_number'] == event.detail || p['barcode'] == event.detail || p['default_code'] == event.detail || p['name'] == event.detail)
                    if (products.length == 1) {
                        var order = this.env.pos.get_order()
                        if(order){
                            order.add_product(products[0], {
                                quantity: 1,
                            });
                        }
                        posbus.trigger('clear-search-bar')
                    }
                }
            }

            disableSale(product) {
                let self = this;
                // if (product['type'] == 'service') {
                //     return true;
                // }
                if (product['available_in_pos'] == false) {
                    return true;
                }
                else if (product['active'] == false) {
                    return true;
                } else if (self.env.pos.config.hide_product_when_outof_stock && !self.env.pos.config.allow_order_out_of_stock) {
                    if (product.type == 'product' && product.get_qty_available() <= 0) {
                        return true;
                    } else {
                        return false;
                    }
                } else {
                    return false;
                }
            }

            get productsToDisplay() {
                const self = this;

                function selectedCategChilds(id){
                    if(typeof id == 'undefined'){
                        id = 0;
                    }
                    let newArr = [id];
                    let arr = [];
                    if(self.env.pos.config.category_ancestors){
                        arr = JSON.parse(self.env.pos.config.category_ancestors);
                    }
                    for(let i in arr){
                        if(arr[i].includes(id)){
                            newArr.push(parseInt(i));
                        }
                    }
                    return newArr;
                }

        
                let productsWillDisplay = [];
                let search_extends_results = this.env.pos.get('search_extends_results');
                
                if(search_extends_results){
                    if (search_extends_results != null) {
                        productsWillDisplay = search_extends_results
                        if (this.selectedCategoryId && this.selectedCategoryId != 0) {
                            productsWillDisplay = productsWillDisplay.filter(p => p.pos_categ_id && p.pos_categ_id[0] == this.selectedCategoryId)
                        }
                    }
                }else{
                    if (this.productsRecommendations && this.productsRecommendations.length > 0) {
                        return this.productsRecommendations.filter((line)=>{return self.disableSale(line)==false});
                    }
                    if (!this.selectedCategoryId || this.selectedCategoryId == 0) {
                        productsWillDisplay = this.env.pos.db.getAllProducts();
                    }else{
                        productsWillDisplay = super.productsToDisplay;
                    }
                }

                let available_categ_ids = self.env.pos.config.iface_available_categ_ids;
                if (self.env.pos.config.limit_categories && available_categ_ids.length > 0) {
                    let categ_and_child_ids = selectedCategChilds(self.selectedCategoryId)
                    productsWillDisplay = productsWillDisplay.filter(function(p){
                        if(p.pos_categ_id){
                            if(categ_and_child_ids.includes(p.pos_categ_id[0])){
                                return true;
                            }
                        }
                        return false;
                    });
                }
                
                if (this.env.pos.config.hidden_product_ids && this.env.pos.config.hidden_product_ids.length > 0) {
                    productsWillDisplay = productsWillDisplay.filter(p => !this.env.pos.config.hidden_product_ids.includes(p.id))
                }
                if (this.selectedSaleCategoryId && this.selectedSaleCategoryId != 0) {
                    productsWillDisplay = productsWillDisplay.filter(p => p.categ_id && p.categ_id[0] == this.selectedSaleCategoryId)
                }

                if (this.env.pos.config.employee_meal){
                    if($('body').attr('data-ems') == '1'){
                        productsWillDisplay = productsWillDisplay.filter(p => p.is_employee_meal)
                    }
                }

                // let productsLimitedDisplay = [];
                // if (this.product_modifier_ids) {
                //     productsLimitedDisplay = productsLimitedDisplay.filter(p => this.product_modifier_ids.indexOf(p.id) == -1)
                //     productsLimitedDisplay = this.product_modifiers.concat(productsLimitedDisplay)
                // }

                if (self.env.pos.config.show_product_template) {
                    let product_template_ids = [];
                    for (let _product of productsWillDisplay) {
                        if(!product_template_ids.includes(_product.product_tmpl_id)){
                            if(self.disableSale(_product)==false){
                                product_template_ids.push(_product.product_tmpl_id);
                            }
                        }
                      
                    }
                    productsWillDisplay = self.env.pos.db.get_product_template_by_ids(product_template_ids);
                }else{
                    productsWillDisplay = productsWillDisplay.filter((l)=>{return self.disableSale(l)==false});
                }

                return productsWillDisplay;
            }

            _switchCategory(event) {
                super._switchCategory(event)
                if (event.detail == 0) { // Todo: event.detail is categoryID, if ID is 0, it mean go to root category and clear search
                    this._clearSearch()
                    this.render()
                }
            }

            async _clearSearch() {
                this.env.pos.set('selectedBrandId', 0);
                this.env.pos.set('selectedCategoryId', 0);
                this.env.pos.set('selectedSaleCategoryId', 0);
                this.env.pos.set('search_extends_results', null)
                super._clearSearch()
            }

            get blockScreen() {
                const selectedOrder = this.env.pos.get_order();
                if (!selectedOrder || !selectedOrder.is_return) {
                    return false
                } else {
                    return true
                }
            }
        }
    Registries.Component.extend(ProductsWidget, RetailProductsWidget);

    return RetailProductsWidget;
});
