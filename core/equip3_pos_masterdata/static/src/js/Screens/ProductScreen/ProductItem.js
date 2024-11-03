odoo.define('equip3_pos_masterdata.ProductItem', function (require) {
    'use strict';

    const ProductItem = require('point_of_sale.ProductItem');
    const Registries = require('point_of_sale.Registries');
    ProductItem.template = 'RetailProductItem';
    Registries.Component.add(ProductItem);
    const core = require('web.core');
    const qweb = core.qweb;
    const {useState} = owl.hooks;
    const {posbus} = require('point_of_sale.utils');
    const  utils = require('web.utils');
    const  round_pr = utils.round_precision;


    const RetailProductItem = (ProductItem) =>
        class extends ProductItem {
            constructor() {
                super(...arguments);
                this.state = useState({
                    refresh: 'waiting',
                });
            }
            get imageUrl() {
                const product = this.props.product;
                if (this.env.pos.config.show_product_template){
                    return `/web/image?model=product.template&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
                } else{
                    return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
                }
            }
            mounted() {
                const self = this
                super.mounted();
                $('.product-list-container tr.receipt-line').click(false)
                $('.product-list-container article').click(false)
                posbus.on('reload.product.item', this, this._syncDirectBackendProduct)
            }

            willUnmount() {
                super.willUnmount();
                posbus.off('reload.product.item', this, null)
            }

            _syncProduct(products) {
                let willRender = false
                if (!this.env.pos.config.show_product_template) {
                    if (products.length == 1 && (products[0]['write_date'] != this.props.product.write_date)) {
                        this.env.pos.product_model.loaded(this.env.pos, products)
                        this.env.pos.indexed_db.write('product.product', products);
                        this.props.product = this.env.pos.db.get_product_by_id(this.props.product.id)
                        willRender = true
                    }
                    if (products.length == 0) {
                        this.env.pos.indexed_db.unlink('product.product', this.props.product);
                        this.props.product['active'] = false;
                        this.env.pos.removeProductHasDeletedOutOfCart(this.props.product.id);
                        willRender = true
                    }
                } else {
                    if (products.length == 1 && (products[0]['write_date'] != this.props.product.write_date)) {
                        this.env.pos.get_model('product.template').loaded(this.env.pos, products)
                        this.env.pos.indexed_db.write('product.template', products);
                    
                        this.props.product = this.env.pos.db.get_product_template_by_id(this.props.product.id)
                        willRender = true
                    }
                    if (products.length == 0) {
                        this.env.pos.indexed_db.unlink('product.template', this.props.product);
                        this.props.product['active'] = false;
                        this.env.pos.removeProductHasDeletedOutOfCart(this.props.product.id);
                        willRender = true
                    }
                }
                if (willRender) {
                    this.render()
                    this.env.pos.trigger('reload.quantity.available')
                }
            }

            async showProductInfo() {
                let {confirmed, payload: result} = await this.showPopup('PopUpProductInfo', {
                    title: this.env._t('Information Detail of ') + this.props.product.display_name,
                    product: this.props.product,
                    quantity: 1
                });
                if (confirmed) {
                    const product = result.product
                    this.trigger('click-product', product);
                }
            }

            async _autoSyncBackend() {
                if (this.env.pos.offlineModel) {
                    console.warn('You Hashmicro POS offline')
                    return true
                }
                const self = this
                this.env.pos.set_synch('connecting', '')
                this.state.refresh = 'connecting'
                if (this.env.pos.config.show_product_template) {
                    var object = this.env.pos.get_model('product.template');
                } else {
                    var object = this.env.pos.get_model('product.product');
                }
                var pos_config_location = [this.env.pos.config.stock_location_id[0]]
                for (let iloc = 0; iloc < this.env.pos.config.stock_location_ids.length; iloc++) {
                    var loc_id = this.env.pos.config.stock_location_ids[iloc]
                    if(this.env.pos.config.stock_location_ids.indexOf(loc_id) <= 0 ){
                        pos_config_location.push(loc_id)
                    }
                }
                const products = await this.rpc({
                    model: object.model,
                    method: 'search_read',
                    domain: [['id', '=', this.props.product.id]],
                    fields: object.fields,
                    context: {
                        limit: 1,
                        location:pos_config_location
                    }
                }, {
                    shadow: true,
                    timeout: 75000
                }).then(function (products) {
                    self.state.refresh = 'done'
                    self.env.pos.set_synch('connected', '')
                    return products
                }, function (error) {
                    if (error && error.message && error.message.code == -32098) {
                        self.env.pos.set_synch('disconnected', 'POS Offline')
                    } else {
                        self.env.pos.set_synch('disconnected', 'Error 403')
                    }
                    self.state.refresh = 'error'
                    return null
                })
                if (products != null) {
                    this._syncProduct(products)
                }
            }

            async _syncDirectBackendProduct(product_id) {
                if (this.env.pos.config.show_product_template) {
                    var object = this.env.pos.get_model('product.template');
                } else {
                    var object = this.env.pos.get_model('product.product');
                }
                var pos_config_location = [this.env.pos.config.stock_location_id[0]]
                for (let iloc = 0; iloc < this.env.pos.config.stock_location_ids.length; iloc++) {
                    var loc_id = this.env.pos.config.stock_location_ids[iloc]
                    if(this.env.pos.config.stock_location_ids.indexOf(loc_id) <= 0 ){
                        pos_config_location.push(loc_id)
                    }
                }
                var context = {location:pos_config_location}
                if (product_id == this.props.product.id) {
                    this.env.pos.set_synch('connecting', '')
                    if (this.env.pos.config.show_product_template) {
                        var products = await this.env.pos.getDatasByModel('product.template', [['id', '=', this.props.product.id]],object.fields,context)
                    }
                    else{
                        var products = await this.env.pos.getDatasByModel('product.product', [['id', '=', this.props.product.id]],object.fields,context)
                    }
                    
                    if (products != null) {
                        this._syncProduct(products)
                        this.env.pos.set_synch('connected', '')
                    } else {
                        this.env.pos.set_synch('disconnected', this.env._t('Offline Mode'))
                    }
                }
            }

            

            get imageUrl() {
                const product = this.props.product;
                return `/web/image?model=product.template&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
            }

            get price() {
                let price = 0;
                if (this.env.pos.config.display_sale_price_within_tax) {
                    price = this.props.product.get_price_with_tax(this.pricelist, 1)
                } else {
                    // price = this.props.product.get_price(this.pricelist, 1)
                    price = this.props.product.get_price_without_tax(this.pricelist, 1)
                }
                if (this.env.pos.config.rounding) {
                    price = round_pr(price, this.env.pos.config.rounding_factor);
                }
                if(this.env.pos.selected_order_method == 'employee-meal'){
                    price = this.props.product.get_price(this.pricelist, 1);
                }

                const formattedUnitPrice = this.env.pos.format_currency(
                    price,
                    'Product Price'
                );
                if (this.props.product.to_weight) {
                    return `${formattedUnitPrice}/${
                        this.env.pos.units_by_id[this.props.product.uom_id[0]].name
                    }`;
                } else {
                    return formattedUnitPrice;
                }
            }

            async editProduct() {
                let {confirmed, payload: results} = await this.showPopup('PopUpCreateProduct', {
                    title: this.env._t('Edit ') + this.props.product.display_name,
                    product: this.props.product
                })
                if (confirmed && results) {
                    let value = {
                        name: results.name,
                        list_price: parseFloat(results.list_price),
                        default_code: results.default_code,
                        barcode: results.barcode,
                        standard_price: parseFloat(results.standard_price),
                        type: results.type,
                        available_in_pos: true
                    }
                    if (results.pos_categ_id != 'null') {
                        value['pos_categ_id'] = parseInt(results['pos_categ_id'])
                    }
                    if (results.image_1920) {
                        value['image_1920'] = results.image_1920.split(',')[1];
                    }
                    await this.rpc({
                        model: 'product.product',
                        method: 'write',
                        args: [[this.props.product.id], value]
                    })
                    this._autoSyncBackend()
                    this.env.pos.alert_message({
                        title: this.env._t('Update Successfully'),
                        body: this.props.product.display_name + ' has updated ! When finish all update, please reload POS Screen for update new Datas'
                    })
                }
            }

            async archiveProduct() {
                let {confirmed, payload: confirm} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Warning !!!'),
                    body: this.env._t('Are you sure want Archive Product Name: ') + this.props.product.display_name + this.env._t(' ?')
                })
                if (confirmed) {
                    await this.rpc({
                        model: 'product.product',
                        method: 'write',
                        args: [[this.props.product.id], {
                            available_in_pos: false,
                        }],
                        context: {}
                    })
                    this.env.pos.alert_message({
                        title: this.env._t('Archived Successfully !'),
                        body: this.props.product.display_name + ' has Archived and Remove out POS Screen, if you need active back, contact your Products Admin and set [Available In POS] back !'
                    })
                    this._autoSyncBackend()
                }
            }

            async addBarcode() {
                let newBarcode = await this.rpc({ // todo: template rpc
                    model: 'product.product',
                    method: 'add_barcode',
                    args: [[this.props.product.id]]
                })
                if (newBarcode) {
                    this.props.product['barcode'] = newBarcode
                    this.printBarcode()
                    this._autoSyncBackend()
                }
            }

            async printBarcode() {
                await this.env.pos.do_action('product.report_product_product_barcode', {
                    additional_context: {
                        active_id: this.props.product.id,
                        active_ids: [this.props.product.id],
                    }
                }, {
                    shadow: true,
                    timeout: 6500
                });
                if (this.env.pos.config.proxy_ip && this.env.pos.config.iface_print_via_proxy) {
                    const reportXML = qweb.render('ProductBarcodeLabel', {
                        product: this.props.product
                    });
                    await this.env.pos.proxy.printer.printXmlReceipt(reportXML);
                }
            }

            async doUpdateOnHand() {
                const product = this.props.product
                let stock_location_ids = this.env.pos.get_all_source_locations();
                let stock_datas = await this.env.pos.getStockDatasByLocationIds([product.id], stock_location_ids).then(function (datas) {
                    return datas
                });
                if (stock_datas) {
                    let items = [];
                    let withLot = false
                    if (product.tracking == 'lot') {
                        withLot = true
                    }
                    if (!withLot) {
                        for (let location_id in stock_datas) {
                            let location = this.env.pos.stock_location_by_id[location_id];
                            if (location) {
                                items.push({
                                    id: location.id,
                                    item: location,
                                    location_id: location.id,
                                    quantity: stock_datas[location_id][product.id]
                                })
                            }
                        }
                    } else {
                        let stockQuants = await this.rpc({
                            model: 'stock.quant',
                            method: 'search_read',
                            domain: [['product_id', '=', product.id], ['location_id', 'in', stock_location_ids]],
                            fields: [],
                            context: {
                                limit: 1
                            }
                        })
                        if (stockQuants) {
                            items = stockQuants.map((q) => ({
                                id: q.id,
                                item: q,
                                lot_id: q.lot_id[0],
                                lot_name: q.lot_id[1],
                                location_id: q.location_id[0],
                                location_name: q.location_id[1],
                                quantity: q.quantity
                            }));
                        }
                    }
                    if (items.length) {
                        let {confirmed, payload: result} = await this.showPopup('UpdateStockOnHand', {
                            title: this.env._t('Summary Stock on Hand (Available - Reserved) each Stock Location of [ ') + product.display_name + ' ]',
                            withLot: withLot,
                            array: items,
                        })
                        if (confirmed) {
                            const newStockArray = result.newArray

                            for (let i = 0; i < newStockArray.length; i++) {
                                let newStock = newStockArray[i];
                                if (!withLot) {
                                    await this.rpc({
                                        model: 'stock.location',
                                        method: 'pos_update_stock_on_hand_by_location_id',
                                        args: [newStock['location_id'], {
                                            product_id: product.id,
                                            product_tmpl_id: product.product_tmpl_id,
                                            quantity: parseFloat(newStock['quantity']),
                                            location_id: newStock['location_id']
                                        }],
                                        context: {}
                                    }, {
                                        shadow: true,
                                        timeout: 65000
                                    })
                                } else {
                                    await this.rpc({
                                        model: 'stock.quant',
                                        method: 'write',
                                        args: [newStock['id'], {
                                            quantity: parseFloat(newStock['quantity']),
                                        }],
                                        context: {}
                                    }, {
                                        shadow: true,
                                        timeout: 65000
                                    })
                                }
                            }
                            this.env.pos.trigger('reload.quantity.available')
                            this.env.pos.alert_message({
                                title: product.display_name,
                                body: this.env._t('Successfully update stock on hand'),
                                color: 'success'
                            })
                            return this.doUpdateOnHand(product)
                        }
                    } else {
                        return this.env.pos.alert_message({
                            title: this.env._t('Warning'),
                            body: product.display_name + this.env._t(' not found stock on hand !!!')
                        })
                    }
                }
            }
        }
    Registries.Component.extend(ProductItem, RetailProductItem);

    return ProductItem;
});
