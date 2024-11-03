odoo.define('equip3_pos_masterdata.LoginScreen', function (require) {
    'use strict';

    const LoginScreen = require('pos_hr.LoginScreen');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const {useBarcodeReader} = require('point_of_sale.custom_hooks');


    const RetailLoginScreen = (LoginScreen) =>
        class extends LoginScreen {
            constructor() {
                super(...arguments);
                useBarcodeReader({
                    loginBadgeId: this._scanbarcode,
                }, true)
            }


            async _barcodeCashierAction(code) {
                this.env.pos.alert_message({
                    title: this.env._t('Scan code'),
                    body: code
                })
                super._barcodeCashierAction(code)
            }

            async _scanbarcode(code) {
                if (!this.env.pos.config.multi_session) {
                    return true
                }
                const employee = this.env.pos.employees.find(emp => emp['barcode'] == Sha1.hash(code))
                if (employee) {
                    await this.assignEmployeetoSession(employee)
                    return true
                }
                return false
            }

            async selectCashier() {
                const list = this.env.pos.employees.map((employee) => {
                    return {
                        id: employee.id,
                        item: employee,
                        label: employee.name,
                        isSelected: false,
                        imageUrl: 'data:image/png;base64, ' + employee['image_1920'],
                    };
                });
                const { confirmed, payload: employee } = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Select Cashier'),
                    list: list,
                });

                if (!confirmed) return false;
                

                if(this.env.pos.config.allow_otp){

                    let api_access = {}
                    api_access['sid'] = this.env.pos.config.twilio_acc_sid
                    api_access['token'] = this.env.pos.config.twilio_auth_token
                    api_access['reset_time'] = this.env.pos.config.pos_otp_reset_time
                    api_access['msg_format'] = this.env.pos.config.pos_otp_msg
                    
                    await this.rpc({
                        model: 'hr.employee',
                        method: 'pos_send_otp',
                        args: [employee,api_access]
                    }).then(function(data){
                        console.log(data);
                    })
                    const empl_otp = await this.rpc({
                        model: 'hr.employee',
                        method: 'search_read',
                        domain: [['id', '=', employee.id]],
                        fields: ['name','last_sent_otp']
                    }).then(function(d){
                        return d[0].last_sent_otp
                    });
                    
                    const { confirmed, payload: inputOTP } = await this.showPopup('NumberPopup', {
                        title: this.env._t('Enter OTP'),
                        startingValue: null,
                    });

                    if (!confirmed) return false;

                    if (confirmed && inputOTP != empl_otp) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Incorrect OTP'),
                        });
                        return false;
                    }else{
                        employee['is_employee'] = true;
                        await this.assignEmployeetoSession(employee)
                    }
                }else{
                    let pin_status = await this.askPin(employee)
                    if(pin_status){
                        await this.assignEmployeetoSession(employee)
                    }else{
                        return false;
                    }
                }
                return false
            }

            async assignEmployeetoSession(employee) {
                this.env.pos.set_cashier(employee);
                if (this.env.pos.config.multi_session) {
                    try {
                        let sessionValue = await this.rpc({
                            model: 'pos.session',
                            method: 'get_session_by_employee_id',
                            args: [[], employee.id, this.env.pos.config.id],
                        })
                        const sessionLogin = sessionValue['session']
                        this.env.pos.pos_session = sessionLogin
                        this.env.pos.login_number = sessionValue.login_number + 1
                        this.env.pos.set_cashier(employee);
                        this.env.pos.db.save('pos_session_id', this.env.pos.pos_session.id);
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
                            body: employee.name
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
        }
    Registries.Component.extend(LoginScreen, RetailLoginScreen);

    return RetailLoginScreen;
});
