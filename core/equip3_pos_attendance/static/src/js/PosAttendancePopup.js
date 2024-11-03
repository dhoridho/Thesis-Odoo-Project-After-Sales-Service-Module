odoo.define('equip3_pos_attendance.PosAttendancePopup', function(require){

  const PosComponent = require('point_of_sale.PosComponent');
  const Registries = require('point_of_sale.Registries');
  const { Gui } = require('point_of_sale.Gui');

  const framework = require('web.framework');

  class PosAttendancePopup extends PosComponent {
      constructor() {
          super(...arguments);
          this.face_recognition = {};
      }
      onClose(){
        let $template = $('.face_recognition_popup');
        $template.hide();
        $template.fadeOut(function(){
            $template.remove();
        });

        Webcam.off('live');
        Webcam.reset();
      }
      open(user_id, checkout) {
        this.current_user_id = user_id
        this.checkout = checkout
        this.changeCashier = !checkout
        let self = this;
        console.log("Open Recognition :::1111")
        framework.blockUI();

        Webcam.off('live');
        Webcam.reset();
        this.rpc({
            route: '/hr_attendance_base',
            params: {
                token: window.localStorage.getItem('token'),
                face_recognition_mode: 'kiosk',
                user_id: user_id ? user_id : false
            },
        }).then(function(data){
            const allowed_user_list = self.env.pos.allowed_users.map((user) => {
                return {
                    id: user.id,
                    item: user,
                    label: user.name,
                    isSelected: false,
                };
            });
            self.face_recognition['allowed_user_list'] = allowed_user_list;
            self.face_recognition['face_recognition_access'] = false;
            self.face_recognition['face_recognition_enable'] = data.face_recognition_enable;
            self.face_recognition['face_recognition_store'] = data.face_recognition_store;
            self.face_recognition['face_emotion'] = data.face_emotion;
            self.face_recognition['face_gender'] = data.face_gender;
            self.face_recognition['face_recognition_mode'] = 'kiosk';

            let age_map =  {
                '20': '0-20',
                '30': '20-30',
                '40': '30-40',
                '50': '40-50',
                '60': '50-60',
                '70': '60-any',
                'any': 'any-any'
            }
            if (data.face_age === 'any'){
                self.face_recognition['face_age'] = 'any-any';
            }else{
                self.face_recognition['face_age'] = age_map[Math.ceil(data.face_age).toString()];
            }

            if (!self.face_recognition.face_recognition_access){
                self.face_recognition.face_recognition_access = false;
            }

            self.face_recognition['labels_ids'] = data.labels_ids;
            let descriptor_ids = [];
            for (let f32base64 of data.descriptor_ids) {
                descriptor_ids.push(new Float32Array(new Uint8Array([...atob(f32base64)].map(c => c.charCodeAt(0))).buffer))
            }
            self.face_recognition['descriptor_ids'] = descriptor_ids;
            self.face_recognition['labels_ids_emp'] = data.labels_ids_emp;

            self.face_recognition['face_photo'] = true;
            if (!self.face_recognition.labels_ids.length || !self.face_recognition.descriptor_ids.length){
                self.face_recognition['face_photo'] = false;
            }
            self.face_recognition['width'] = 600;
            self.face_recognition['height'] = 500;
            framework.unblockUI();
            let $el = $(`
                <div class="face_recognition_popup">
                    <div style="font-size: 14px; z-index: 4;width: 100%;overflow: hidden;" class="modal-dialog">
                      <div class="face_recognition_content">
                          <div style=" background: transparent; border: none; text-align: left;position:relative;" class="title">
                            <div>Face recognition process</div>
                            <div class="result-container">
                                <div id="emotion" style="float:left;">Emotion</div>
                                <div id="gender" style="float:left; padding-left:10px;">Gender</div>
                                <div id="age" style="float:left; padding-left:10px;">Age</div>
                            </div>
                            <div class="button cancel"><i class="fa fa-times"></i></div>
                          </div>
                          <div style="margin: 0; overflow:auto; width:100%;padding-top: 15px;" class="body">
                            <div style="height: 600px; width:100%; position:relative;" class="clearfix">
                                <div id="live_webcam" class="live_webcam"></div>
                            </div>
                          </div>
                          <div class="footer" style="display:none">
                            <div class="button cancel">Close</div>
                          </div>
                      </div>
                    </div>
                    <div class="o_background"></div>
                </div>
            `);
            $el.appendTo('body');
            $el.find('.cancel').on('click', function(){
                $el.hide();
                $el.fadeOut(function(){
                    $el.remove();
                });

                Webcam.off('live');
                Webcam.reset();
            });

            Webcam.off('live');
            Webcam.reset();
            self.load_face_recognition();
        })
    }

    load_face_recognition() {
        let self = this;
        self.fr_load_models().then(function(){
            console.log("prepareWebCam::::111")
            let $popup = $('.face_recognition_popup');
            let width = 600;
            let height = 500;
            if(typeof width != 'undefined' || typeof height != undefined){ 
                Webcam.set({
                    width: width,
                    height: height,
                    dest_width: width,
                    dest_height: height,
                    image_format: 'jpeg',
                    jpeg_quality: 90,
                    force_flash: false,
                    fps: 45,
                    swfURL: '/hr_attendance_face_recognition/static/src/libs/webcam.swf',
                    constraints:{ optional: [{ minWidth: 600 }] }
                }); 
                Webcam.attach($('#live_webcam')[0]); 
                Webcam.on('live', function(data) {
                    $('video').css('width','100% !important');
                    $('video').css('height','100% !important');
                    $('#live_webcam').css('width','100% !important');
                    $('#live_webcam').css('height','100% !important');
                    self.fr_face_predict();
                });
            }
        })
    }

    fr_load_models(){
        console.log("load_models::::111")
        let models_path = '/hr_attendance_face_recognition/static/src/js/models';
        /****Loading the model ****/
        return Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(models_path),
            faceapi.nets.faceLandmark68Net.loadFromUri(models_path),
            faceapi.nets.faceRecognitionNet.loadFromUri(models_path),
            faceapi.nets.faceExpressionNet.loadFromUri(models_path),
            faceapi.nets.ageGenderNet.loadFromUri(models_path)
        ]);
    }
  
    async fr_face_predict(){ 
        const video = document.getElementsByTagName("video")[0];
        const canvas = faceapi.createCanvasFromMedia(video);
        $(canvas).css('left', '16px');
        $(canvas).css('position', 'absolute');
        $(video).css('float', 'left');
        let container = document.getElementById('live_webcam');
        container.append(canvas);
        this.stop = false;
        this.fr_face_detection(video, canvas);
    }

    async fr_face_detection(video, canvas){
        let self = this;
        if (this.stop)
            return false;

        function interpolateAgePredictions(age, predictedAges) {
            predictedAges = [age].concat(predictedAges).slice(0, 30);
            const avgPredictedAge = predictedAges.reduce((total, a) => total + a) / predictedAges.length;
            return avgPredictedAge;
        }
        function check_face_filter(age, gender, emotion) {
            let age_access = false, gender_access = false, emotion_access = false;
            let p1 = self.face_recognition.face_age.split('-')[0];
            let p2 = self.face_recognition.face_age.split('-')[1];
            if (p1 === 'any')
                p1 = 0;
            if (p2 === 'any')
                p2 = 1000;
            p1 = Number(p1)
            p2 = Number(p2)

            if (age >= p1 && age <= p2 )
                age_access = true;
            if (gender === self.face_recognition.face_gender)
                gender_access = true;
            if (emotion === self.face_recognition.face_emotion)
                emotion_access = true;

            if (self.face_recognition.face_age === 'any-any')
                age_access = true;
            if (self.face_recognition.face_gender === 'any')
                gender_access = true;
            if (self.face_recognition.face_emotion === 'any')
                emotion_access = true;

            if (!age_access || !gender_access || !emotion_access)
                return false;
            return true;
        }

        let predictedAges = [];
        const displaySize = { width: video.clientWidth, height: video.clientHeight };
        faceapi.matchDimensions(canvas, displaySize);

        console.log('~ Face descriptor ~', self.face_recognition.descriptor_ids)
        console.log('~ Face label ~', self.face_recognition.labels_ids_emp)
        const detections = await faceapi
            .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
            .withFaceLandmarks()
            .withFaceExpressions()
            .withAgeAndGender()
            .withFaceDescriptor();

        console.log("Face is detected:", (detections?true:false) );
        canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
        if (detections){
            const resizedDetections = faceapi.resizeResults(detections, displaySize);
            faceapi.draw.drawDetections(canvas, resizedDetections);
            faceapi.draw.drawFaceLandmarks(canvas, resizedDetections);

            if (resizedDetections && Object.keys(resizedDetections).length > 0) {
                const age = resizedDetections.age;
                const interpolatedAge = interpolateAgePredictions(age, predictedAges);
                const gender = resizedDetections.gender;
                const expressions = resizedDetections.expressions;
                const maxValue = Math.max(...Object.values(expressions));
                const emotion = Object.keys(expressions).filter( i => expressions[i] === maxValue);

                $("#age").text(`Age - ${interpolatedAge}`);
                $("#gender").text(`Gender - ${gender}`);
                $("#emotion").text(`Emotion - ${emotion[0]}`);

                // Face recognition
                const maxDescriptorDistance = 0.4;               
                const labeledFaceDescriptors = await Promise.all(
                    self.face_recognition.labels_ids.map(async (label, i) => {    
                        return new faceapi.LabeledFaceDescriptors(label, [self.face_recognition.descriptor_ids[i]])
                    })
                )
                const faceMatcher = new faceapi.FaceMatcher(labeledFaceDescriptors, maxDescriptorDistance)
                const results = faceMatcher.findBestMatch(resizedDetections.descriptor);
                const box = resizedDetections.detection.box;
                const text = results.toString();
                const drawBox = new faceapi.draw.DrawBox(box, { label: text });
                drawBox.draw(canvas);

                if (text.indexOf('unknown') === -1 && check_face_filter(interpolatedAge,gender,emotion[0])){
                    let username_id = text.split('(')[0];
                    let checkface1 = Cookies.get("checkface1")
                    let checkface2 = Cookies.get("checkface2")
                    let checkface3 = Cookies.get("checkface3")
                    let checkface4 = Cookies.get("checkface4")
                    let is_ok = false;

                    if(checkface1!=false && checkface1!='false' && checkface3!=false && checkface3!='false'){
                        if (checkface1!=emotion[0] ){
                            if(username_id==checkface3) {
                                is_ok = true;
                            }
                        }
                    }

                    console.log("Face is recognised:", is_ok)
                    if(is_ok){
                        if (self.face_recognition.face_recognition_mode == "kiosk" && self.face_recognition.fullscreen) {
                            let style_css = '<div class="div_need-d-none"><style type="text/css">.need-d-none{display: none !important;}</style></div>'
                            $('body').append(style_css);
                        }
                        if (self.face_recognition.face_recognition_store)
                            await Webcam.snap(data_uri => {
                                Cookies.set('doubleco', true);
                                self.face_recognition.webcam_snapshot = data_uri.split(',')[1];
                            });
                        
                        await this.fr_check_in_out(canvas, text);
                        return;
                    }
                    
                    Cookies.set('checkface1', emotion[0]);
                    Cookies.set('checkface3', username_id);
                }
            }
        }
        await this.fr_wait(300);
        this.fr_face_detection(video, canvas);
    }

    async fr_check_in_out(canvas, user) {
        let self = this;

        console.log('Face recogniton: to -> check in')
        function find_employee_by_user_id(user_id) {
            for (let elem of self.face_recognition.labels_ids_emp){
                if (elem.user_id == user_id){ return elem;}
            }
            return false;
        }

        self.face_recognition.face_recognition_access = true;
        if (self.face_recognition.face_recognition_store){
            self.face_recognition.face_recognition_image = canvas.toDataURL().split(',')[1];
        }
        if (self.face_recognition.face_recognition_mode) {
            let user_id = parseInt(user.split(',')[1].split(' ')[0]);
            let employee = find_employee_by_user_id(user_id);
            const cashier = this.env.pos.employees.find(e => e.user_id[0] === user_id)
            if(employee && user_id && cashier){
                console.log('Face recogniton: check in');

                cashier['is_employee'] = true;
                cashier['is_cashier'] = true;

                if(self.checkout===true){
                    self.rpc({
                        model: 'res.users',
                        method: 'action_pos_attendance_checked_out',
                        args: [user_id],
                        context: {
                            'face_recognition_force': true,
                            'employee': employee,
                            'face_recognition_auto': self.face_recognition.face_recognition_auto,
                            'webcam_snapshot': self.face_recognition.webcam_snapshot,
                            'face_recognition_image': self.face_recognition.face_recognition_image
                        }
                    });
                }
                if(self.changeCashier===true){
                    self.rpc({
                        model: 'res.users',
                        method: 'action_pos_attendance_checked_in',
                        args: [user_id],
                        context: {
                            'face_recognition_force': true,
                            'employee': employee,
                            'face_recognition_auto': self.face_recognition.face_recognition_auto,
                            'webcam_snapshot': self.face_recognition.webcam_snapshot,
                            'face_recognition_image': self.face_recognition.face_recognition_image
                        }
                    });
                }

                let $template = $('.face_recognition_popup');
                $template.hide();
                $template.fadeOut(function(){
                    $template.remove();
                });

                Webcam.off('live');
                Webcam.reset();
                if(self.checkout===true){
                    Gui.showPopup('ConfirmPopup', {
                        title: 'Success',
                        body: 'Checkout succesfully!',
                    });
                    framework.blockUI();
                    window.location = '/web#action=point_of_sale.action_client_pos_menu';
                }
                if(self.changeCashier===true){
                    Gui.showPopup('ConfirmPopup', {
                        title: 'Success',
                        body: 'Change cashier to ' + employee.name,
                    });
                    self.env.pos.set_cashier(employee);
                }
            }
        }
    }

    fr_wait(milliseconds) {
        return new Promise(resolve => setTimeout(resolve, milliseconds));
    }

  }

  PosAttendancePopup.template = `
      <div class="face_recognition_popup">
          <div style="font-size: 14px; z-index: 4;width: 100%;overflow: hidden;" class="modal-dialog">
            <div class="face_recognition_content">
                <div style=" background: transparent; border: none; text-align: left;position:relative;" class="title">
                  <div>Face recognition process</div>
                  <div class="result-container">
                      <div id="emotion" style="float:left;">Emotion</div>
                      <div id="gender" style="float:left; padding-left:10px;">Gender</div>
                      <div id="age" style="float:left; padding-left:10px;">Age</div>
                  </div>
                  <div class="button cancel"><i class="fa fa-times"></i></div>
                </div>
                <div style="margin: 0; overflow:auto; width:100%;padding-top: 15px;" class="body">
                  <div style="height: 600px; width:100%; position:relative;" class="clearfix">
                      <div id="live_webcam" class="live_webcam"></div>
                  </div>
                </div>
                <div class="footer" style="display:none">
                  <div class="button cancel" t-on-click="onClose">Close</div>
                </div>
            </div>
          </div>
          <div class="o_background"></div>
      </div>
  `;
  Registries.Component.add(PosAttendancePopup);
  return PosAttendancePopup;
});