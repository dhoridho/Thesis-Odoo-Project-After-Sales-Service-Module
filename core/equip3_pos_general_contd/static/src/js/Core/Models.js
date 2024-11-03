odoo.define('equip3_pos_general_contd.Models', function (require) {
    const models = require('point_of_sale.models');
    const retailModel = require('equip3_pos_masterdata.model');
    const core = require('web.core')
    const indexedDBContd = require('equip3_pos_general_contd.indexedDBContd');

    let _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({

        initialize: function (session, attributes) {
            _super_PosModel.initialize.apply(this, arguments);

            this.indexedDBContd = new indexedDBContd(this.session);
        },


        async action_download_paid_orders() {
            _super_PosModel.action_download_paid_orders.apply(this, arguments);
            await this.action_download_order_history_local();
        },

        async action_download_order_history_local() {
            if(this.config.is_save_order_history_local){
                console.warn('[action_download_order_history_local] backup local order log');
                let order_datas = await this.indexedDBContd.fetch_datas('order.history', 1);;
                if(!order_datas){
                    order_datas = [];
                }
                let filename = `backup_local_order_log_${moment().format('YYYY-MM-DD-HH-mm-ss')}.json`;
                await this.download_data(filename, JSON.stringify(order_datas));
            }
        },


        _prepare_data_order_history_local: function(data_order){
            let new_values = {
                active: true,
                id: this.env.pos.db.get_order_history_local_unique_id(data_order),
                client_use_voucher: null,
                pos: null,
                sync_state: 'Not Sync',
            }
            let order = {
                ...data_order, 
                ...new_values
            }
            return order;
        },

        // TODO: save data order to pos cache service (APK middleware)
        push_order_pos_cache_service(data_orders) {
            let self = this;
            let url = self.config.link_pos_cache_service;
            let datas = [];
            for (let i = data_orders.length - 1; i >= 0; i--) {
                let data_order = data_orders[i].data;
                if(data_order){
                    let order = self._prepare_data_order_history_local(data_order);
                    if(!self.env.pos.db.order_history_local_pos_cache_ids.includes(order.id)){
                        datas.push({
                          id: order.id,
                          uid: order.uid,
                          date: moment.utc().format('YYYY-MM-DD hh:mm:ss'),
                          data: [order]
                        });
                    }
                }
            }

            function _push(data){
                console.warn('Push: data to POS Cache Service:', data);
                let receiptJSON = JSON.stringify(data);
                let xhttp = new XMLHttpRequest();
                xhttp.onreadystatechange = function() {
                    if (xhttp.readyState == XMLHttpRequest.DONE) {
                        console.warn('Finish: Push data to POS Cache Service: ', xhttp.responseText);
                    }
                }
                xhttp.onerror = function () {
                    console.error('Finish: Cannot connect to POS Cache Service! \n' + xhttp.statusText)
                };
                xhttp.open('POST', url, true);
                xhttp.send(receiptJSON);
            }

            for (let data of datas){
                let order = this.env.pos.get_order();
                if(!url){
                    console.warn('[push_order_pos_cache_service] link_pos_cache_service:', link_pos_cache_service);
                }else{
                    _push(data);
                    if(!self.env.pos.db.order_history_local_pos_cache_ids.includes(data.id)){
                        self.env.pos.db.order_history_local_pos_cache_ids.push(data.id);
                    }
                }
            }
        },

        /* Save order to indexedDB for checking data */
        add_order_history_local: function(data_orders){
            let self = this;
            let orders = [];
            for (var i = data_orders.length - 1; i >= 0; i--) {
                let data_order = data_orders[i].data;
                if(data_order){
                    let order = self._prepare_data_order_history_local(data_order);
                    if(!self.env.pos.db.order_history_local_ids.includes(order.id)){
                        orders.push(order);
                    }
                }
            }
            if(orders.length){
                self.indexedDBContd.write('order.history', orders);
                self.env.pos.db.save_order_history_local(orders);
            }
            return data_orders;
        },

        update_order_history_local: function(data_order){
            this.indexedDBContd.write('order.history', [data_order]);
        },

        update_change_order_history_local: function(pos_reference){
            console.warn('[update_change_order_history_local] - order: ', pos_reference)
            let order_log = this.env.pos.db.get_order_history_local_by_name(pos_reference);
            order_log.sync_state = 'Synced';
            this.update_order_history_local(order_log)
            this.env.pos.db.save_order_history_local([order_log]);
        },
        _prepare_data_from_local_order_log(order_log){
            let data = order_log;
            if(data.client_use_voucher_amount && data.client_use_voucher_amount >= 0){
                data.client_use_voucher = true;
            }
            delete data.id;
            delete data.active;
            delete data.pos;
            delete data.sync_state;
            delete data.is_from_import;
            return { id: data.uid,  data: data,  to_invoice: false }
        },
        _force_push_orders: function(orders, options) {
            var self = this;
            options._force_push_orders = true;
            this.set_synch('connecting', orders.length);

            return this._save_to_server(orders, options).then(function (server_ids) {
                self.set_synch('connected');
                for (let i = 0; i < server_ids.length; i++) {
                    self.validated_orders_name_server_id_map[server_ids[i].pos_reference] = server_ids[i].id;
                }
                return _.pluck(server_ids, 'id');
            }).catch(function(error){
                self.set_synch(self.get('failed') ? 'error' : 'disconnected');
                return Promise.reject(error);
            });
        },

        _flush_orders: function (orders, options) {;
            let _force_push_orders = false;
            if(options._force_push_orders){
                _force_push_orders = true;
            }

            if(this.config && this.config.is_save_order_history_local && _force_push_orders == false){
                this.add_order_history_local(orders);
            }
            if(this.config && this.config.is_save_order_to_pos_cache_service && _force_push_orders == false){
                this.push_order_pos_cache_service(orders);
            }

            return _super_PosModel._flush_orders.apply(this, arguments)
        },
        
        _save_to_server: function (orders, options) {
            let self = this;
            let _force_push_orders = false;
            if(options._force_push_orders){
                _force_push_orders = true;
            }

            if(this.config && this.config.is_save_order_history_local && _force_push_orders == false){
                this.add_order_history_local(orders);
            }
            if(this.config && this.config.is_save_order_to_pos_cache_service && _force_push_orders == false){
                this.push_order_pos_cache_service(orders);
            }

            return _super_PosModel._save_to_server.call(this,orders,options).then(function(return_dict){
                if(return_dict && self.config && self.config.is_save_order_history_local){
                    _.forEach(return_dict, function(data){
                        if(data.pos_reference) {
                            try {
                                self.update_change_order_history_local(data.pos_reference);
                            } catch(err) {
                                console.error('Error ~ [update_change_order_history_local] ', err.message)
                            }
                        }
                    });
                }
                return return_dict;
            });
        },

    });
});