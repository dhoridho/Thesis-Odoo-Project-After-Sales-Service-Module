odoo.define('equip3_pos_general.LoginScreen', function (require) {
    'use strict';

    const {useExternalListener} = owl.hooks;
    const LoginScreen = require('pos_hr.LoginScreen');
    const Registries = require('point_of_sale.Registries');
    const DefaultResScreen = require('equip3_pos_masterdata.DefaultResScreen');

    Registries.Component.add(LoginScreen);

    const UserLoginScreen = (LoginScreen) =>
        class extends LoginScreen {

            constructor() { 
                super(...arguments);

                useExternalListener(window, 'keyup', this._keyUp);
                this.env.pos.lockedUpdateOrderLines = true; // todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
            }

            willUnmount() {
                super.willUnmount();
                const self = this;
                setTimeout(function () {
                    self.env.pos.lockedUpdateOrderLines = false; // timeout 0.5 seconds unlock todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
                }, 500)
            }

            async _keyUp(event) {
                console.log('[UserLoginScreen_keyboardHandler]: ', event.key)
                if (event.key == 'Enter') {
                    this.selectCashier();
                }
            }

            async _barcodeCashierAction(code) {
                this.env.pos.alert_message({
                    title: this.env._t('Scan code'),
                    body: code
                })
                
                let theEmployee;
                let notAllowed = false;
                let notAllowedName = '';
                let allowed_employee_ids = [];

                if(this.env.pos.config && this.env.pos.config.module_pos_hr){
                    if(this.env.pos.config.allowed_employee_ids){
                        allowed_employee_ids = this.env.pos.config.allowed_employee_ids;    
                    }
                }

                for (let employee of this.env.pos.employees) {
                    if (employee.barcode === Sha1.hash(code.code)) {
                        theEmployee = employee;

                        if(allowed_employee_ids){
                            if (!allowed_employee_ids.includes(employee.id)) {
                                notAllowed = true;
                                notAllowedName = employee.name;
                                theEmployee = false;
                            }
                        }
                        break;
                    }
                }
                if(notAllowed){
                    this.env.pos.alert_message({
                        title: this.env._t('Scan code Invalid!'),
                        body: notAllowedName + " not allowed Login to this session"
                    });
                    return;
                }
                if (!theEmployee) return;

                if (!theEmployee.pin || (await this.askPin(theEmployee))) {
                    let cashier = this.env.pos.allowed_users.find((user) => user.id == theEmployee.user_id[0]);
                    if(!cashier) {
                        this.env.pos.alert_message({
                            title: this.env._t('Error'),
                            body: "Object cashier not found!!"
                        });
                        return;
                    }
                    cashier['is_employee'] = true;
                    this.assignCashiertoSession(cashier);
                    this.back();
                }
            }

            async getSelectionCashier(selectionList) {
                const { confirmed, payload: employee } = await this.showPopup('CashierSelectionPopup', {
                    title: this.env._t('Change Cashier'),
                    list: selectionList,
                });

                if (!confirmed) return false;
                if (!employee.pin) {
                    return employee;
                }
                return await this.askPin(employee);
            }

            async selectCashier() {
                const list = this.env.pos.allowed_users.map((user) => {
                    return {
                        id: user.id,
                        item: user,
                        label: user.name,
                        isSelected: false,
                        imageUrl: 'data:image/png;base64, ' + user['image_1920'],
                    };
                });
                const cashier = await this.getSelectionCashier(list);

                if (cashier) {
                    cashier['is_employee'] = true;
                    await this.assignCashiertoSession(cashier)
                    
                    let config = this.env.pos.config;
                    const table = this.env.pos.table;

                    let dine_in = false;
                    if((config.floor_ids.length != 0) || (config.floor_ids.length == 0 && config.is_table_management)){
                        dine_in = true;
                    }
                    //Dine-IN, Takeaway, Employee Meal, Online Outlet
                    let countMethods =  [!dine_in, !config.takeaway_order, !config.employee_meal]
                            .filter(m => m == false).length;

                    jQuery('.pos').attr('data-selected-order-count-method', countMethods);
                    if(countMethods == 0){
                        this.showScreen('ProductScreen', {count_method:0});
                    }else if(countMethods == 1){
                        if (dine_in){
                            if(config.floor_ids.length != 0){
                                this.showScreen('DefaultResScreen');
                            }
                            if(config.floor_ids.length == 0 && config.is_table_management){
                                this.showScreen('DefaultResScreen');
                            }
                        }
                        if (config.takeaway_order){
                            this.showScreen('DefaultResScreen');
                        }
                        if (config.employee_meal){
                            this.showScreen('DefaultResScreen');
                        }
                    }else{
                        this.showScreen('DefaultResScreen', { 
                            name: 'DefaultResScreen', 
                            props: { floor: table ? table.floor : null } 
                        });
                    }

                    return true;
                }
                return false
            }

            async assignCashiertoSession(cashier) {
                this.env.pos.set_cashier(cashier);
                if (this.env.pos.config.multi_session) {
                    try {
                        let sessionValue = await this.rpc({
                            model: 'pos.session',
                            method: 'get_session_by_cashier_id',
                            args: [[], cashier.id, this.env.pos.config.id],
                        })
                        const sessionLogin = sessionValue['session']
                        this.env.pos.pos_session = sessionLogin
                        this.env.pos.login_number = sessionValue.login_number + 1
                        this.env.pos.set_cashier(cashier);
                        this.env.pos.db.save('pos_session_id', this.env.pos.pos_session.id);

                        this.env.pos.log_cashier_pos('login');

                        const orders = this.env.pos.get('orders').models;
                        for (let i = 0; i < orders.length; i++) {
                            orders[i]['pos_session_id'] = sessionLogin['id']
                        }
                        if (this.env.pos.config.cash_control && sessionLogin['state'] != 'opening_control') {
                            posbus.trigger('close-cash-screen')
                        }
                        if (this.env.pos.config.cash_control && sessionLogin['state'] == 'opening_control') {
                            posbus.trigger('open-cash-screen')
                        }
                        this.env.pos.alert_message({
                            title: this.env._t('Login Successfully'),
                            body: cashier.name
                        })
                    } catch (error) {
                        if (error.message.code < 0) {
                            await this.showPopup('OfflineErrorPopup', {
                                title: this.env._t('Offline'),
                                body: this.env._t('Unable to save changes.'),
                            });
                        }
                    }

                }
                return this.back();
            }
        };

    
    LoginScreen.template = 'UserLoginScreen';
    Registries.Component.extend(LoginScreen, UserLoginScreen);

    return LoginScreen;
});
