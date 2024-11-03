;(function (factory) {
    var registeredInModuleLoader = false;
    if (typeof define === 'function' && define.amd) {
        define(factory);
        registeredInModuleLoader = true;
    }
    if (typeof exports === 'object') {
        module.exports = factory();
        registeredInModuleLoader = true;
    }
    if (!registeredInModuleLoader) {
        var OldCookies = window.Cookies;
        var api = window.Cookies = factory();
        api.noConflict = function () {
            window.Cookies = OldCookies;
            return api;
        };
    }
}(function () {
    function extend () {
        var i = 0;
        var result = {};
        for (; i < arguments.length; i++) {
            var attributes = arguments[ i ];
            for (var key in attributes) {
                result[key] = attributes[key];
            }
        }
        return result;
    }

    function init (converter) {
        function api (key, value, attributes) {
            var result;
            if (typeof document === 'undefined') {
                return;
            }

            // Write

            if (arguments.length > 1) {
                attributes = extend({
                    path: '/'
                }, api.defaults, attributes);

                if (typeof attributes.expires === 'number') {
                    var expires = new Date();
                    expires.setMilliseconds(expires.getMilliseconds() + attributes.expires * 864e+5);
                    attributes.expires = expires;
                }

                // We're using "expires" because "max-age" is not supported by IE
                attributes.expires = attributes.expires ? attributes.expires.toUTCString() : '';

                try {
                    result = JSON.stringify(value);
                    if (/^[\{\[]/.test(result)) {
                        value = result;
                    }
                } catch (e) {}

                if (!converter.write) {
                    value = encodeURIComponent(String(value))
                        .replace(/%(23|24|26|2B|3A|3C|3E|3D|2F|3F|40|5B|5D|5E|60|7B|7D|7C)/g, decodeURIComponent);
                } else {
                    value = converter.write(value, key);
                }

                key = encodeURIComponent(String(key));
                key = key.replace(/%(23|24|26|2B|5E|60|7C)/g, decodeURIComponent);
                key = key.replace(/[\(\)]/g, escape);

                var stringifiedAttributes = '';

                for (var attributeName in attributes) {
                    if (!attributes[attributeName]) {
                        continue;
                    }
                    stringifiedAttributes += '; ' + attributeName;
                    if (attributes[attributeName] === true) {
                        continue;
                    }
                    stringifiedAttributes += '=' + attributes[attributeName];
                }
                return (document.cookie = key + '=' + value + stringifiedAttributes);
            }

            // Read

            if (!key) {
                result = {};
            }

            // To prevent the for loop in the first place assign an empty array
            // in case there are no cookies at all. Also prevents odd result when
            // calling "get()"
            var cookies = document.cookie ? document.cookie.split('; ') : [];
            var rdecode = /(%[0-9A-Z]{2})+/g;
            var i = 0;

            for (; i < cookies.length; i++) {
                var parts = cookies[i].split('=');
                var cookie = parts.slice(1).join('=');

                if (cookie.charAt(0) === '"') {
                    cookie = cookie.slice(1, -1);
                }

                try {
                    var name = parts[0].replace(rdecode, decodeURIComponent);
                    cookie = converter.read ?
                        converter.read(cookie, name) : converter(cookie, name) ||
                        cookie.replace(rdecode, decodeURIComponent);

                    if (this.json) {
                        try {
                            cookie = JSON.parse(cookie);
                        } catch (e) {}
                    }

                    if (key === name) {
                        result = cookie;
                        break;
                    }

                    if (!key) {
                        result[name] = cookie;
                    }
                } catch (e) {}
            }
            return result;
        }

        api.set = api;
        api.get = function (key) {
            return api.call(api, key);
        };
        api.getJSON = function () {
            return api.apply({
                json: true
            }, [].slice.call(arguments));
        };
        api.defaults = {};
        api.remove = function (key, attributes) {
            api(key, '', extend(attributes, {
                expires: -1
            }));
        };
        api.withConverter = init;
        return api;
    }
    return init(function () {});
}));
Cookies.set('checkface1', false);
Cookies.set('checkface2', false);
Cookies.set('checkface3', false);
Cookies.set('doubleco', false);

odoo.define('equip3_hr_kiosk_web_attendance.kioskhrm', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var config = require('web.config');
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;

    var FaceRecognitionDialog = Dialog.extend({
        xmlDependencies: ['/hr_attendance_face_recognition/static/src/xml/attendance.xml'],
        template: 'WebCamDialog',

        init: function (parent, options) {
            options = options || {};
            options.fullscreen = config.device.isMobile;
            options.fullscreen = true;
            options.dialogClass = options.dialogClass || '' + ' o_act_window';
            options.size = 'large';
            options.title =  _t("Face recognition process");
            this.labels_ids = options.labels_ids;
            this.descriptor_ids = options.descriptor_ids;
            this.labels_ids_emp = options.labels_ids_emp || [];
            this.token = options.token;
            this.lat = options.lat;
            this.long = options.long;
            this.face_recognition_mode = options.face_recognition_mode;
            this.parent = parent;
            this._super(parent, options);
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.width = document.body.scrollWidth;
                self.height = document.body.scrollHeight;

                Webcam.set({
                    width: self.width,
                    height: self.height,
                    dest_width: self.width,
                    dest_height: self.height,
                    image_format: 'jpeg',
                    jpeg_quality: 90,
                    force_flash: false,
                    fps: 45,
                    swfURL: '/hr_attendance_face_recognition/static/src/libs/webcam.swf',
                    constraints:{ optional: [{ minWidth: 600 }] }
                });
                Webcam.attach(self.$('#live_webcam')[0]);
                Webcam.on('live', function(data) {
                    $('video').css('width','100%');
                    $('video').css('height','100%');
                    $('#live_webcam').css('width','100%');
                    $('#live_webcam').css('height','100%');
                    self.face_predict();
                });
            });
        },

        interpolateAgePredictions: function(age, predictedAges) {
            predictedAges = [age].concat(predictedAges).slice(0, 30);
            const avgPredictedAge = predictedAges.reduce((total, a) => total + a) / predictedAges.length;
            return avgPredictedAge;
        },

        find_employee_by_user_id: function(user_id) {
            for (let elem of this.labels_ids_emp)
                if (elem.user_id === user_id)
                    return elem;
        },

        check_in_out: function(canvas, user) {
            var self = this
            var debounced = _.debounce(() => {
                this.parent.face_recognition_access = true;
                if (this.parent.face_recognition_store)
                    this.parent.face_recognition_image = canvas.toDataURL().split(',')[1];
                if (this.face_recognition_mode) {
                    var user_id = Number(user.split(',')[1].split(' ')[0]);
                    var employee = this.find_employee_by_user_id(user_id);
                    // {id: 1, attendance_state: 'checked_in', name: 'Administrator', hours_today: 0, user_id: 2}
                    // this.parent.do_action({
                    //     type: 'ir.actions.client',
                    //     tag: 'hr_attendance_my_attendances',
                    //     context: {
                    //         'direct':true,
                    //         // check in/out without face recognition
                    //         'face_recognition_force': true,
                    //         // employee default
                    //         'employee': employee,
                    //         'face_recognition_auto': this.parent.face_recognition_auto,
                    //         'webcam_snapshot': this.parent.webcam_snapshot,
                    //         'face_recognition_image': this.parent.face_recognition_image,
                    //         'selected_location': this.parent.selected_location,
                    //     },
                    // });
                    rpc.query({
                        route: '/hr_attendance_manual',
                        params: {
                            employee_id: parseInt(employee.id),
                            location: [self.lat, self.long],
                            webcam: self.parent.webcam_snapshot,
                        },
                    }).then(function (result) {
                        var attendance_id = result.action.attendance.id
                        window.location.replace(`/kioskhrm/success/${self.token}/${attendance_id}`)
                    });
                    return
                }
                this.parent.update_attendance();
            }, 500, true);
            debounced();
        },

        check_face_filter: function(age, gender, emotion) {
            var age_access = false, gender_access = false, emotion_access = false;

            var p1 = this.parent.face_age.split('-')[0];
            var p2 = this.parent.face_age.split('-')[1];
            if (p1 === 'any')
                p1 = 0;
            if (p2 === 'any')
                p2 = 1000;
            p1 = Number(p1)
            p2 = Number(p2)

            if (age >= p1 && age <= p2 )
                age_access = true;
            if (gender === this.parent.face_gender)
                gender_access = true;
            if (emotion === this.parent.face_emotion)
                emotion_access = true;

            if (this.parent.face_age === 'any-any')
                age_access = true;
            if (this.parent.face_gender === 'any')
                gender_access = true;
            if (this.parent.face_emotion === 'any')
                emotion_access = true;

            if (!age_access || !gender_access || !emotion_access)
                return false;
            return true;
        },

        face_detection: async function(video, canvas){
            var self = this
            if (this.stop)
                return
            let predictedAges = [];
            const displaySize = { width: video.clientWidth, height: video.clientHeight };
            faceapi.matchDimensions(canvas, displaySize);

            const detections = await faceapi
            .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
       
            .withFaceLandmarks()
            .withFaceExpressions()
            .withAgeAndGender()
            .withFaceDescriptor();

            canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
            if (detections){
                const resizedDetections = faceapi.resizeResults(detections, displaySize);
                faceapi.draw.drawDetections(canvas, resizedDetections);
                faceapi.draw.drawFaceLandmarks(canvas, resizedDetections);

                if (resizedDetections && Object.keys(resizedDetections).length > 0) {
                    const age = resizedDetections.age;
                    const interpolatedAge = this.interpolateAgePredictions(age, predictedAges);
                    const gender = resizedDetections.gender;
                    const expressions = resizedDetections.expressions;
                    const maxValue = Math.max(...Object.values(expressions));
                    const emotion = Object.keys(expressions).filter(
                    item => expressions[item] === maxValue
                    );
                    $("#age").text(`Age - ${interpolatedAge}`);
                    $("#gender").text(`Gender - ${gender}`);
                    $("#emotion").text(`Emotion - ${emotion[0]}`);

                    // Face recognition
                    const maxDescriptorDistance = 0.4;                          
                    //const labeledFaceDescriptors = await new faceapi.LabeledFaceDescriptors(this.labels_ids[0], this.descriptor_ids)
                    //const faceMatcher = await new faceapi.FaceMatcher(labeledFaceDescriptors, maxDescriptorDistance);
                    const labeledFaceDescriptors = await Promise.all(
                      this.labels_ids.map(async (label, i) => {          
                          return new faceapi.LabeledFaceDescriptors(label, [this.descriptor_ids[i]])
                      })
                    )
                    const faceMatcher = new faceapi.FaceMatcher(labeledFaceDescriptors, maxDescriptorDistance)
                    const results = faceMatcher.findBestMatch(resizedDetections.descriptor);
                    const box = resizedDetections.detection.box;
                    const text = results.toString();
                    const drawBox = new faceapi.draw.DrawBox(box, { label: text });
                    drawBox.draw(canvas);
                    var is_not_photo = false
                    if (text.indexOf('unknown') === -1 && this.check_face_filter(interpolatedAge,gender,emotion[0])){
                        var checkface1 = Cookies.get("checkface1")
                        var checkface2 = Cookies.get("checkface2")
                        var checkface3 = Cookies.get("checkface3")
                        var checkface4 = Cookies.get("checkface4")
            
                        if(checkface1!=false && checkface1!='false' && checkface3!=false && checkface3!='false'){
                            if (checkface1!=emotion[0] ){
                                if(text.split('(')[0]==checkface3) {
                                    is_not_photo = true
                                }
                            }
                        }

                        if(is_not_photo==true || is_not_photo=='true'){
                            if (self.face_recognition_mode == "kiosk" && self.fullscreen) {
                                var style_css= '<div class="div_need-d-none"><style type="text/css">.need-d-none{display: none !important;}</style></div>'
                                $( "body" ).append(style_css);
                            }
                            if (this.parent.face_recognition_store)
                                await Webcam.snap(data_uri => {
                                    Cookies.set('doubleco', true);
                                    this.parent.webcam_snapshot = data_uri.split(',')[1];
                                });
                            this.check_in_out(canvas, text);
                            return;   
                        }
                        Cookies.set('checkface1', emotion[0]);
                        Cookies.set('checkface3', text.split('(')[0]);
                    }
                }
            }
            await this.sleep(200);
            this.face_detection(video, canvas);
        },

        sleep: function(ms) {
          return new Promise(resolve => setTimeout(resolve, ms));
        },

        face_predict: async function(){
            const video = $('video[playsinline="playsinline"][autoplay="autoplay"]')[0];
            const canvas = faceapi.createCanvasFromMedia(video);
            $(canvas).css('left', '16px');
            $(canvas).css('position', 'absolute');
            $(video).css('float', 'left');
            let container = document.getElementById("live_webcam");
            container.append(canvas);
            this.stop = false;
            this.face_detection(video, canvas);
        },

        destroy: function () {
            if ($('.modal-footer .btn-primary').length) 
                $('.modal-footer .btn-primary')[0].click();
            this.stop = true;
            Webcam.off('live');
            Webcam.reset();
            this._super.apply(this, arguments);
        },
    });


    publicWidget.registry.kioskHRM = publicWidget.Widget.extend({
        selector: '.o_hr_attendance_kiosk_hrm_mode_container',
        events: {
            'click .o_hr_attendance_button_employees': '_onClickAttendance',
        },
        xmlDependencies: ['/web/static/src/xml/dialog.xml'],

        load_models: function(){
            let models_path = '/hr_attendance_face_recognition/static/src/js/models';
            return Promise.all([
                faceapi.nets.tinyFaceDetector.loadFromUri(models_path),
                faceapi.nets.faceLandmark68Net.loadFromUri(models_path),
                faceapi.nets.faceRecognitionNet.loadFromUri(models_path),
                faceapi.nets.faceExpressionNet.loadFromUri(models_path),
                faceapi.nets.ageGenderNet.loadFromUri(models_path)
            ]);
        },

        parse_data_face_recognition: function () {
            var self = this;
            self.state_read.then(function(data) {
                var data = self.data;

                self.face_recognition_enable = data.face_recognition_enable;
                self.face_recognition_store = data.face_recognition_store;
                self.face_recognition_auto = data.face_recognition_auto;
                self.face_emotion = data.face_emotion;
                self.face_gender = data.face_gender;

                var age_map = {
                    '20':'0-20',
                    '30': '20-30',
                    '40': '30-40',
                    '50': '40-50',
                    '60': '50-60',
                    '70': '60-any',
                    'any': 'any-any'
                }
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

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if ($('.o_hr_attendance_kiosk_welcome_row').length > 0) {
                    self.token = $('#token').text()
                    self.lat = $('#lat').text()
                    self.long = $('#long').text()
                    self.$modal = $(QWeb.render('Dialog', {
                        fullscreen: self.fullscreen,
                        title: self.title,
                        subtitle: self.subtitle,
                        technical: self.technical,
                        renderHeader: self.renderHeader,
                        renderFooter: self.renderFooter,
                    }));
                    self._onClickAttendance()
                }
            });
        },

        start_camera: function (parent) {
            var self = this;
            var ap1 = []

            var def1 = this._rpc({
                route: '/web/dataset/search_read',
                model: 'ir.config_parameter',
                domain: [['key', '=', 'hr_attendance_face_recognition_kiosk_auto']],
                fields: ['value'],
            }).then(function (data) {
                if (data.length > 0) {
                    if (!data.records[0]['value']){
                        var check = false
                        ap1.push(check)
                    } else {
                        var check = true
                        ap1.push(check)
                    }
                } else {
                    var check = false
                    ap1.push(check)
                }
            });

            var token = window.localStorage.getItem('token');
            var def_hr_attendance_base = rpc.query({
                route: '/hr_attendance_base',
                params: {
                    token: token,
                    face_recognition_mode: 'kiosk'
                },
            }).then(function(data) {
                self.data = data;
                self.state_read.resolve();
                self.state_save.then(function() {
                    self.state_render.resolve();
                });
            });

            self.parse_data_face_recognition();
            return $.when(def1,def_hr_attendance_base).done(result =>{
                this.promise_face_recognition.then(result =>{
                    this.state_save.then(result =>{
                        if (this.open_facecam) {
                            if (this.face_photo) {
                                if(ap1[0]) {
                                    new FaceRecognitionDialog(this, {
                                        labels_ids: this.labels_ids,
                                        descriptor_ids: this.descriptor_ids,
                                        labels_ids_emp: this.labels_ids_emp,
                                        get_face_in_cam:true,
                                        face_recognition_mode: 'kiosk',
                                        token: this.token,
                                        lat: this.lat,
                                        long: this.long,
                                    }).open();
                                }
                            } else {
                                Swal.fire({
                                title: 'No one images/photos uploaded',
                                  text: "Please go to your profile and upload 1 photo",
                                  icon: 'error',
                                  confirmButtonColor: '#3085d6',
                                  confirmButtonText: 'Ok'
                                });
                            }
                        }
                    })
                })
            })
        },

        _onClickAttendance: function (ev) {
            var self = this;
            this._rpc({
                route: '/web/dataset/search_read',
                model: 'ir.config_parameter',
                domain: [['key', '=', 'hr_attendance_face_recognition_kiosk_auto']],
                fields: ['value'],
            }).then(function (data) {
                if (data.length > 0){
                    if(!data.records[0]['value']){
                        self.do_action('hr_attendance.hr_employee_attendance_action_kanban', {
                            additional_context: {'no_group_by': true},
                        });
                    }
                    else{
                        self.open_facecam = true;
                        self.start_camera();
                    }
                }
                else{
                    self.do_action('hr_attendance.hr_employee_attendance_action_kanban', {
                        additional_context: {'no_group_by': true},
                    });
                }
            })
        },
    });

    return publicWidget.registry.kioskHRM;
});