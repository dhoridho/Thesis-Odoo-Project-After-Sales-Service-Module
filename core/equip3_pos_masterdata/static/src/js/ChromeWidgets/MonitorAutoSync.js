odoo.define('equip3_pos_masterdata.MonitorAutoSync', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const {Gui} = require('point_of_sale.Gui');
    const {posbus} = require('point_of_sale.utils');
    const {useState} = owl;

    let DATASET = {
        data: {},
        count: {
            product: 0,
            product_stock: 0,
            pricelist: 0,
            promotion: 0,
            coupon: 0,
        }
    };

    class MonitorAutoSync extends PosComponent {
        constructor() {
            super(...arguments);

            useListener('open-monitor-auto-sync-detail', () => this.onClickOpenDetail());

            this.state = useState({
                data: {},
                count: {
                    product: 0,
                    product_stock: 0,
                    pricelist: 0,
                    promotion: 0,
                    coupon: 0,
                }
            });

            if(this.env.pos.config.is_monitor_auto_sync){
                this.applyPreviousDataset();
            }
        }

        mounted() {
            if(this.env.pos.config.is_monitor_auto_sync){
                posbus.on('update-monitor-auto-sync', this, this.updateData);
            }
        }

        willUnmount() {
            if(this.env.pos.config.is_monitor_auto_sync){
                posbus.off('update-monitor-auto-sync', this);
            }
        }

        onClickClear(){
            DATASET = {
                data: {},
                count: {
                    product: 0,
                    product_stock: 0,
                    pricelist: 0,
                    promotion: 0,
                    coupon: 0,
                }
            };
            this.state.data = {};
            this.state.count.product = 0;
            this.state.count.product_stock = 0;
            this.state.count.pricelist = 0;
            this.state.count.promotion = 0;
            this.state.count.coupon = 0;
            console.warn('[MonitorAutoSync] clear');
            this.render();
        }

        async onClickOpenDetail(){
            Gui.showPopup('MonitorAutoSyncDetail', { dataset: DATASET });
        }

        applyPreviousDataset(){
            if(DATASET.data){
                this.state.data = DATASET.data;
            }
            if(DATASET.count.product){
                this.state.count.product += DATASET.count.product;
            }
            if(DATASET.count.product_stock){
                this.state.count.product_stock += DATASET.count.product_stock;
            }
            if(DATASET.count.pricelist){
                this.state.count.pricelist += DATASET.count.pricelist;
            }
            if(DATASET.count.promotion){
                this.state.count.promotion += DATASET.count.promotion;
            }
            if(DATASET.count.coupon){
                this.state.count.coupon += DATASET.count.coupon;
            }
            console.warn('[MonitorAutoSync->applyPreviousDataset]:', DATASET);
        }

        updateData(value){
            let self = this;
            try {
                let new_value = value;
                let old_value = self.state.data[value.id];
                if(old_value){
                    new_value = {...old_value, ...value};
                    new_value.total_unsync_data = old_value.total_unsync_data;
                    new_value.total_synced_data = old_value.total_synced_data + value.total_synced_data;
                    new_value.duration = old_value.duration + value.duration; // in milliseconds
                }

                DATASET.data[value.id] = new_value;
                self.state.data[value.id] = new_value;

                self._sumCountData(value);
            } catch(err) {
                console.error('[updateData] ~ Error', err.message)
            }
        }

        _sumCountData(value){
            let count = value.total_synced_data
            if(value.type == 'product'){
                this.state.count.product += count;
                DATASET.count.product += count;
            }
            if(value.type == 'product_stock'){
                this.state.count.product_stock += count;
                DATASET.count.product_stock += count;
            }
            if(value.type == 'pricelist'){
                this.state.count.pricelist += count;
                DATASET.count.pricelist += count;
            }
            if(value.type == 'promotion'){
                this.state.count.promotion += count;
                DATASET.count.promotion += count;
            }
            if(value.type == 'coupon'){
                this.state.count.coupon += count;
                DATASET.count.coupon += count;
            }
        }

    }

    MonitorAutoSync.template = 'MonitorAutoSync';
    Registries.Component.add(MonitorAutoSync);
    return MonitorAutoSync;
});
