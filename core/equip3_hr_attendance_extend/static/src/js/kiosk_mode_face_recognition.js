odoo.define('hr_attendance_face_recognition.kiosk_mode', function(require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var core = require('web.core');
var Session = require('web.session');
var KioskMode = require('hr_attendance.kiosk_mode');
var rpc = require('web.rpc')
var FaceRecognitionDialog = require('hr_attendance_face_recognition.my_attendances').FaceRecognitionDialog;
var Dialog = require('web.Dialog');
const AttendanceDialog = require('equip3_hr_attendance_extend.AttendanceDialog');

var QWeb = core.qweb;



var FaceRecognitionKioskMode = KioskMode.include({
    events: {
        "click .o_hr_attendance_button_employees": function(){
            var self = this;

            // const currentContext = self.context || {}
            // const extendedContext = Object.assign({}, currentContext, {
            //     'attendance_id_pin_disable_masking': true,
            // });
            // READ data from hr config settings if web kiosk pin is True
            this._rpc({
                model: 'hr.config.settings',
                method: 'read',
                args: [[1], [], ['id', 'name', 'web_kiosk_pin']],
                // context: extendedContext
            }).then(function(records) {
                // DO popup
                let record = records[0]
                if(record.web_kiosk_pin){
                    self.open_web_kiosk_popup()
                }else{
                    self.start_face_recog()
                }
            })
        },
        "click .filter_location": "_onClickLocation",
    },

    open_web_kiosk_popup: function(){
        var self = this
        self.employee = {}
        const dialog = new AttendanceDialog(null, {
            onEnterFunction: function () {
                var attendance_id_pin_val = $('#attendance_id_pin').val()
                self._rpc({
                    model: 'hr.employee',
                    method: 'match_attendance_id_pin',
                    args: [
                        attendance_id_pin_val
                    ],
                }).then(function(employees){
                    if (employees.length > 0){
                        self.employee = employees[0]
                        return self.checkin_checkout_availabilty_validation()
                    }else{
                        self.displayNotification({
                            type: 'danger',
                            title: 'Invalid Attendance ID!',
                            sticky: false,
                        });
                        return Promise.reject()
                    }
                }).then(function () {
                    return self.checkin_checkout_avail_checker();
                }).then(function(res){
                    return self._checkin_checkout_availabilty(res)
                }).then(function (result) {
                    if (result){
                        self.displayNotification({
                            type: result.toast_type,
                            title: result.toast_content,
                            sticky: false,
                        });
                        if (result.toast_type === 'danger'){
                            return Promise.reject(new Error(result.toast_content))
                        }
                        else{
                            self.start_face_recog()
                            dialog.close()
                        }
                    }else{
                        self.displayNotification({
                            type: 'danger',
                            title: 'Error could match the locations!',
                            sticky: false,
                        });
                        return Promise.reject(new Error('Error could match the locations!'))
                    }
                }).catch(function(err) {
                    if(err instanceof GeolocationPositionError){
                        self._getPositionErrorToCheck(err).then(function (result) {
                            if (result){
                                self.displayNotification({
                                    type: result.toast_type,
                                    title: result.toast_content,
                                    sticky: false,
                                });
                                if (result.toast_type === 'danger') { return Promise.reject() }
                                else{ return Promise.resolve() }
                            }else{
                                self.displayNotification({
                                    type: 'danger',
                                    title: 'Error could match the locations!',
                                    sticky: false,
                                });
                                return Promise.reject()
                            }
                        });
                    }
                });
            }  // Pass the function to handle "Enter"
        });
        dialog.start();  // Open the dialog
        // var dialog = new Dialog(self, {
        //     title: 'Input Attendance PIN ',
        //     size: 'medium',
        //     buttons: [
        //         {text: 'Enter', classes: 'btn-primary', click: },
        //     ],
        //     $content: $('<div>').html(`
        //         <input type="text" id="attendance_id_pin" class="form-control" required="" style="margin-left: auto !important; margin-right: auto !important;">
        //     `),
        // });

        // dialog.open();
    },

    start_face_recog: function(){
        var self = this;
        var selected_location_value = $('ul.o_location_filter').find('li > a.selected').parent().data('value');
        self.selected_location = selected_location_value;
        rpc.query({
            model: 'ir.config_parameter',
            method: 'search_read',
            domain: [['key', '=', 'hr_attendance_face_recognition_kiosk_auto']],
            fields: ['value']
        }).then(function (data) {
            if (data.length > 0){
                if(!data[0]['value']){
                    self.do_action('hr_attendance.hr_employee_attendance_action_kanban', {
                        additional_context: {'no_group_by': true},
                    });
                }
                else{
                    self.open_facecam = true;
                    self.start();
                }
            }
            else{
                self.do_action('hr_attendance.hr_employee_attendance_action_kanban', {
                    additional_context: {'no_group_by': true},
                });
            }
        })
    },

    checkin_checkout_availabilty_validation: function(){
        var self = this
        var selected_location_value = $('ul.o_location_filter').find('li > a.selected').parent().data('value');
        self.selected_location = selected_location_value
        return this._rpc({
            model: 'hr.employee',
            method: 'save_selected_location',
            args: [
                [self.employee.id],
                {
                    selected_active_location_id: selected_location_value,
                }
            ],
        })
    },

    checkin_checkout_avail_checker: function() {
        var self = this;
        var options = {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        };
        // self._checkin_checkout_availabilty = self._checkin_checkout_availabilty.bind(self)
        // self._getPositionErrorToCheck = self._getPositionErrorToCheck.bind(self)
        // if (navigator.geolocation) {
        return new Promise((resolve, rejected) => {
            navigator.geolocation.getCurrentPosition(
                position => {
                    resolve(position)
                },
                error => {
                    rejected(error)
                },
                options
            )
        });
        // }
    },

    _getPositionErrorToCheck: function (error) {
        console.warn("ERROR(" + error.code + "): " + error.message);
        const position = {
            coords: {
                latitude: 0.0,
                longitude: 0.0,
            },
        };
        return this._checkin_checkout_availabilty(position);
    },

    _checkin_checkout_availabilty: function (position) {
        var self = this;
        return this._rpc({
            model: "hr.employee",
            method: "checkin_checkout_availabilty",
            args: [
                [self.employee.id],
                null,
                [position.coords.latitude, position.coords.longitude],
            ],
        })
    },

    _onClickLocation: function (ev) {
        ev.preventDefault();
        $(ev.target).parents().find('ul.o_location_filter').find('li > a.selected').removeClass('selected');
        if ($(ev.target).is('a')) {
            $(ev.target).addClass('selected');
        } else {
            $(ev.target).find('a').addClass('selected');
        }
        var title = $(ev.target).parents().find('ul.o_location_filter').find('li > a.selected').parent().attr('title');
        $('.location_res').text(title);
    },

    // loaded models there for best perfomance
    load_models: function(){
        let models_path = '/hr_attendance_face_recognition/static/src/js/models'
        return Promise.all([
          faceapi.nets.tinyFaceDetector.loadFromUri(models_path),
          faceapi.nets.faceLandmark68Net.loadFromUri(models_path),
          faceapi.nets.faceRecognitionNet.loadFromUri(models_path),
          faceapi.nets.faceExpressionNet.loadFromUri(models_path),
          faceapi.nets.ageGenderNet.loadFromUri(models_path)
        ]);
    },

    // parse data setting from server
    parse_data_face_recognition: function () {
            var self = this;
            self.state_read.then(function(data) {
                var data = self.data;
                self.face_recognition_enable = data.face_recognition_enable;
                self.face_recognition_store = data.face_recognition_store;
                self.face_recognition_auto = data.face_recognition_auto;

                self.face_emotion = data.face_emotion;
                self.face_gender = data.face_gender;
                var age_map =  {
                    '20':'0-20',
                    '30': '20-30',
                    '40': '30-40',
                    '50': '40-50',
                    '60': '50-60',
                    '70': '60-any',
                    'any': 'any-any'}
                if (data.face_age === 'any')
                    self.face_age = 'any-any';
                else
                    self.face_age = age_map[Math.ceil(data.face_age).toString()];

                if (!self.face_recognition_access)
                    self.face_recognition_access = false;

                self.labels_ids = data.labels_ids;
                //self.labels_ids_emp = JSON.parse(data.labels_ids_emp);
                self.labels_ids_emp = data.labels_ids_emp;
                self.descriptor_ids = [];
                for (var f32base64 of data.descriptor_ids) {
                    self.descriptor_ids.push(new Float32Array(new Uint8Array([...atob(f32base64)].map(c => c.charCodeAt(0))).buffer))
                }
                self.face_photo = true;
                if (!self.labels_ids.length || !self.descriptor_ids.length)
                    self.face_photo = false;
                self.state_save.resolve();             
            });
        },

    init: function (parent, options) {
        this.promise_face_recognition = this.load_models();
        // state when end request /hr_attendance_base
        this.state_read = $.Deferred();
        // after read, we write data to memory 
        this.state_save = $.Deferred();
        // after save we render page template
        this.state_render = $.Deferred();
        this.open_facecam = false;
        // after render we bind click action on template and add map
        this._super(parent, options);
    },


    start:   function() {
        var self = this;
        self.location_list = []
        var ap1 = []

        var location = this._rpc({
            route: '/get/all-active-location-data',
            params: {
                user_id: this.getSession().uid,
            },
        }).then(function (res) {
            self.location_list = res.location_list
            self.$el.html(QWeb.render("HrAttendanceKioskMode", {widget: self}));
        });

        var def1 = rpc.query({
                model: 'ir.config_parameter',
                method: 'search_read',
                domain: [['key', '=', 'hr_attendance_face_recognition_kiosk_auto']],
                fields: ['value']
            }).then(function (data) {
                if (data.length > 0){
                    if(!data[0]['value']){
                        var check = false
                        ap1.push(check)
                    }
                    else{
                        var check = true
                        ap1.push(check)
                    }
                }
                else{
                    var check = false
                    ap1.push(check)
                }
                    
            })



    var token = window.localStorage.getItem('token');
    var def_hr_attendance_base = this._rpc({
        route: '/hr_attendance_base',
        params: {
            token: token,
            face_recognition_mode: 'kiosk',
            employee_id: self.employee ? self.employee.id : false
        },
    }).then(function(data) {
        self.data = data;
        self.state_read.resolve();
        self.state_save.then(function() {
            self.state_render.resolve();
        });
        self.parse_data_face_recognition();
    });
    return $.when(location,def1,def_hr_attendance_base, this._super.apply(this, arguments)).done(
        result =>{
            this.promise_face_recognition.then(
            result =>{
            this.state_save.then(
                result =>{
                    if (this.open_facecam) {
                        if (this.face_photo) {
                            if(ap1[0]){
                                new FaceRecognitionDialog(this, {
                                        labels_ids: this.labels_ids,
                                        descriptor_ids: this.descriptor_ids,
                                        labels_ids_emp: this.labels_ids_emp,
                                        // after finded redirect to my attendance
                                        // without face recognition control
                                        get_face_in_cam:true,
                                        face_recognition_mode: 'kiosk',
                                        selected_location: this.selected_location,
                                    }).open();
                            }
                        }
                            // }
                        else {
                            Swal.fire({
                            title: 'No one images/photos uploaded',
                              text: "Please go to your profile and upload 1 photo",
                              icon: 'error',
                              confirmButtonColor: '#3085d6',
                              confirmButtonText: 'Ok'
                            });
                        }
                    }
                    this.$('.filter_location').eq(0).click();
                    var title = this.$('.filter_location').eq(0).text()
                    this.$('.location_res').text(title);
            })
            })
        })


        
       

    },
});
});
