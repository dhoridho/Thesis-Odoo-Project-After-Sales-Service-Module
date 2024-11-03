odoo.define('equip3_pos_masterdata_fnb.FloorScreen', function (require) {
    'use strict';

    const FloorScreen = require('pos_restaurant.FloorScreen');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const { useListener } = require('web.custom_hooks');

    const RetailFloorScreen = (FloorScreen) =>
        class extends FloorScreen {
            constructor() {
                super(...arguments);
                useListener('create-round', this._createRound);
            }
            async _createTableRoundHelper(copyTable) {
                let newTable;
                if (copyTable) {
                    newTable = Object.assign({}, copyTable);
                    newTable.position_h += 10;
                    newTable.position_v += 10;
                } else {
                    newTable = {
                        position_v: 100,
                        position_h: 100,
                        width: 75,
                        height: 75,
                        shape: 'round',
                        seats: 1,
                    };
                }
                newTable.name = this._getNewTableName(newTable.name);
                delete newTable.id;
                newTable.floor_id = [this.activeFloor.id, ''];
                newTable.floor = this.activeFloor;
                try {
                    await this._save(newTable);
                    this.activeTables.push(newTable);
                    return newTable;
                } catch (error) {
                    if (error.message.code < 0) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Offline'),
                            body: this.env._t('Unable to create table because you are offline.'),
                        });
                        return;
                    } else {
                        throw error;
                    }
                }
            }
            async _createRound() {
                const newTable = await this._createTableRoundHelper();
                if (newTable) {
                    this.state.selectedTableId = newTable.id;
                }
            }

            mounted() {
                if (this.env.pos.table) {
                    this.env.pos.set_table(null);
                }
                // super.mounted(); // kimanh: we no need call super because super order set table is null
                posbus.on('refresh:FloorScreen', this, this.render);
                if (this.env.pos.iot_connections && this.env.pos.iot_connections.length) {
                    this.env.pos.config.sync_multi_session = true
                }
            }

            willUnmount() {
                super.willUnmount();
                posbus.off('refresh:FloorScreen', this, null);
            }

            async _tableLongpolling() {
                if (this.env.pos.config.sync_multi_session) {
                    return true
                } else {
                    super._tableLongpolling()
                }
            }
        }
    Registries.Component.extend(FloorScreen, RetailFloorScreen);

    return RetailFloorScreen;
});
