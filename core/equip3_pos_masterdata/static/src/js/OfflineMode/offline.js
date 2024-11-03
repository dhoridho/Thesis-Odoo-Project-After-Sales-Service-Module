odoo.define('equip3_pos_masterdata.offline', function (require) {
    const models = require('point_of_sale.models');
    const core = require('web.core')
    const retailModel = require('equip3_pos_masterdata.model')
    const bigData = require('equip3_pos_masterdata.big_data')
    const productItem = require('equip3_pos_masterdata.ProductItem')

    let _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        load_server_data: function () {
            console.log('load_server_data for offline mode')
            const self = this;
            this.offlineModel = false
            this.pushOrderInBackground = false
            return _super_PosModel.load_server_data.apply(this, arguments).then(function () {
                console.log('load_server_data for offline started')
                core.bus.on('connection_lost', self, self._onConnectionLost);
                core.bus.on('connection_restored', self, self._onConnectionRestored);
            })
        },

        _onConnectionLost() {
            console.error('Network of Hashmicro POS server turn off. Please checking your network or waiting Hashmicro POS Server online back')
            this.offlineModel = true
            this.set_synch('disconnected', 'Offline')
        },

        _onConnectionRestored() {
            console.warn('Network of Hashmicro POS server Restored')
            this.offlineModel = false
            this.set_synch('connected', '')
        },

        _save_to_server: function (orders, options) {
            
            if(this.config && this.config.is_save_order_history_local){
                this.add_order_history_local(orders);
            } 
            if(this.config && this.config.is_save_order_to_pos_cache_service){
                this.push_order_pos_cache_service(orders);
            }
            
            //TODO: Both Offline or Online, pos.order will be create in the background
            if (this.offlineModel){
                console.error('_save_to_server() Network of Hashmicro POS server turn off. Please checking your network or waiting Hashmicro POS Server online back')
                this.set_synch('disconnected', 'Offline');
                return Promise.resolve([]);
            } else if(!this.offlineModel && this.pushOrderInBackground){ 
                console.warn('_save_to_server() Push Order in the Background')  
                return Promise.resolve([]);
            }else{
                return _super_PosModel._save_to_server.call(this, orders, options);
            }
        },

        getStockDatasByLocationIds(product_ids = [], location_ids = []) {
            if (!this.offlineModel) {
                return _super_PosModel.getStockDatasByLocationIds.call(this, product_ids, location_ids)
            } else {
                console.error('getStockDatasByLocationIds() Network of Hashmicro POS server turn off. Please checking your network or waiting Hashmicro POS Server online back')
                return Promise.resolve(null);
            }
        },

    })
})