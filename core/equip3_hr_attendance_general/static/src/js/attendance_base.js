odoo.define('equip3_hr_attendance_general.my_attendances', function(require) {
    "use strict";

    var core = require('web.core');
    var Attendances = require('hr_attendance.my_attendances');
    var QWeb = core.qweb;
    var _t = core._t;
    var rpc = require('web.rpc');
    var config = require('web.config');
    var Dialog = require('web.Dialog');
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var field_utils = require('web.field_utils');
    var FaceRecognitionDialog = require('hr_attendance_face_recognition.my_attendances').FaceRecognitionDialog;

    FaceRecognitionDialog.include({
        start_end_break: function(canvas, user) {
            var debounced = _.debounce(() => {
                this.parent.face_recognition_access = true;
                if (this.parent.face_recognition_store)
                    this.parent.face_recognition_image = canvas.toDataURL().split(',')[1];
                if (this.face_recognition_mode) {
                    var user_id = Number(user.split(',')[1].split(' ')[0]);
                    var employee = this.find_employee_by_user_id(user_id);

                    this.parent.do_action({
                        type: 'ir.actions.client',
                        tag: 'hr_attendance_my_attendances',
                        context: {
                            // check in/out without face recognition
                            'face_recognition_force': true,
                            // employee default
                            'employee': employee,
                            'face_recognition_auto': this.parent.face_recognition_auto,
                            'webcam_snapshot': this.parent.webcam_snapshot,
                            'face_recognition_image': this.parent.face_recognition_image
                        },
                    });
                    return
                }

                this.parent.update_start_end_break();
            }, 500, true);
            debounced();
        },

        face_detection: async function(video, canvas){
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
                    const maxDescriptorDistance = 0.6;                          
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

                    // access success
                    if (text.indexOf('unknown') === -1 &&
                        this.check_face_filter(interpolatedAge,gender,emotion[0])){
                        if (this.parent.face_recognition_store)
                            await Webcam.snap(data_uri => {
                                this.parent.webcam_snapshot = data_uri.split(',')[1];
                            });
                        if (this.parent.is_for_break) {
                            this.start_end_break(canvas, text)
                        }
                        else {
                            this.check_in_out(canvas, text);
                        }
                        return;                    
                    }
                }
            }
            await this.sleep(200);
            this.face_detection(video, canvas);
        },
    });

    Attendances.include({
        events: _.extend({}, Attendances.prototype.events, {
            "click .o_hr_attendance_start_end_break_icon":_.debounce(function() {
                this.update_start_end_break_with_face_recognition();
            }, 200, true),
        }),

        start: function () {
            var self = this;

            var emplpoyee = this._rpc({
                model: 'hr.employee',
                method: 'search_read',
                args: [[['user_id', '=', this.getSession().uid]], [
                    'attendance_state',
                    'name',
                    'hours_today',
                    'break_state',
                    'break_hours_today'
                ]],
            }).then(function (res) {
                self.employee = res.length && res[0];
                if (res.length) {
                    self.hours_today = field_utils.format.float_time(self.employee.hours_today);
                    self.break_state = self.employee.break_state;
                    self.break_hours_today = field_utils.format.float_time(self.employee.break_hours_today);
                }
            });

            var config = this._super.apply(this, arguments).then(function () {
                if (self.searchModelConfig &&
                    self.searchModelConfig.context &&
                    self.searchModelConfig.context.employee){

                    self.kiosk = self.searchModelConfig.context.face_recognition_force;
                    self.face_recognition_auto = self.searchModelConfig.context.face_recognition_auto;
                    self.webcam_snapshot = self.searchModelConfig.context.webcam_snapshot;
                    self.face_recognition_image = self.searchModelConfig.context.face_recognition_image;
                    self.employee = self.searchModelConfig.context.employee;
                    self.hours_today = field_utils.format.float_time(self.employee.hours_today);
                }
            });

            return Promise.all([emplpoyee, config]);
        },

        init: function() {
            this.is_for_break = false
            this._super.apply(this, arguments);
        },

        update_start_end_break_with_face_recognition: function(){
            this.is_for_break = true
            if (!this.face_recognition_enable){
                this.face_recognition_access = true;
                this.update_start_end_break();
                return
            }
            // if kiosk mode enable, recognition already done
            if (this.kiosk){
                this.face_recognition_access = true;
                this.update_start_end_break();
                return
            }
            this.promise_face_recognition.then(
                result => {
                    if (this.face_photo)
                        new FaceRecognitionDialog(this, {
                            labels_ids: this.labels_ids,
                            descriptor_ids: this.descriptor_ids
                        }).open();
                    else
                        Swal.fire({
                        title: 'No one images/photos uploaded',
                          text: "Please go to your profile and upload 1 photo",
                          icon: 'error',
                          confirmButtonColor: '#3085d6',
                          confirmButtonText: 'Ok'
                        });
                },
                error => {
                    console.log(error);
            });
        },

        update_start_end_break: function () {
            var self = this;
            // self.is_for_break = true
            var token = window.localStorage.getItem('token');

            self.state_read = $.Deferred();
            self.state_save = $.Deferred();

            if (Object.keys(self.data).includes("geo_enable")){
                self.parse_data_geo();
                self.geolocation();
            }
            if (Object.keys(self.data).includes("webcam_enable"))
                self.parse_data_webcam();
            if (Object.keys(self.data).includes("ip_enable"))
                self.parse_data_ip();
            if (Object.keys(self.data).includes("token_enable"))
                self.parse_data_token();
            if (Object.keys(self.data).includes("face_recognition_enable"))
                self.parse_data_face_recognition();

            if (Object.keys(self.data).includes("geospatial_enable"))
                self.parse_data_geospatial();
            else
                self.geo_coords.resolve();

            self.geo_coords.then(result =>{
                this._rpc({
                    route: '/hr_attendance_base',
                    params: {
                        token: token,
                        employee: this.employee,
                        employee_from_kiosk: this.kiosk,
                        latitude: self.latitude,
                        longitude: self.longitude,
                        // is_for_break: self.is_for_break
                    },
                }).then(function(data) {
                    self.data = data;
                    self.state_read.resolve();
                    if (!data.length){
                        self.state_save.resolve();
                    }
                    self.state_save.then(function(data) {
                        if (self.webcam_live){
                            Webcam.snap(function(data_uri) {
                                self.webcam_access = true;
                                // base64 data
                                self.webcam_snapshot = data_uri.split(',')[1];
                                if (self.check_access())
                                    self.send_break_data();
                            });
                        }
                        else{
                            if (self.check_access())
                                self.send_break_data();
                        }
                    });
                });
            });
        },

        send_break_data: function() {
            var self = this, geo_str = null;
    
            if (self.latitude && self.longitude)
                var geo_str = self.latitude.toString() + " " + self.longitude.toString();
    
            var access_allowed = QWeb.render("HrAttendanceAccessAllowed", {widget: self});
            var access_denied = QWeb.render("HrAttendanceAccessDenied", {widget: self});
            var access_allowed_disable = QWeb.render("HrAttendanceAccessAllowedDisable", {widget: self});
            var access_denied_disable = QWeb.render("HrAttendanceAccessDeniedDisable", {widget: self});
            
            var accesses = {};
            if (self.ip_access !== undefined) 
                accesses['ip_access'] = {'access': self.ip_access, 'enable': self.ip_enable};
            if (self.token_access !== undefined) 
                accesses['token_access'] = {'access': self.token_access, 'enable': self.token_enable};
            if (self.geo_access !== undefined) 
                accesses['geo_access'] = {'access': self.geo_access, 'enable': self.geo_enable};
            if (self.webcam_access !== undefined) 
                accesses['webcam_access'] = {'access': self.webcam_access, 'enable': self.webcam_enable};
            if (self.face_recognition_access !== undefined) 
                accesses['face_recognition_access'] = {'access': self.face_recognition_access, 'enable': self.face_recognition_enable};
            if (self.geospatial_access !== undefined) 
                accesses['geospatial_access'] = {'access': self.geospatial_access, 'enable': self.geospatial_enable};
    
            self._rpc({
                model: 'hr.employee',
                method: 'break_manual',
                args: [[self.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'],
                context: {
                        'ismobile': config.device.isMobile,
                        'ip': self.ip,
                        'ip_id': self.ip_id,
                        'geospatial_id': self.geospatial_id,
                        'geo': geo_str,
                        'token': self.token_id,
                        'user_agent_html': self.user_agent_html,
                        'webcam': self.webcam_snapshot,
                        'face_recognition_image': self.face_recognition_image,
                        'access_allowed': access_allowed,
                        'access_denied': access_denied,
                        'access_allowed_disable': access_allowed_disable,
                        'access_denied_disable': access_denied_disable,
                        'accesses': accesses,
                        'kiosk_shop_id': self.kiosk_shop_id,
                        'is_for_break': self.is_for_break,
                    },
            })
            .then(function(result) {
                if (self.kiosk)
                    result.action.next_action = 'hr_attendance_kiosk_mode';
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.do_warn(result.warning);
                }
            });
        }

    });
});