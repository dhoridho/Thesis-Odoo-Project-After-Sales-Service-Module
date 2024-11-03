/*
    Copyright 2016 Siddharth Bhalgami <siddharth.bhalgami@techreceptives.com>
    Copyright 2019 Shurshilov Artem <shurshilov.a@yandex.ru>
    License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
*/
odoo.define('web_image_webcam.webcam_widget', function(require) {
    "use strict";

    var core = require('web.core');
//    var Model = require('web.Model');
    var Dialog = require('web.Dialog');
    var base_f = require('web.basic_fields');
    var imageWidget = base_f.FieldBinaryImage;
    var DocumentViewer = require('mail.DocumentViewer');
    var field_utils = require('web.field_utils');

    var _t = core._t;
    var QWeb = core.qweb;

    imageWidget.include({

        interpolateAgePredictions1: function(age, predictedAges) {
            predictedAges = [age].concat(predictedAges).slice(0, 30);
            const avgPredictedAge = predictedAges.reduce((total, a) => total + a) / predictedAges.length;
            return avgPredictedAge;
        },
        face_detection1: async function(video,canvas){
            
            var stop1 = Cookies.get("stop1")
            if (stop1 == true || stop1 == 'true')
                return
            var $this = this
            Cookies.set('get_descriptor', false);
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
                $('#live_webcam').css("padding-left", "unset");
                $($('#live_webcam').parent()).css("padding-left", "unset");
                const resizedDetections = faceapi.resizeResults(detections, displaySize);
                faceapi.draw.drawDetections(canvas, resizedDetections);
                faceapi.draw.drawFaceLandmarks(canvas, resizedDetections);
                if (resizedDetections && Object.keys(resizedDetections).length > 0) {
                        const age = resizedDetections.age;
                        const interpolatedAge = $this.interpolateAgePredictions1(age, []);
                        const gender = resizedDetections.gender;
                        const expressions = resizedDetections.expressions;
                        const maxValue = Math.max(...Object.values(expressions));
                        const emotion = Object.keys(expressions).filter(
                        item => expressions[item] === maxValue
                        );
                        $("#age").text(` Age - ${interpolatedAge}`);
                        $("#gender").text(` Gender - ${gender}`);
                        $("#emotion").text(`Emotion - ${emotion[0]}`);
                        const box = resizedDetections.detection.box;
                        const drawBox = new faceapi.draw.DrawBox(box, { label: "Descriptor..." });
                        drawBox.draw(canvas);
                        Cookies.set('get_descriptor', true);
                    }
            }
            await $this.sleep1(300);
            $this.face_detection1(video, canvas)
        },
        sleep1: function(ms) {
          return new Promise(resolve => setTimeout(resolve, ms));
        },

        _render: function () {
            this._super();
            if(this.model!='hr.employee'){
                  var $this = this
            
    
            var self = this,
                WebCamDialog = $(QWeb.render("WebCamDialog")),
                img_data;

            let models_path = '/hr_attendance_face_recognition/static/src/js/models'
            /****Loading the model ****/
   
          faceapi.nets.tinyFaceDetector.loadFromUri(models_path)
          faceapi.nets.faceLandmark68Net.loadFromUri(models_path)
          faceapi.nets.faceRecognitionNet.loadFromUri(models_path)
          faceapi.nets.faceExpressionNet.loadFromUri(models_path)
          faceapi.nets.ageGenderNet.loadFromUri(models_path)

            // ::webcamjs:: < https://github.com/jhuckaby/webcamjs >
            // Webcam: Set Custom Parameters
            
             Webcam.set({
                width: 320,
                height: 240,
                dest_width: 320,
                dest_height: 240,
                image_format: 'jpeg',
                jpeg_quality: 90,
                force_flash: false,
                fps: 45,
                swfURL: '/web_image_webcam/static/src/js/webcam.swf',
                //force_flash: true,
            });

            self.$el.find('.o_form_binary_file_web_cam').removeClass('col-md-offset-5');

/*            new Model('ir.config_parameter').call('get_param', ['web_widget_image_webcam.flash_fallback_mode', false]).
            then(function(default_flash_fallback_mode) {
                if (default_flash_fallback_mode == 1) {
                    Webcam.set({
                        
                            :: Important Note about Chrome 47+ :: < https://github.com/jhuckaby/webcamjs#important-note-for-chrome-47 >
                            Setting "force_flash" to "true" will always run in Adobe Flash fallback mode on Chrome, but it is not desirable.
                        
                        force_flash: true,
                    });
                }
            });*/

            self.$el.find('.o_form_binary_file_web_cam').off().on('click', function(){
                // Init Webcam

               
            
                Cookies.set('stop1', false);
                Webcam.on('live', async function(data) {
    

                    const video = await WebCamDialog.find("video")[0];

                    $(video).before('<img id="face_recog_area" src="/equip3_hr_attendance_extend/static/src/img/face%20recog.png" style="position: absolute;left: 63px;width: auto;height: 200px;bottom: 22px;">');
                    const canvas = await faceapi.createCanvasFromMedia(video);
                    $(canvas).css('left', '0px');
                    $(canvas).css('position', 'absolute');
                    $(video).css('float', 'left');
                    let container = document.getElementById("live_webcam");
                    container.append(canvas);
                     $this.face_detection1(video, canvas);
          
                
                    
            });
                new Dialog(self, {
                    size: 'large',
                    dialogClass: 'o_act_window',
                    title: _t("WebCam Booth"),
                    $content: WebCamDialog,
                    buttons: [
                        {
                            text: _t("Take Snapshot"), classes: 'btn-primary take_snap_btn',
                            click: function () {
                                
                                Cookies.set('stop1', true);
                                $(".modal-body #live_webcam").before('<div id="webcam_result" class="webcam_result_attendance"/>');
                                Webcam.snap( function(data) {
                                    img_data = data;
                                    // Display Snap besides Live WebCam Preview
                                    WebCamDialog.find("#webcam_result").html('<img src="'+img_data+'"/>');
                                    $($('#live_webcam video[playsinline="playsinline"][autoplay="autoplay"]')[0]).addClass('d-none')
                                    $('#live_webcam').css("position", "absolute");
                                    $('#live_webcam').css("top", "0");
                                });
                                // Remove "disabled" attr from "Save & Close" button
                                $('.save_close_btn').removeAttr('disabled');
                                $('.cam_after').removeClass('d-none');
                                $('.take_snap_btn').addClass('d-none');
                                Webcam.off('live');
                                $('#face_recog_area').remove()
                                
                            }
                        },
                        {
                            text: _t("Save & Close"), classes: 'btn-primary save_close_btn cam_after d-none', 
                            click: function () {
                                var get_descriptor = Cookies.get("get_descriptor")
                                console.log(get_descriptor,'get_descriptorget_descriptorget_descriptor')
                                if (get_descriptor == true || get_descriptor == 'true') {
                                    var img_data_base64 = img_data.split(',')[1];
                                    var approx_img_size = 3 * (img_data_base64.length / 4)  // like... "3[n/4]"
                                    $this.on_file_uploaded(approx_img_size, "web-cam-preview.jpeg", "image/jpeg", img_data_base64);
                                    $('.cam_after_close').click()
                                }
                                else{
                                    alert("Descriptor Missing... Please take your picture again..")
                                }
                                    
                            }
                               
                        },
                        {
                            text: _t("Retake"), classes: 'btn-primary cam_after  d-none',
                            click: async function () {
                                await $('.cam_after_close').click()
                                await $('.o_form_image_controls .o_form_binary_file_web_cam').click()                             
                            }
                        },
                        {
                            text: _t("Close"), close: true, classes:'cam_after_close'
                        }
                    ]
                }).open();
 
    
                    

                Webcam.attach(WebCamDialog.find('#live_webcam')[0]);

                // At time of Init "Save & Close" button is disabled
                $('.save_close_btn').attr('disabled', 'disabled');

                // Placeholder Image in the div "webcam_result"
                WebCamDialog.find("#webcam_result").html('<img src="/web_image_webcam/static/src/img/webcam_placeholder.png"/>');
            });
            }
        },
    });

    Dialog.include({
        destroy: function () {
            $('#face_recog_area').remove()
            Cookies.set('stop1', true);
            Webcam.off('live');
            $('#live_webcam canvas').remove()
            // Shut Down the Live Camera Preview | Reset the System
            $('.take_snap_btn').removeClass('d-none');
             $('.modal-body #webcam_result.webcam_result_attendance').remove();
             $('#live_webcam').css("position", "unset");
            $('#live_webcam').css("top", "unset");
             $($('#live_webcam video[playsinline="playsinline"][autoplay="autoplay"]')[0]).removeClass('d-none')
             $(".modal-body #age").text('Age');
            $(".modal-body #gender").text('Gender');
            $(".modal-body #emotion").text('Emotion');
            Webcam.reset();

            this._super.apply(this, arguments);
        },
    });

});
